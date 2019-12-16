from prompt_toolkit.layout.containers import VSplit, Window, HSplit, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout


def get_title_text():
    return 'Enigma Status'


def p2p_status():
    return VSplit([

        Window(content=FormattedTextControl(text="Connected"), align=WindowAlign.CENTER),

        # A vertical line in the middle. We explicitly specify the width, to
        # make sure that the layout engine will not try to divide the whole
        # width by three for all these windows. The window will simply fill its
        # content by repeating this character.
        Window(width=1, char='|'),

        Window(content=FormattedTextControl(text="2/20 peers"), align=WindowAlign.CENTER),
])


def node_status(buff):
    return VSplit([

        # Window(content=FormattedTextControl(text="Unregistered"), align=WindowAlign.CENTER),
        Window(BufferControl(buffer=buff), align=WindowAlign.CENTER)
        # A vertical line in the middle. We explicitly specify the width, to
        # make sure that the layout engine will not try to divide the whole
        # width by three for all these windows. The window will simply fill its
        # content by repeating this character.
])


def enigma_window(buff):
    body = HSplit([
        Window(
            height=1,
            content=FormattedTextControl(get_title_text),
            align=WindowAlign.CENTER,
        ),
        VSplit([
            HSplit([
                # Horizontal separator.
                Window(height=1, char="=", style="class:line"),
                # The 'body', like defined above.
                Window(height=1, content=FormattedTextControl("Network Status"), align=WindowAlign.CENTER),

                p2p_status(),
                Window(height=1, char="=", style="class:line"),
            ]),
            Window(width=2, char='||'),
            HSplit([
                # Horizontal separator.
                Window(height=1, char="=", style="class:line"),
                # The 'body', like defined above.
                Window(height=1, content=FormattedTextControl("Node Status"), align=WindowAlign.CENTER),

                node_status(buff),
                Window(height=1, char="=", style="class:line"),
            ])
        ])

    ], height=5)

    return body

