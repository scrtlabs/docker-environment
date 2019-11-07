import os
import sys
import logging


def get_logger(logger_name: str = 'enigma') -> logging.Logger:
    logger = logging.getLogger(logger_name)
    loglevel = getattr(logging, os.getenv('LOG_LEVEL', '').upper(), logging.INFO)
    if not isinstance(loglevel, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logger.setLevel(level=loglevel)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)-8s %(funcName)s:%(lineno)s -- %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
