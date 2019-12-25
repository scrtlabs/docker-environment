import os
import json

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger


logger = get_logger('client-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = ['ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CONTRACTS_FOLDER', 'FAUCET_URL',
            'WORKER_URL', 'PROXY_PORT']

# local path to where we save the private key/public key if we generate it locally
KEY_PAIR_PATH = os.path.dirname(os.path.dirname(__file__))


def save_to_path(path, file):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb+') as f:
        f.write(file)


if __name__ == '__main__':

    logger.info('STARTING P2P STARTUP')
    env = os.getenv('ENIGMA_ENV', 'COMPOSE')
    config = Config(required=required)
    provider = Provider(config=config)

    # *** Load parameters from config

    contracts_folder_path = config['CONTRACTS_FOLDER']
    enigma_abi_filename = config['ENIGMA_CONTRACT_FILE_NAME']
    eth_node_address = f'{config["ETH_NODE_ADDRESS"]}'

    # Load Enigma.json ABI
    enigma_contract_abi = provider.enigma_abi

    if config.get('SGX_MODE', 'SW') == 'SW':
        enigma_abi_filename = 'EnigmaSimulation.json'

    contract_abi_path = contracts_folder_path + enigma_abi_filename
    save_to_path(contract_abi_path, enigma_contract_abi)

    token_contract_abi = json.loads(provider.enigma_token_abi)
    token_contract_address = provider.token_contract_address

    eng_contract_addr = provider.enigma_contract_address
    logger.info(f'Got address {eng_contract_addr} for enigma contract')

    addresses = {'contract': eng_contract_addr,
                 'token': token_contract_address,
                 'eth_node': f'{eth_node_address}',
                 'proxy': f'{config["WORKER_URL"]}:{config["PROXY_PORT"]}'}

    if env == 'COMPOSE':
        addresses['voting'] = provider.voting_contract_address
        addresses['sample'] = provider.sample_contract_address

    save_to_path(contracts_folder_path+'addresses.json', json.dumps(addresses).encode())
