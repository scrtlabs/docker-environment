#!/usr/bin/env python3
"""
This script uses the enigma provider class to identify all the network parameters used by the operator,
and writes them to the operator's `.env` file.
"""

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger
from enigma_docker_common.provider import Provider
from enigma_docker_common.utils import parse_env_file, dump_env_file

logger = get_logger('operator-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
    # defaults in local config file
    'CONTRACT_DISCOVERY_ADDRESS',
    'MONGO_URL',
    'ENG_NODE_ADDRESS',
    'ENG_NODE_PORT',
    'ETH_NODE_PORT',
    'ETH_NODE_ADDRESS',
    'DB_NAME',
    'KEY_MANAGEMENT_DISCOVERY',
]

try:
    config = Config(required=required)
except (ValueError, IOError) as e:
    logger.critical(f'encountered unexpected error while configuring the operator: {e!r}')
    raise


def main():
    provider = Provider(config)
    logger.info('fetching deployed Ethereum addresses for Enigma and Enigma Token contracts')
    enigma_contract_address = provider.enigma_contract_address
    enigma_token_contract_address = provider.token_contract_address

    # parse, modify, and rewrite the .env files
    for path in ['.env', 'operator/.env']:
        with open(path, 'r') as file:
            envs = parse_env_file(file)

        for env_var, config_var in {
                'ETH_HOST': 'ETH_NODE_ADDRESS',
                'ENIGMA_HOST': 'ENG_NODE_ADDRESS',
                'MONGO_URL': 'MONGO_URL',
                'ETH_PORT': 'ETH_NODE_PORT',
                'ENIGMA_PORT': 'ENG_NODE_PORT',
                'DB_NAME': 'DB_NAME',
                'OPERATOR_ETH_PRIVATE_KEY': 'OPERATOR_ETH_PRIVATE_KEY',
                'SECRET_CONTRACT_BUILD_FOLDER': 'SECRET_CONTRACT_BUILD_FOLDER',
                'SALAD_SMART_CONTRACT_ADDRESS': 'SALAD_SMART_CONTRACT_ADDRESS',
                'SALAD_SECRET_CONTRACT_ADDRESS': 'SALAD_SECRET_CONTRACT_ADDRESS',
                'NETWORK_ID': 'NETWORK_ID',
        }.items():
            envs[env_var] = config[config_var]

        envs['ENIGMA_CONTRACT_ADDRESS'] = enigma_contract_address
        envs['ENIGMA_TOKEN_CONTRACT_ADDRESS'] = enigma_token_contract_address

        with open(path, 'w') as file:
            dump_env_file(envs, file)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(f'encountered unexpected error while configuring the operator: {e}')
        raise
