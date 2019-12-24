from asyncio import Future

from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import Button, Dialog, Label


class MessageDialog:
    # pylint: disable=duplicate-code
    def __init__(self, title, text, kb=KeyBindings()):
        self.future = Future()
        self.close_once = False

        @kb.add('escape')
        def set_done(event=''):  # pylint: disable=unused-argument
            if not self.close_once:
                self.close_once = True
                self.future.set_result(None)

        ok_button = Button(text="OK", handler=set_done)

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text), ]),
            buttons=[ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog
