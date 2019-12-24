from prompt_toolkit.layout.containers import VSplit, Window, HSplit, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
)


def peers(peers_txt: Buffer):
    return Window(BufferControl(buffer=peers_txt), align=WindowAlign.CENTER)


def get_title_text():
    return 'Enigma Status'


def p2p_status(peers_buf: Buffer):
    return VSplit([
        ConditionalContainer(
            Window(content=FormattedTextControl([("class:connected", "Connected"), ]), align=WindowAlign.CENTER),
            filter=Condition(lambda: peers_buf.text != '0/50 Peers')
        ),
        ConditionalContainer(
            Window(content=FormattedTextControl([("class:error", "Not Connected"), ]), align=WindowAlign.CENTER),
            filter=Condition(lambda: peers_buf.text == '0/50 Peers',)
        ),
        # A vertical line in the middle. We explicitly specify the width, to
        # make sure that the layout engine will not try to divide the whole
        # width by three for all these windows. The window will simply fill its
        # content by repeating this character.
        Window(width=1, char='|'),

        peers(peers_buf), ])


def node_status(buff):
    return Window(BufferControl(buffer=buff), align=WindowAlign.CENTER)


def EnigmaWindow(buff: Buffer, peers_buff: Buffer):  # pylint: disable=R0801
    return HSplit([
        Window(height=1, content=FormattedTextControl(get_title_text), align=WindowAlign.CENTER, ),
        VSplit([
            HSplit([
                Window(height=1, char="=", style="class:line"),
                Window(height=1, content=FormattedTextControl("Network Status"), align=WindowAlign.CENTER),
                p2p_status(peers_buff),
                Window(height=1, char="=", style="class:line"),
            ]),
            Window(width=2, char='||'),
            HSplit([
                Window(height=1, char="=", style="class:line"),
                Window(height=1, content=FormattedTextControl("Node Status"), align=WindowAlign.CENTER),
                node_status(buff),
                Window(height=1, char="=", style="class:line"),
            ])
        ])

    ], height=5)
