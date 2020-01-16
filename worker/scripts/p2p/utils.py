import os
import pathlib
import time
from collections import UserDict
from typing import Union

from enigma_docker_common.crypto import open_eth_keystore
from enigma_docker_common.logger import get_logger

logger = get_logger('worker.p2p.utils')


def load_ethereum_keys(config: UserDict):
    """ Will generate keys if they don't exist """
    keystore_dir = config.get('ETH_KEY_PATH', pathlib.Path.home())
    password = config.get('PASSWORD', 'cupcake')  # :)
    return open_eth_keystore(keystore_dir, config, password=password, create=True)


def load_staking_keys(config: UserDict):
    """ Will generate keys if they don't exist """
    staking_key_dir = config.get('STAKE_KEY_PATH', pathlib.Path.home())
    password = config.get('PASSWORD', 'cupcake')  # :)
    return open_eth_keystore(staking_key_dir, config, password=password, create=True)


def wait_for_staking_address(config: UserDict) -> str:
    while True:
        try:
            staking_address = get_staking_address(config)
            return staking_address
        except FileNotFoundError:
            logger.debug('Still waiting for staking address... Set it up using the CLI')
            set_status(config, 'Waiting for setup')
            time.sleep(2)


def save_to_path(path: str, file: Union[bytes, str], flags='wb+'):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, flags) as f:
        f.write(file)


def address_as_string(addr: Union[bytes, str]) -> str:
    if isinstance(addr, bytes):
        addr = addr.decode()
    return addr


def get_staking_address(config: UserDict):
    filename = f'{config["STAKE_KEY_PATH"]}{config["STAKE_KEY_NAME"]}'
    with open(filename, 'r') as f:
        staking_address = f.read()
        return staking_address


def set_status(config, new_status: str) -> None:
    filename = f'{config["ETH_KEY_PATH"]}{config["STATUS_FILENAME"]}'
    with open(filename, 'w+') as f:
        f.write(new_status)


def get_status(config) -> str:
    filename = f'{config["ETH_KEY_PATH"]}{config["STATUS_FILENAME"]}'
    status = ''
    with open(filename, 'r+') as f:
        status = f.read()
    return status
