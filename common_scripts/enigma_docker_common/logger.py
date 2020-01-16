import os
import sys
import logging


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""

    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BROWN = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREY = '\033[0;37m'

    DARK_GREY = '\033[1;30m'
    LIGHT_RED = '\033[1;31m'
    LIGHT_GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    LIGHT_BLUE = '\033[1;34m'
    LIGHT_PURPLE = '\033[1;35m'
    LIGHT_CYAN = '\033[1;36m'
    WHITE = '\033[1;37m'

    RESET = "\033[0m"

    @classmethod
    def _colorize(cls, color):
        return f'[%(asctime)25s] {color}%(levelname)7s{cls.RESET} [%(name)s] %(funcName)s:%(lineno)s -- %(message)s'

    @classmethod
    def get_formats(cls):
        return {
            logging.DEBUG: cls._colorize(cls.GREY),
            logging.INFO: cls._colorize(cls.GREEN),
            logging.WARNING: cls._colorize(cls.YELLOW),
            logging.ERROR: cls._colorize(cls.RED),
            logging.CRITICAL: cls._colorize(cls.LIGHT_RED)
        }

    def format(self, record):
        log_fmt = self.get_formats().get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(logger_name: str = 'enigma') -> logging.Logger:
    logger = logging.getLogger(logger_name)
    loglevel = getattr(logging, os.getenv('LOG_LEVEL', '').upper(), logging.INFO)
    if not isinstance(loglevel, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logger.setLevel(level=loglevel)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = CustomFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
