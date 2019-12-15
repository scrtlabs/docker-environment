#!/usr/bin/env python3
"""
This script uses the enigma provider class to identify all the network parameters used by the operator,
and writes them to the operator's `.env` file.
"""

import os
import typing

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger

logger = get_logger('operator-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
    # defaults in local config file
    'CONTRACT_DISCOVERY_ADDRESS',
    'ENG_NODE_ADDRESS',
    'ENG_NODE_PORT',
    'ETH_NODE_PORT',
    'ETH_NODE_ADDRESS',
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
    logger.critical(f'encountered unexpected error while configuring the operator: {e!r}')
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


def main():
    provider = Provider(config)
    logger.info('fetching deployed Ethereum addresses for Enigma and Enigma Token contracts')
    enigma_contract_address = provider.enigma_contract_address
    enigma_token_contract_address = provider.token_contract_address

    # parse, modify, and rewrite the .env files
    for path in ['.env', 'operator/.env']:
        with open(path, 'r') as file:
            env_vars = parse_env_file(file)

        for env_var, config_var in {
            'ETH_HOST': 'ETH_NODE_ADDRESS',
            'ENIGMA_HOST': 'ENG_NODE_ADDRESS',
            'MONGO_URL': 'MONGO_URL',
            'ETH_PORT': 'ETH_NODE_PORT',
            'ENIGMA_PORT': 'ENG_NODE_PORT',
            'DB_NAME': 'DB_NAME',
        }.items():
            env_vars[env_var] = config[config_var]

        env_vars['ENIGMA_CONTRACT_ADDRESS'] = enigma_contract_address
        env_vars['ENIGMA_TOKEN_CONTRACT_ADDRESS'] = enigma_token_contract_address

        with open(path, 'w') as file:
            dump_env_file(env_vars, file)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f'encountered unexpected error while configuring the operator: {e}')
        raise
