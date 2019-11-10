import os
import json
import pathlib

from p2p_node import P2PNode

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger
from enigma_docker_common.crypto import get_eth_address
from enigma_docker_common.blockchain import get_initial_coins
from enigma_docker_common.enigma import EnigmaTokenContract

logger = get_logger('worker.p2p-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
              'CONTRACT_DISCOVERY_PORT', 'CONTRACT_DISCOVERY_ADDRESS',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CORE_ADDRESS', 'CORE_PORT', 'CONTRACTS_FOLDER',
              'KEY_MANAGEMENT_ADDRESS', 'FAUCET_URL', 'MINIMUM_ETHER_BALANCE', 'BALANCE_WAIT_TIME']
env_defaults = {'K8S': './p2p/config/k8s_config.json',
                'TESTNET': './p2p/config/testnet_config.json',
                'MAINNET': './p2p/config/mainnet_config.json',
                'COMPOSE': './p2p/config/compose_config.json'}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')

is_bootstrap = os.getenv('BOOTSTRAP', '')

if not is_bootstrap:
    required.append('BOOTSTRAP_ADDRESS')

config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])

# local path to where we save the private key/public key if we generate it locally
KEY_PAIR_PATH = os.path.dirname(os.path.dirname(__file__))


def save_to_path(path, file, flags='wb+'):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, flags) as f:
        f.write(file)


if __name__ == '__main__':
    # todo: unhardcode this
    executable = '/root/p2p/src/cli/cli_app.js'

    logger.info('Setting up worker...')
    logger.info(f'Running for environment: {env}')

    provider = Provider(config=config)

    # *** Load parameters from config
    enigma_abi_path = f'{config["CONTRACTS_FOLDER"]}{config["ENIGMA_CONTRACT_FILE_NAME"]}'
    # bootstrap params
    if is_bootstrap:
        bootstrap_id = config.get('BOOTSTRAP_ID', 'B1')
        peer_name = ''
    else:
        peer_name = config.get('PEER_NAME', 'peer1')
        bootstrap_id = ''

    deposit_amount = int(config['DEPOSIT_AMOUNT'])
    eth_key_path = config['ETH_KEY_PATH']

    # Load Enigma.json ABI
    save_to_path(enigma_abi_path, provider.enigma_abi)

    eng_contract_addr = provider.enigma_contract_address
    logger.info(f'Got address {eng_contract_addr} for enigma contract')

    PRIV_KEY_FILENAME = "id_rsa"
    PUB_KEY_FILENAME = "id_rsa.pub"

    pubkey_path = f'{eth_key_path}{PUB_KEY_FILENAME}'
    privkey_path = f'{eth_key_path}{PRIV_KEY_FILENAME}'

    login_and_deposit = False

    if config.get('FORCE_NEW_ETH_ADDR', False):
        logger.info('Generating new Ethereum address')
        private_key, eth_address = get_eth_address()
        save_to_path(privkey_path, private_key, 'w+')
        save_to_path(pubkey_path, eth_address, 'w+')
    else:  # try to open address from filesystem
        try:
            with open(pubkey_path, 'r') as f:
                eth_address = f.read()
            with open(privkey_path, 'r') as f:
                private_key = f.read()

            logger.info(f'Loaded key from local filesystem, ethereum address: {eth_address}')

        except FileNotFoundError:
            logger.info('Ethereum address not found. Generating new address...')
            private_key, eth_address = get_eth_address()
            save_to_path(privkey_path, private_key, 'w+')
            save_to_path(pubkey_path, eth_address, 'w+')
            logger.info(f'Done! New address is {eth_address}')
            # todo: add a check it was properly saved

    #  will not try a faucet if we're in mainnet - also, it should be logged inside
    try:
        get_initial_coins(eth_address, 'ETH', config)
        get_initial_coins(eth_address, 'ENG', config)
    except RuntimeError as e:
        logger.critical(f'Failed to get enough ETH or ENG to start - {e}')
        exit(-2)
    except ConnectionError as e:
        logger.critical(f'Failed to connect to remote address: {e}')
        exit(-1)

    if env in ['COMPOSE', 'TESTNET', 'K8S']:

        # tell the p2p to automatically log us in and do the deposit for us
        login_and_deposit = True

        erc20_contract = EnigmaTokenContract(config["ETH_NODE_ADDRESS"],
                                             provider.token_contract_address,
                                             json.loads(provider.enigma_token_abi)['abi'])

        # todo: when we switch this key to be inside the enclave, or encrypted, modify this
        erc20_contract.approve(eth_address,
                               provider.enigma_contract_address,
                               deposit_amount,
                               private_key=bytes.fromhex(private_key[2:]))

        val = erc20_contract.check_allowance(eth_address, provider.enigma_contract_address)
        logger.info(f'Current allowance for {provider.enigma_contract_address}, from {eth_address}: {val} ENG')

    if is_bootstrap:
        p2p_runner = P2PNode(bootstrap=True,
                             bootstrap_id=bootstrap_id,
                             ethereum_key=private_key,
                             contract_address=eng_contract_addr,
                             public_address=eth_address,
                             ether_node=config["ETH_NODE_ADDRESS"],
                             abi_path=enigma_abi_path,
                             key_mgmt_node=config["KEY_MANAGEMENT_ADDRESS"],
                             deposit_amount=deposit_amount,
                             login_and_deposit=login_and_deposit)
    else:
        bootstrap_node = config['BOOTSTRAP_ADDRESS']
        p2p_runner = P2PNode(bootstrap=False,
                             peer_name=peer_name,
                             ethereum_key=private_key,
                             contract_address=eng_contract_addr,
                             public_address=eth_address,
                             ether_node=config["ETH_NODE_ADDRESS"],
                             key_mgmt_node=config["KEY_MANAGEMENT_ADDRESS"],
                             abi_path=enigma_abi_path,
                             bootstrap_address=bootstrap_node,
                             deposit_amount=deposit_amount,
                             login_and_deposit=login_and_deposit)

    # Setting workdir to the base path of the executable, because everything is fragile
    os.chdir(pathlib.Path(executable).parent)

    p2p_runner.run()
