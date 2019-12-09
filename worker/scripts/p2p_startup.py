import os
import json
import pathlib

from p2p_node import P2PNode
from bootstrap_loader import BootstrapLoader

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger
from enigma_docker_common.crypto import open_eth_keystore
from enigma_docker_common.ethereum import EthereumGateway
from enigma_docker_common.faucet_api import get_initial_coins
from enigma_docker_common.enigma import EnigmaTokenContract

logger = get_logger('worker.p2p-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
              'CONTRACT_DISCOVERY_ADDRESS', 'KEY_MANAGEMENT_DISCOVERY',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CORE_ADDRESS', 'CORE_PORT', 'CONTRACTS_FOLDER',
              'KEY_MANAGEMENT_ADDRESS', 'FAUCET_URL', 'MINIMUM_ETHER_BALANCE', 'BALANCE_WAIT_TIME', 'MIN_CONFIRMATIONS']

env_defaults = {'K8S': './p2p/config/k8s_config.json',
                'TESTNET': './p2p/config/testnet_config.json',
                'MAINNET': './p2p/config/mainnet_config.json',
                'COMPOSE': './p2p/config/compose_config.json'}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')

is_bootstrap = os.getenv('BOOTSTRAP', '')

try:
    config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
except (ValueError, IOError):
    exit(-1)

# local path to where we save the private key/public key if we generate it locally
KEY_PAIR_PATH = os.path.dirname(os.path.dirname(__file__))


def save_to_path(path, file, flags='wb+'):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, flags) as f:
        f.write(file)


def check_eth_limit(account: str,
                    min_ether: float,
                    eth_node: str):
    eth_gateway = EthereumGateway(eth_node)
    cur_balance = float(eth_gateway.balance(account))
    if min_ether > cur_balance:
        logger.info(f'Ethereum balance {cur_balance} is less than the minimum amount {min_ether} ETH required to start '
                    f'the worker. Please transfer currency to the worker account: {account} and restart the worker')
        exit(0)
    # if allowance_limit > float(erc20.check_allowance(enigma_contract_address, account)):
    #     logger.info(f'{currency} balance is less than the minimum amount {min_ether}ETH required to start the worker'
    #                 f' Please transfer currency to the worker account: {account}')


def main():
    # todo: unhardcode this
    executable = '/root/p2p/src/cli/cli_app.js'

    logger.info('Setting up worker...')
    logger.info(f'Running for environment: {env}')

    provider = Provider(config=config)

    ethereum_node = config["ETH_NODE_ADDRESS"]

    # *** Load parameters from config
    enigma_abi_path = f'{config["CONTRACTS_FOLDER"]}{config["ENIGMA_CONTRACT_FILE_NAME"]}'

    bootstrap_id = config.get('BOOTSTRAP_ID', '') if is_bootstrap else ''
    bootstrap_address = config.get('BOOTSTRAP_ADDRESS', '')
    bootstrap_loader = BootstrapLoader(config, bootstrap_id)
    # file must be .json since p2p will try to use require(). Can remove when p2p is changed
    bootstrap_path: str = config['BOOTSTRAP_PATH'] + bootstrap_id
    bootstrap_port: str = config['BOOTSTRAP_PORT']

    # #### bootstrap params #####
    if is_bootstrap:
        logger.info('Loading bootstrap node parameters')
        keyfile = bootstrap_loader.to_json()

        bootstrap_id = bootstrap_loader.address

        # we save the keyfile to disk so we can send it to p2p runner
        bootstrap_path += '.json'
        save_to_path(bootstrap_path, keyfile)

    if not bootstrap_address:  # if bootstrap addresses are not configured, try to pull
        logger.info('Loading bootstrap addresses...')
        bootstrap_address = bootstrap_loader.all_bootstrap_addresses()
        logger.info(f'Got bootstrap addresses: {bootstrap_address}')
    else:
        logger.info(f'Bootstrap addresses already set: {bootstrap_address}')

    deposit_amount = int(config['DEPOSIT_AMOUNT'])

    # Load Enigma.json ABI
    save_to_path(enigma_abi_path, provider.enigma_abi)

    eng_contract_addr = provider.enigma_contract_address
    logger.info(f'Got address {eng_contract_addr} for enigma contract')

    login_and_deposit = False

    keystore_dir = config.get('ETH_KEY_PATH', pathlib.Path.home())
    password = config.get('PASSWORD', 'cupcake')  # :)
    private_key, eth_address = open_eth_keystore(keystore_dir, config, password=password, create=True)
    #  will not try a faucet if we're in mainnet - also, it should be logged inside

    erc20_contract = EnigmaTokenContract(config["ETH_NODE_ADDRESS"],
                                         provider.token_contract_address,
                                         json.loads(provider.enigma_token_abi)['abi'])

    #  will not try a faucet if we're in mainnet - also, it should be logged inside
    if env in ['COMPOSE', 'K8S']:

        staking_key_dir = config.get('STAKE_KEY_PATH', pathlib.Path.home())
        staking_key, staking_address = open_eth_keystore(staking_key_dir, config, password=password, create=True)

        try:
            get_initial_coins(eth_address, 'ETH', config)
            get_initial_coins(staking_address, 'ETH', config)
        except RuntimeError as e:
            logger.critical(f'Failed to get enough ETH to start - {e}')
            exit(-2)
        except ConnectionError as e:
            logger.critical(f'Failed to connect to remote address: {e}')
            exit(-1)

        try:
            get_initial_coins(staking_address, 'ENG', config)
        except RuntimeError as e:
            logger.critical(f'Failed to get enough ENG for staking address - Error: {e}')
            exit(-2)
        except ConnectionError as e:
            logger.critical(f'Failed to connect to remote address: Error: {e}')
            exit(-1)

        # tell the p2p to automatically log us in and do the deposit for us
        login_and_deposit = True

        # todo: when we switch this key to be inside the enclave, or encrypted, modify this
        erc20_contract.approve(staking_address,
                               provider.enigma_contract_address,
                               deposit_amount,
                               key=bytes.fromhex(staking_key[2:]))

        val = erc20_contract.check_allowance(staking_address, provider.enigma_contract_address)
        logger.info(f'Current allowance for {provider.enigma_contract_address}, from {staking_address}: {val} ENG')

        # temp for now till staking address is integrated:
        eth_address = staking_address
        private_key = staking_key

    if env in ['TESTNET', 'MAINNET']:
        staking_address = config["STAKING_ADDRESS"]

    check_eth_limit(eth_address, float(config["MINIMUM_ETHER_BALANCE"]), ethereum_node)

    kwargs = {'ethereum_key': private_key,
              'public_address': eth_address,
              'ether_node': ethereum_node,
              'abi_path': enigma_abi_path,
              'key_mgmt_node': config["KEY_MANAGEMENT_ADDRESS"],
              'deposit_amount': deposit_amount,
              'bootstrap_address': bootstrap_address,
              'contract_address': eng_contract_addr,
              'login_and_deposit': login_and_deposit,
              'health_check_port': config["HEALTH_CHECK_PORT"],
              'min_confirmations': config["MIN_CONFIRMATIONS"]}

    if is_bootstrap:
        p2p_runner = P2PNode(bootstrap=True,
                             bootstrap_id=bootstrap_id,
                             bootstrap_path=bootstrap_path,
                             bootstrap_port=bootstrap_port,
                             **kwargs)
    else:
        p2p_runner = P2PNode(bootstrap=False,
                             **kwargs)

    # Setting workdir to the base path of the executable, because everything is fragile
    os.chdir(pathlib.Path(executable).parent)
    import time
    p2p_runner.start()
    while not p2p_runner.kill_now:
        time.sleep(2)
        # add cleanup here if necessary


if __name__ == '__main__':
    main()




