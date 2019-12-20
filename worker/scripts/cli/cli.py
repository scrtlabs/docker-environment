#!/usr/bin/python3

import asyncio
import os
import time
from asyncio import ensure_future
from pathlib import Path
from threading import Thread

from components import (
    TextInputDialog,
    MessageDialog
)
from enigma_docker_common.config import Config
from enigma_docker_common.ethereum import EthereumGateway
from prompt_toolkit import Application
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.application.current import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    FloatContainer
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import SearchToolbar, TextArea
from pyfiglet import figlet_format
from windows import (
    EnigmaWindow,
    EthereumWindow,
    StakingWindow
)
from worker_interface import WorkerInterface
from animations import animate_loading_text, rotate_loading_dots
from styles import example_style
kb = KeyBindings()

env_defaults = {'K8S': f'{Path.home() / "p2p" / "config" / "k8s_config.json"}',
                'TESTNET': f'{Path.home() / "p2p" / "config" / "testnet_config.json"}',
                'MAINNET': f'{Path.home() / "p2p" / "config" / "mainnet_config.json"}',
                'COMPOSE': f'{Path.home() / "p2p" / "config" / "compose_config.json"}'}

import logging
logging.getLogger('pycommon.config').setLevel(logging.CRITICAL)
try:
    config = Config(config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
except (ValueError, IOError):
    exit(1)

# noinspection PyUnboundLocalVariable
ethereum = EthereumGateway(config['ETH_NODE_ADDRESS'])
# noinspection PyUnboundLocalVariable
node_actions = WorkerInterface(config=config)

""" Flow: Setup - input staking address, generate eth, transfer funds (balance > 0.1), 
register, wait for staker to do stuff, login """

peers = Buffer()
peers.text = "0"
ethereum_address = Buffer()  # Editable buffer.
ethereum_address.text = "N/A"
staking_address = Buffer()
staking_address.text = "N/A"
balance_buff = Buffer()
balance_buff.text = "N/A"
node_status_buf = Buffer()
node_status_buf.text = "N/A"
enigma_contract_address = node_actions.provider.enigma_contract_address

balance = 0
commands = ["setup", "help", "exit", "register", "login", "logout", "restart", "generate deposit", "generate approve",
            "generate set-address"]
command_completer = WordCompleter(commands, ignore_case=True, sentence=True)


@kb.add('c-c')
def exit_(event):
    """
    Pressing Ctrl-C will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()


@kb.add('f1')
def show_detailed_help(event=None):
    title = 'Help'

    text = """Type setup and enter your staking address when prompted. Enter OK
The software will then generate an operating address for you, which will be 
displayed on the logs and on the CLI.

Transfer some Kovan ETH (1 KETH will be plenty) to your operating address
Then you can use the `register` command. You should eventually see the node 
status switch to 'Registered'.
Next you need to setOperatingAddress() and deposit() with your staking 
address. You can generate the data* for these transactions by using the 
'generate approve' and 'generate deposit', 'generate set-address' commands.
('approve' is a transaction setting an ERC-20 allowance). 
     
* The Data field contains the Ethereum smart-contract function parameters. 
We recommend checking the data before broadcasting 
the transaction """
    show_message(title, text)


def get_help_text():
    if staking_address.text == 'N/A':
        help_text = """\n\nWelcome to the Enigma Management Tool!\n\nThis node is not yet configured with a staking address. To initiate the node, use the "setup" command. 
        """
    else:
        help_text = f'Welcome to the Enigma Management Tool! Try one of our commands: {commands}'
    return help_text


def get_title_text():
    return [
        ("class:title", figlet_format("Enigma Secret Node", font="slant")),
        ("class:title", " (Press [Ctrl-C] to quit, [F1] for help.)"),
    ]


body = ConditionalContainer(VSplit([
    EnigmaWindow(node_status_buf, peers),

    # A vertical line in the middle. We explicitly specify the width, to
    # make sure that the layout engine will not try to divide the whole
    # width by three for all these windows. The window will simply fill its
    # content by repeating this character.
    Window(width=2, char='||'),

    EthereumWindow(balance_buff, ethereum_address),
    # Window(content=BufferControl(buffer=buffer1)),

]), filter=Condition(lambda: staking_address.text != 'N/A'))


search_field = SearchToolbar()  # For reverse search.

output_field = TextArea(style="class:output-field", text=get_help_text())
input_field = TextArea(
    height=1,
    prompt=">>> ",
    style="class:input-field",
    multiline=False,
    wrap_lines=False,
    completer=command_completer,
)


def can_register():
    return float(balance) >= 0.1


# Attach accept handler to the input field. We do this by assigning the
# handler to the `TextArea` that we created earlier. it is also possible to
# pass it to the constructor of `TextArea`.
# NOTE: It's better to assign an `accept_handler`, rather then adding a
#       custom ENTER key binding. This will automatically reset the input
#       field and add the strings to the history.
def accept(buff):
    txt = input_field.text

    # Evaluate "calculator" expression.

    async def coroutine():
        try:
            output = ''
            cmd = txt.lower().strip()
            if cmd == 'exit':
                # to properly handle exit events we create a fake object that matches what an event expects
                # There's probably a better way to do this but I don't care enough to look
                class Object:
                    pass
                event_mock = Object()
                event_mock.app = get_app()
                # noinspection PyTypeChecker
                exit_(event_mock)
            elif cmd == 'help':
                show_detailed_help()
                output = f'Please use F1 on your keyboard for a more detailed help dialogue or try one of the below commands.\n{commands}'
            elif cmd == 'setup':
                open_dialog = TextInputDialog(
                    title="Secret Node Setup",
                    label_text="Enter staking address",
                )
                staking = await show_dialog_as_float(open_dialog)
                await node_actions.set_staking_address(staking)
                output = f"\n\nSuccessfully set staking address!"
            elif cmd == 'restart':
                node_actions.restart()
                output = f"Initiated restart successfully"
            elif cmd.startswith('generate approve'):
                try:
                    deposit_amount = int(float(cmd.split(' ')[2]) * (10**8))
                    output = 'Generated data for transaction:' + node_actions.generate_approve(staking_address.text,
                                                                                               deposit_amount)
                except Exception:
                    output = "Please enter a number of ENG to deposit. " \
                             "Usage: generate approve [N] [  N - amount of allowance in ENG  ]\n\nExample: generate allowance 10000"
            elif cmd.startswith('generate deposit'):
                try:
                    deposit_amount = int(float(cmd.split(' ')[2]) * (10**8))
                    output = 'Generated data for transaction:' + node_actions.generate_deposit(staking_address.text,
                                                                                               deposit_amount)
                except Exception:
                    output = "Please enter a number of ENG to deposit. " \
                             "Usage: generate allowance [N] [  N - amount to deposit in ENG  ]\n\nExample: generate allowance 10000"

            elif cmd.startswith('generate set-address'):
                output = 'Generated data for transaction:' + node_actions.generate_set_operating_address(staking_address.text,
                                                                                                         ethereum_address.text)
            elif cmd in node_actions.available_actions:
                if cmd == 'register' and not can_register():
                    output = '\n\nNot enough ETH in account to register. Please deposit at least 0.1 ETH'
                else:
                    future = asyncio.ensure_future(node_actions.do_action(txt))
                    while not future.done():
                        await animate_loading_text(output_field.buffer, txt)
                    output = future.result()
                
            else:
                output = f"\n\nThis command is not recognized. \n Please try again with one of these commands: {commands}"
            # output = "\nIn:  {}\nOut: {}".format(
            #     input_field.text, eval(input_field.text)
            # )  # Don't do 'eval' in real code!

        except BaseException as e:
            output = "\n\nError: {}".format(e)
        new_text = output

        # Add text to output buffer.
        output_field.buffer.document = Document(
            text=new_text, cursor_position=len(new_text)
        )

    ensure_future(coroutine())


input_field.accept_handler = accept


root_container = FloatContainer(
    content=HSplit([
        Window(
            height=15,
            content=FormattedTextControl(get_title_text),
            align=WindowAlign.CENTER,
            style="class:logo"
        ),
        # Horizontal separator.
        Window(height=1, char="-", style="class:line"),
        StakingWindow(staking_address, enigma_contract_address),
        Window(height=1, char="-", style="class:line"),
        # The 'body', like defined above.
        body,
        Window(height=1, char="-", style="class:line"),
        Window(height=2, char=" ", style="class:line"),
        # ConditionalContainer

        search_field,
        input_field,
        output_field,
    ]),
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1),
        )
    ],
)


# noinspection PyTypeChecker
layout = Layout(root_container, focused_element=input_field)


def show_message(title, text):
    async def coroutine():
        dialog = MessageDialog(title, text, kb)
        await show_dialog_as_float(dialog)

    ensure_future(coroutine())


async def show_dialog_as_float(dialog):
    """Coroutine"""
    float_ = Float(content=dialog)
    if len(root_container.floats) < 2:
        root_container.floats.insert(0, float_)

        app = get_app()

        focused_before = app.layout.current_window
        app.layout.focus(dialog)
        result = await dialog.future
        app.layout.focus(focused_before)

        if float_ in root_container.floats:
            root_container.floats.remove(float_)

        return result

#  ************* Long lived actions ***************** #


async def do_get_ethereum_address():
    global ethereum_address
    while True:
        try:
            ethereum_address.text = await node_actions.get_eth_address()
        except Exception:
            ethereum_address.text = "N/A"
        await asyncio.sleep(5)


async def do_get_staking_address():
    global staking_address, output_field
    while True:
        try:
            staking_address.text = await node_actions.get_staking_address()
        except Exception as e:
            staking_address.text = "N/A"
            # output_field.text = str(e)
        await asyncio.sleep(5)


async def do_get_status():
    global node_status_buf
    new_status = 'Down'
    prev_status = ''
    rotated = ''
    prev_status = 'Down'
    while True:
        try:
            new_status = await node_actions.get_status()
            if prev_status == new_status:
                rotated = rotate_loading_dots(rotated)
                node_status_buf.text = rotated
            else:
                prev_status = new_status
                rotated = new_status
                node_status_buf.text = rotated
        except Exception as e:
            node_status_buf.text = "N/A"
            # output_field.text = str(e)
        await asyncio.sleep(1)


def do_get_balance():
    global balance
    balance_buff.text = "N/A"
    while True:
        try:
            if ethereum_address.text != 'N/A':
                balance = ethereum.balance(ethereum_address.text)
                balance_buff.text = str(balance) + ' ETH'
        except Exception as e:
            output_field.text = str(e)
        time.sleep(5)


async def do_get_peers():
    global peers
    while True:
        try:
            connections = await node_actions.get_connections()
            peers.text = connections[1:-1] + '/50 Peers'
        except Exception as e:
            peers.text = "0/50 Peers"
            # output_field.text = str(e)
        await asyncio.sleep(1)

#  ************* Long lived actions ***************** #

style = example_style


async def main():
    app = Application(layout=layout, full_screen=True, key_bindings=kb, style=style)
    worker = Thread(target=do_get_balance, args=(), daemon=True)
    worker.start()

    # read the staking address so we know if we already initialized or not
    try:
        staking_address.text = await node_actions.get_staking_address()
    except FileNotFoundError:
        staking_address.text = "N/A"

    app.create_background_task(do_get_status())
    app.create_background_task(do_get_ethereum_address())
    app.create_background_task(do_get_staking_address())
    app.create_background_task(do_get_peers())
    result = await app.run_async()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
