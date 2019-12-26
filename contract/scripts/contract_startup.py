# Environment options: LOCAL, K8S, TESTNET, MAINNET
import os

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger
from enigma_docker_common.provider import Provider
from web3.auto import w3 as auto_w3

logger = get_logger(__file__)

# required configuration parameters -- these can all be overridden as environment variables
required = ['PRINCIPAL_ADDRESS_PATH', 'CONTRACT_DISCOVERY_ADDRESS', 'KEY_MANAGEMENT_DISCOVERY']


def save_to_path(path, file):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w+') as f:
        f.write(file)


if __name__ == '__main__':
    logger.info('STARTING CONTRACT STARTUP SCRIPT')

    config = Config(required=required)
    provider = Provider(config=config)
    logger.info(f'Downloading key management enigma address...')
    addr = provider.principal_address
    addr = auto_w3.toChecksumAddress(addr)
    logger.info(f'Downloaded key management enigma address successfully -- {addr}')
    save_to_path(config['PRINCIPAL_ADDRESS_PATH'], addr)
