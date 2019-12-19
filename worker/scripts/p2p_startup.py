import os
import json
import pathlib
import time
from typing import Union
from urllib.parse import urlparse

from p2p_node import P2PNode
from bootstrap_loader import BootstrapLoader

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger
from enigma_docker_common.utils import remove_0x
from enigma_docker_common.crypto import open_eth_keystore, address_from_private
from enigma_docker_common.ethereum import EthereumGateway
from enigma_docker_common.faucet_api import get_initial_coins
from enigma_docker_common.enigma import EnigmaTokenContract, EnigmaContract

logger = get_logger('worker.p2p-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
              'CONTRACT_DISCOVERY_ADDRESS', 'KEY_MANAGEMENT_DISCOVERY',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CORE_ADDRESS', 'CORE_PORT', 'CONTRACTS_FOLDER',
              'KEY_MANAGEMENT_ADDRESS', 'FAUCET_URL', 'MINIMUM_ETHER_BALANCE', 'BALANCE_WAIT_TIME', 'MIN_CONFIRMATIONS']

env_defaults = {'K8S': '/root/p2p/config/k8s_config.json',
                'TESTNET': '/root/p2p/config/testnet_config.json',
                'MAINNET': '/root/p2p/config/mainnet_config.json',
                'COMPOSE': '/root/p2p/config/compose_config.json'}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')

is_bootstrap = os.getenv('BOOTSTRAP', '')
log_level = os.getenv('LOG_LEVEL', 'info')

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
                    eth_node: str) -> bool:
    eth_gateway = EthereumGateway(eth_node)
    cur_balance = float(eth_gateway.balance(account))
    if min_ether > cur_balance:
        logger.info(f'Ethereum balance {cur_balance} is less than the minimum amount {min_ether} ETH required to start '
                    f'the worker. Please transfer currency to the worker account: {account} and restart the worker')
        # exit(0)
        return False
    return True
    # if allowance_limit > float(erc20.check_allowance(enigma_contract_address, account)):
    #     logger.info(f'{currency} balance is less than the minimum amount {min_ether}ETH required to start the worker'
    #                 f' Please transfer currency to the worker account: {account}')


def address_as_string(addr: Union[bytes, str]) -> str:
    if isinstance(addr, bytes):
        addr = addr.decode()
    return addr


def get_staking_key():
    filename = f'{config["STAKE_KEY_PATH"]}{config["STAKE_KEY_NAME"]}'
    with open(filename, 'r') as f:
        staking_address = f.read()
        return staking_address


def set_status(new_status: str) -> None:
    filename = f'{config["ETH_KEY_PATH"]}{config["STATUS_FILENAME"]}'
    with open(filename, 'w+') as f:
        f.write(new_status)


def get_status() -> str:
    filename = f'{config["ETH_KEY_PATH"]}{config["STATUS_FILENAME"]}'
    status = ''
    with open(filename, 'r+') as f:
        status = f.read()
    return status


def main():
    set_status('Down')
    # todo: unhardcode this
    executable = '/root/p2p/src/cli/cli_app.js'

    logger.info('Setting up worker...')
    logger.info(f'Running for environment: {env}')

    staking_key_dir = config.get('STAKE_KEY_PATH', pathlib.Path.home())

    staking_key = ''
    staking_address = ''

    auto_init = True
    eng_contract: EnigmaContract = None

    provider = Provider(config=config)

    if not is_bootstrap and env in ['TESTNET', 'MAINNET']:
        while True:
            try:
                staking_address = get_staking_key()
                break
            except FileNotFoundError:
                logger.info('Waiting for staking address... Set it up using the CLI')
                set_status('Waiting for setup')
                time.sleep(2)

        logger.info(f'Got staking address {staking_address}')
    set_status('Getting Ethereum Address')
    ethereum_node = config["ETH_NODE_ADDRESS"]

    keystore_dir = config.get('ETH_KEY_PATH', pathlib.Path.home())
    password = config.get('PASSWORD', 'cupcake')  # :)
    private_key, eth_address = open_eth_keystore(keystore_dir, config, password=password, create=True)

    set_status('Reticulating Splines...')

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

    eng_contract_addr = address_as_string(provider.enigma_contract_address)

    logger.info(f'Got address {eng_contract_addr} for enigma contract')

    token_contract_addr = address_as_string(provider.token_contract_address)
    logger.info(f'Got address {token_contract_addr} for token contract')

    erc20_contract = EnigmaTokenContract(config["ETH_NODE_ADDRESS"],
                                         token_contract_addr,
                                         json.loads(provider.enigma_token_abi)['abi'])

    # keystore_dir = config.get('ETH_KEY_PATH', pathlib.Path.home())
    # password = config.get('PASSWORD', 'cupcake')  # :)
    # private_key, eth_address = open_eth_keystore(keystore_dir, config, password=password, create=True)

    #  will not try a faucet if we're in mainnet - also, it should be logged inside
    #  will not try a faucet if we're in a testing environment
    if env in ['COMPOSE', 'K8S']:
        set_status('Compose local setup...')
        staking_key, staking_address = open_eth_keystore(staking_key_dir, config, password=password, create=True)

        try:
            get_initial_coins(eth_address, 'ETH', config)
            get_initial_coins(staking_address, 'ETH', config)
        except RuntimeError as e:
            logger.critical(f'Failed to get enough ETH from faucet to start. Error: {e}')
            exit(-2)
        except ConnectionError as e:
            logger.critical(f'Failed to connect to faucet address. Exiting...')
            exit(-1)

        try:
            get_initial_coins(staking_address, 'ENG', config)
        except RuntimeError as e:
            logger.critical(f'Failed to get enough ENG for staking address - Error: {e}')
            exit(-2)
        except ConnectionError as e:
            logger.critical(f'Failed to connect to faucet address. Exiting...')
            exit(-1)

    # load operating key from configuration -- used in testnet to automatically start bootstrap nodes
    if is_bootstrap and env in ['TESTNET']:
        private_key = config["OPERATING_PRIVATE_KEY"]
        eth_address = erc20_contract.w3.toChecksumAddress(address_from_private(private_key))
        logger.info(f'Loaded private key from config. Staking address is: {eth_address}')
    logger.info(f'private_key={private_key}')
    logger.info(f'public_key={eth_address}')
    # load staking key from configuration -- used in testnet to automatically perform staking for bootstrap nodes
    if is_bootstrap and env in ['TESTNET', 'MAINNET']:
        staking_key = config["STAKING_PRIVATE_KEY"]
        staking_address = address_from_private(staking_key)
        staking_address = erc20_contract.w3.toChecksumAddress(staking_address)
        logger.info(f'Loaded staking private key. Staking address is: {staking_address}')
        # we write to this file as a flag that we don't need to do this again
        # save_to_path(staking_key_dir+config['STAKE_KEY_NAME'], staking_address, flags="w+")

    # perform deposit
    if env in ['K8S', 'COMPOSE'] or (is_bootstrap and env == 'TESTNET'):
        """ Logic for deposit is:

        Staking address                             Operating address 
                     --------setOperatingAddress---------> 

                     <--------------register--------------

                     ---------------deposit-------------->

                     <-----------------login--------------                                       
        """
        # tell the p2p to automatically register -- mostly used for testing environments
        auto_init = True

        #  todo: when we switch this key to be inside the enclave, or encrypted, modify this
        erc20_contract.approve(staking_address,
                               provider.enigma_contract_address,
                               deposit_amount,
                               key=bytes.fromhex(remove_0x(staking_key)))

        val = erc20_contract.check_allowance(staking_address, provider.enigma_contract_address)
        logger.info(f'Current allowance for {provider.enigma_contract_address}, from {staking_address}:'
                    f' {int(val, 16) / (10^8)} ENG')

    while not check_eth_limit(eth_address, float(config["MINIMUM_ETHER_BALANCE"]), ethereum_node):
        set_status('Waiting for ETH...')
        time.sleep(5)

    p = urlparse(ethereum_node)
    hostname = p.hostname
    port = p.port

    # in ganache WS and HTTP are in the same port. In our testnet it isn't (8546 and 8545 respectively)
    if env in ['TESTNET', 'MAINNET']:
        ether_gateway = config.get('ETHEREUM_NODE_ADDRESS_WEBSOCKET', f'ws://{hostname}:{port+1}')
    else:
        ether_gateway = config.get('ETHEREUM_NODE_ADDRESS_WEBSOCKET', f'ws://{hostname}:{port}')
    kwargs = {'staking_address': staking_address,
              'ethereum_key': private_key,
              'public_address': eth_address,
              'ether_node': ether_gateway,
              'abi_path': enigma_abi_path,
              'key_mgmt_node': config["KEY_MANAGEMENT_ADDRESS"],
              'deposit_amount': deposit_amount,
              'bootstrap_address': bootstrap_address,
              'contract_address': eng_contract_addr,
              'health_check_port': config["HEALTH_CHECK_PORT"],
              'min_confirmations': config["MIN_CONFIRMATIONS"],
              'log_level': log_level,
              'auto_init': auto_init}

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
    p2p_runner.start()

    eng_contract = EnigmaContract(config["ETH_NODE_ADDRESS"],
                                  provider.enigma_contract_address,
                                  json.loads(provider.enigma_abi)['abi'])

    logger.info('Waiting for node to finish registering...')
    # for now lets sleep instead of getting confirmations till we move it to web
    while True:
        status = get_status()
        if status.lower() == 'registered':
            break
        time.sleep(10)

    # we perform auto-deposit in testing environment
    if env in ['K8S', 'COMPOSE'] or (is_bootstrap and env == 'TESTNET'):
        set_status('Setting staking address...')
        logger.info(f'Attempting to set operating address -- staking:{staking_address} operating: {eth_address}')
        eng_contract.transact(staking_address, staking_key, 'setOperatingAddress',
                              eng_contract.w3.toChecksumAddress(eth_address))
        logger.info('Set operating address successfully!')

        set_status('Depositing...')
        logger.info(f'Attempting deposit from {staking_address} on behalf of worker {eth_address}')
        eng_contract.transact(staking_address, staking_key, 'deposit',
                              eng_contract.w3.toChecksumAddress(staking_address), deposit_amount)
        logger.info(f'Successfully deposited!')
        time.sleep(60)
        # login the worker (hopefully this works)
        set_status('Logging in...')
        if p2p_runner.login():
            set_status('Running')
        else:
            set_status('Failed to login - See logs')

    set_status('Waiting for login...')
    logger.info('Waiting for deposit & login...')

    while not p2p_runner.kill_now:
        # snooze
        time.sleep(2)
    set_status('Down')


if __name__ == '__main__':
    main()




