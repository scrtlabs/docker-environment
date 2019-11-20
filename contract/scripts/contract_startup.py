# Environment options: LOCAL, K8S, TESTNET, MAINNET
import logging
import sys
import os
from web3.auto import w3 as auto_w3

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger


logger = get_logger(__file__)

# required configuration parameters -- these can all be overridden as environment variables
required = [
              # required by provider AND locally
              'PRINCIPAL_ADDRESS_PATH', 'CONTRACT_DISCOVERY_ADDRESS',
              'KEY_MANAGEMENT_DISCOVERY']

env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}


def save_to_path(path, file):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w+') as f:
        f.write(file)


if __name__ == '__main__':
    logger.info('STARTING CONTRACT STARTUP SCRIPT')

    config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
    provider = Provider(config=config)
    logger.info(f'Downloading key management enigma address...')
    addr = provider.principal_address
    addr = auto_w3.toChecksumAddress(addr)
    logger.info(f'Downloaded key management enigma address successfully -- {addr}')
    save_to_path(config['PRINCIPAL_ADDRESS_PATH'], addr)
