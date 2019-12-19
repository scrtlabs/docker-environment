from prompt_toolkit.layout.containers import VSplit, Window, HSplit, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer


def get_title_text():
    return 'Staking Address'


def staking_address(staking_address_txt: Buffer):
    return Window(content=BufferControl(buffer=staking_address_txt), align=WindowAlign.CENTER)


def StakingWindow(staking_address_txt: Buffer):
    body = VSplit([
        # todo: figure out how to pack
        Window(width=2, char='||'),
        HSplit([
            # Horizontal separator.
            # The 'body', like defined above.
            Window(height=1, content=FormattedTextControl(get_title_text()), align=WindowAlign.CENTER),
            staking_address(staking_address_txt),
        ], height=3),
        Window(width=2, char='||'),
        ])

    return body

