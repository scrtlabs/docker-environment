#!/usr/bin/env python3
"""
This script uses the enigma provider class to identify all the network parameters used by the salad client,
and writes them to the salad client's `.env` file.
"""

import typing
import os
import socket

from time import sleep

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger

logger = get_logger('salad-client-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
    # defaults in local config file
    'CONTRACT_DISCOVERY_ADDRESS',
    'ENG_NODE_ADDRESS',
    'ENG_NODE_PORT',
    'ETH_NODE_PORT',
    'ETH_NODE_ADDRESS',
    'OPERATOR_HOST',
    'OPERATOR_PORT',
    'MONGO_URL',
    'DB_NAME',
    'KEY_MANAGEMENT_DISCOVERY',
]

env_defaults = {
    'K8S': 'config/k8s_config.json',
    'TESTNET': 'config/testnet_config.json',
    'MAINNET': 'config/mainnet_config.json',
    'COMPOSE': 'config/compose_config.json'
}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')

try:
    config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
except (ValueError, IOError) as e:
    logger.critical(f'encountered unexpected error while configuring the salad client: {e!r}')
    raise


def parse_env_file(file: typing.Iterable[typing.Text]) -> dict:
    """Parse a .env file to a dict"""
    return {var: val for var, val in (
        line.rstrip().split('=', 2)
        for line
        in file
        if not line.startswith('#')
    )}


def dump_env_file(env_vars: dict, file: typing.TextIO) -> None:
    file.writelines(f'{key}={value}\n' for key, value in env_vars.items())


def wait_for_operator_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = 1
    while result != 0:
        print(f'Waiting for the operator server to start at {config["OPERATOR_HOST"]}:{config["OPERATOR_PORT"]}')
        result = sock.connect_ex((config['OPERATOR_HOST'], int(config['OPERATOR_PORT'])))
        sleep(5)


def main():
    wait_for_operator_server()

    # parse, modify, and rewrite the .env file
    path = '.env'
    with open(path, 'r') as file:
        env_vars = parse_env_file(file)

    for env_var, config_var in {
        'ETH_HOST': 'ETH_NODE_ADDRESS',
        'ENIGMA_HOST': 'ENG_NODE_ADDRESS',
        'OPERATOR_HOST': 'OPERATOR_HOST',
        'ETH_PORT': 'ETH_NODE_PORT',
        'ENIGMA_PORT': 'ENG_NODE_PORT',
        'WS_PORT': 'OPERATOR_PORT',
        'MONGO_URL': 'MONGO_URL',
    }.items():
        env_vars[env_var] = config[config_var]

    with open(path, 'w') as file:
        dump_env_file(env_vars, file)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f'encountered unexpected error while configuring the salad client: {e}')
        raise
