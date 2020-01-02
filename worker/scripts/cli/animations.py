import asyncio
from prompt_toolkit.buffer import Buffer


async def animate_loading_buffer(buf: Buffer):
    buf.text = buf.text + '.'
    # output = worker_if.do_action(txt)
    await asyncio.sleep(0.2)
    buf.text = buf.text + '..'
    await asyncio.sleep(0.2)
    buf.text = buf.text + '...'
    await asyncio.sleep(0.2)


async def animate_loading_text(buf: Buffer, text):
    buf.text = text + '.'
    # output = worker_if.do_action(txt)
    await asyncio.sleep(0.2)
    buf.text = text + '..'
    await asyncio.sleep(0.2)
    buf.text = text + '...'
    await asyncio.sleep(0.2)


def rotate_loading_dots(text):
    num_of_dots = text[-3:].count('.')
    if num_of_dots == 0:
        return text
    new_dots = '.' * ((num_of_dots + 1) % 4) or '.'
    return text[:-num_of_dots] + new_dots
