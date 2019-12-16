#!/usr/bin/python3

import time
import os
from asyncio import ensure_future
import asyncio
from pathlib import Path
from prompt_toolkit import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from pyfiglet import figlet_format
from prompt_toolkit.widgets import SearchToolbar, TextArea
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.widgets import Frame

from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
    FloatContainer
)

from prompt_toolkit.shortcuts import input_dialog, message_dialog
from enigma_docker_common.config import Config
from ethereum import EthereumGateway
from threading import Thread

from worker_interface import WorkerInterface

from enigma_window import enigma_window
from ethereum_window import ethereum_window
from staking_window import staking_window

from components import TextInputDialog

env_defaults = {'K8S': f'{Path.home() / "p2p" / "config" / "k8s_config.json"}',
                'TESTNET': f'{Path.home() / "p2p" / "config" / "testnet_config.json"}',
                'MAINNET': f'{Path.home() / "p2p" / "config" / "mainnet_config.json"}',
                'COMPOSE': f'{Path.home() / "p2p" / "config" / "compose_config.json"}'}

try:
    config = Config(config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
except (ValueError, IOError):
    exit(1)

ethereum = EthereumGateway(config['ETH_NODE_ADDRESS'])

""" Flow: Setup - input staking address, generate eth, transfer funds (balance > 0.1), register, wait for staker to do stuff, login """

# noinspection PyUnboundLocalVariable
worker_if = WorkerInterface(config=config)
peers = Buffer()
peers.text = "0"
ethereum_address = Buffer()  # Editable buffer.
staking_address = Buffer()
balance_buff = Buffer()
balance = 0
staking_address.text = "N/A"
ethereum_address.text = "N/A"
balance_buff.text = "N/A"

eng_txt = figlet_format("Enigma Secret Node", font="slant")

kb = KeyBindings()
node_status_buf = Buffer()
node_status_buf.text = "N/A"


@kb.add('c-c')
def exit_(event):
    """
    Pressing Ctrl-C will exit the user interface.

    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    """
    event.app.exit()


def get_title_text():
    return [
        ("class:title", eng_txt),
        ("class:title", " (Press [Ctrl-C] to quit.)"),
    ]


body = ConditionalContainer(VSplit([
    enigma_window(node_status_buf, peers),

    # A vertical line in the middle. We explicitly specify the width, to
    # make sure that the layout engine will not try to divide the whole
    # width by three for all these windows. The window will simply fill its
    # content by repeating this character.
    Window(width=2, char='||'),

    ethereum_window(balance_buff, ethereum_address),
    # Window(content=BufferControl(buffer=buffer1)),

]), filter=Condition(lambda: staking_address.text != 'N/A'))

completer = ["help", "exit", "register", "login", "logout"]


def get_help_text():
    if staking_address.text == 'N/A':
        help_text = """
        Welcome to the Enigma Management Tool! To initiate the node, use the "setup" command. 
        """
    else:
        help_text = f'Welcome to the Enigma Management Tool! Try one of our commands: {completer}'
    return help_text

search_field = SearchToolbar()  # For reverse search.

output_field = TextArea(style="class:output-field", text=get_help_text())
input_field = TextArea(
    height=1,
    prompt=">>> ",
    style="class:input-field",
    multiline=False,
    wrap_lines=False,
    search_field=search_field,
)


# Attach accept handler to the input field. We do this by assigning the
# handler to the `TextArea` that we created earlier. it is also possible to
# pass it to the constructor of `TextArea`.
# NOTE: It's better to assign an `accept_handler`, rather then adding a
#       custom ENTER key binding. This will automatically reset the input
#       field and add the strings to the history.


def can_register():
    return balance <= 0.05


def accept(buff):
    txt = input_field.text

    # Evaluate "calculator" expression.

    async def coroutine():
        try:
            output = ''
            if txt == 'exit':
                # to properly handle exit events we create a fake object that matches what an event expects
                # There's probably a better way to do this but I don't care enough to look
                class Object:
                    pass
                event_mock = Object()
                event_mock.app = get_app()
                # noinspection PyTypeChecker
                exit_(event_mock)

            elif txt == 'setup':
                open_dialog = TextInputDialog(
                    title="Secret Node Setup",
                    label_text="Enter staking address",
                )
                staking = await show_dialog_as_float(open_dialog)
                await worker_if.set_staking_address(staking)
                output = f"Successfully set staking address!"

            elif txt in worker_if.available_actions:
                if txt == 'register':
                    if can_register():
                        output = 'Not enough ETH in account to register. Please deposit at least 0.1 ETH'
                    else:
                        output = await worker_if.do_action(txt)
                else:
                    output = await worker_if.do_action(txt)

            else:
                output = f"unsupported + {input_field.text}"
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
        ),
        # Horizontal separator.
        Window(height=1, char="-", style="class:line"),
        staking_window(staking_address),
        Window(height=1, char="-", style="class:line"),
        # The 'body', like defined above.
        body,
        Window(height=1, char="-", style="class:line"),
        # ConditionalContainer

        search_field,
        input_field,
        output_field
    ]),
    floats=[]
)

# noinspection PyTypeChecker
layout = Layout(root_container, focused_element=input_field)


async def show_dialog_as_float(dialog):
    " Coroutine. "
    float_ = Float(content=dialog)
    root_container.floats.insert(0, float_)

    app = get_app()

    focused_before = app.layout.current_window
    app.layout.focus(dialog)
    result = await dialog.future
    app.layout.focus(focused_before)

    if float_ in root_container.floats:
        root_container.floats.remove(float_)

    return result


async def do_get_ethereum_address():
    global ethereum_address
    while True:
        try:
            ethereum_address.text = await worker_if.get_eth_address()
        except Exception:
            ethereum_address.text = "N/A"
        await asyncio.sleep(5)


async def do_get_staking_address():
    global staking_address, output_field
    while True:
        try:
            staking_address.text = await worker_if.get_staking_address()
        except Exception as e:
            staking_address.text = "N/A"
            # output_field.text = str(e)
        await asyncio.sleep(5)


async def do_get_status():
    global node_status_buf
    while True:
        try:
            node_status_buf.text = await worker_if.get_status()
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
            connections = await worker_if.get_connections()
            peers.text = connections[1:-1] + '/50 Peers'
        except Exception as e:
            peers.text = "0/50 Peers"
            # output_field.text = str(e)
        await asyncio.sleep(1)


async def main():
    app = Application(layout=layout, full_screen=True, key_bindings=kb)
    worker = Thread(target=do_get_balance, args=(), daemon=True)
    worker.start()
    app.create_background_task(do_get_status())
    app.create_background_task(do_get_ethereum_address())
    app.create_background_task(do_get_staking_address())
    app.create_background_task(do_get_peers())
    result = await app.run_async()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
