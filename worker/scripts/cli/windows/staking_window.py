from prompt_toolkit.layout.containers import VSplit, Window, HSplit, WindowAlign, HorizontalAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.buffer import Buffer


def staking_title_text():
    return 'Staking Address'


def contract_title_text():
    return 'Enigma Contract Address'


def erc20_title_text():
    return 'ERC-20 Contract Address'


def address_window(staking_address_txt: Buffer):
    return Window(content=BufferControl(buffer=staking_address_txt), align=WindowAlign.CENTER, height=1, width=65)


def enimga_contract_address(contract_address: str):
    return Window(height=1, content=FormattedTextControl(contract_address), align=WindowAlign.CENTER)


def StakingWindow(staking_address_txt: Buffer, contract_address: str, token_contract: str):
    body = VSplit([
        # todo: figure out how to pack
        Window(width=2, char='||'),
        HSplit([
            # Horizontal separator.
            # The 'body', like defined above.
            Window(height=1, content=FormattedTextControl(staking_title_text()), align=WindowAlign.CENTER),
            address_window(staking_address_txt),
        ], height=2),
        Window(width=2, char='||', align=WindowAlign.CENTER),
        HSplit([
            # Horizontal separator.
            # The 'body', like defined above.
            Window(height=1, content=FormattedTextControl(contract_title_text()), align=WindowAlign.CENTER),
            enimga_contract_address(contract_address),
        ], height=2),
        Window(width=2, char='||', align=WindowAlign.CENTER),
        HSplit([
            # Horizontal separator.
            # The 'body', like defined above.
            Window(height=1, content=FormattedTextControl(erc20_title_text()), align=WindowAlign.CENTER),
            enimga_contract_address(token_contract),
        ], height=2),
        Window(width=2, char='||'),
        ], align=HorizontalAlign.CENTER)

    return body

