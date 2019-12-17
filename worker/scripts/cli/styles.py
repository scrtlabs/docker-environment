from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import ANSI

example_style = Style.from_dict(
    {
        "connected": "#00ff00",
#       "connected frame-label": "bg:#ffffff #000000",
#       "connected.body": "bg:#000000 #00ff00",
#       "connected shadow": "bg:#00aa00",
        "error": "#ff0000",
        "logo": "#8844ff italic bold",
        "logo shadow": "bg:#00aa00"
    }
)

class Color:
    colors = {
        'BLACK': '\033[0;30m',
        'RED': '\033[0;31m',
        'GREEN': '\033[0;32m',
        'BROWN': '\033[0;33m',
        'BLUE': '\033[0;34m',
        'PURPLE': '\033[0;35m',
        'CYAN': '\033[0;36m',
        'GREY': '\033[0;37m',

        'DARK_GREY': '\033[1;30m',
        'LIGHT_RED': '\033[1;31m',
        'LIGHT_GREEN': '\033[1;32m',
        'YELLOW': '\033[1;33m',
        'LIGHT_BLUE': '\033[1;34m',
        'LIGHT_PURPLE': '\033[1;35m',
        'LIGHT_CYAN': '\033[1;36m',
        'WHITE': '\033[1;37m',

        'RESET': "\033[0m"
    }
    @classmethod
    def color(cls, color, text):
        try:
            return f'{cls.colors[color.upper()]}{text}{cls.colors["RESET"]}'
        except KeyError:
            raise ValueError(f'Unknown color: {color}')


colorize = Color().color

