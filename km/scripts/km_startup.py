# Environment options: COMPOSE, K8S, TESTNET, MAINNET
import os
import json
import subprocess
import pathlib
import threading

from km_address_server import run

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger
from enigma_docker_common.crypto import open_eth_keystore
from enigma_docker_common.faucet_api import get_initial_coins

logger = get_logger('key_management.startup')


required = [  # global environment setting
              'ENIGMA_ENV',
              # required by provider AND locally
              'CONTRACT_DISCOVERY_ADDRESS', 'KEY_MANAGEMENT_DISCOVERY',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'CONTRACTS_FOLDER', 'DEFAULT_CONFIG_PATH', 'FAUCET_URL',
              'KEYPAIR_FILE_NAME', 'TEMP_CONFIG_PATH', "MINIMUM_ETHER_BALANCE", "MINIMUM_ENG_BALANCE",
]

env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')
SGX_MODE = os.getenv('SGX_MODE', 'HW')


def generate_config_file(app_config: dict, default_config_path: str, config_file_path: str) -> None:
    """ Generates a configuration file based on environment variables set in env_map variable above """
    with open(default_config_path, 'r') as f:
        default_config = json.load(f)

    # for each value either use the environment variable set as key.upper() or take the value from the default config
    # also, if the value can represent an integer, use that representation instead of a string
    temp_conf = {k: int(app_config.get(k.upper(), v))
                 if app_config.get(k.upper(), 'false').isdigit()
                 else app_config.get(k.upper(), v)
                 for k, v in default_config.items()}

    # Changing the name so it's consistent with the one in p2p
    temp_conf['CONFIRMATIONS'] = int(app_config['MIN_CONFIRMATIONS']) if 'MIN_CONFIRMATIONS' in app_config \
        else temp_conf['CONFIRMATIONS']

    logger.debug(f'Running with config file at {config_file_path} with parameters: {temp_conf}')

    with open(config_file_path, 'w') as f:
        f.write(json.dumps(temp_conf))


def generate_keypair(km_executable: str, keypair_path, address_path, config_path: str) -> None:
    import subprocess
    subprocess.call([km_executable, "-w", f'--principal-config', f"{config_path}"])

    if not os.path.exists(keypair_path):
        raise FileNotFoundError(f'Keypair file doesn\'t exist -- initializing must have failed')
    if not os.path.exists(address_path):
        raise FileNotFoundError(f'Address file doesn\'t exist -- initializing must have failed')


def save_to_path(path, file):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb+') as f:
        f.write(file)


if __name__ == '__main__':
    # parse arguments
    logger.info('STARTING KEY MANAGEMENT.....')
    logger.info(f'Enviroment: {env}')

    config = Config(required=required, config_file=env_defaults[env])
    provider = Provider(config=config)

    keypair = config['KEYPAIR_PATH']
    public = config['KEYPAIR_PUBLIC_PATH']
    config['URL'] = f'{config["ETH_NODE_ADDRESS"]}'
    # not sure we want to let people set the executable from outside, especially
    # since we're running as root atm O.o
    if 'EXECUTABLE_PATH' in os.environ:
        del os.environ['EXECUTABLE_PATH']

    executable = config['EXECUTABLE_PATH']
    os.chdir(pathlib.Path(executable).parent)

    if not os.path.exists(keypair) or not os.path.exists(public):
        generate_keypair(executable, keypair, public, config['DEFAULT_CONFIG_PATH'])



    try:
        with open('/root/.enigma/principal-sign-addr.txt') as f:
            signing_address = f.read()
            logger.info(f'Found Signing address: {signing_address}')
    except FileNotFoundError:
        logger.critical('Signing address not found. Please restart or check configuration')
        exit(-1)

    try:
        with open('/root/.enigma/ethereum-account-addr.txt') as f:
            eth_address = f.read()
            logger.info(f'Found Ethereum address: {eth_address}')
            config['ACCOUNT_ADDRESS'] = eth_address[2:]
    except FileNotFoundError:
        logger.warning('Ethereum address not found, continuing from defaults')

    #  KM address discovery mechanism for testing environments
    if env in ['COMPOSE', 'K8S']:
        thread1 = threading.Thread(target=run, args=(int(config.get('ADDRESS_DISCOVERY_PORT', 8081)), ))
        thread1.start()

    #  will not try a faucet if we're in mainnet or testnet
    if env in ['COMPOSE', 'K8S']:
        try:
            get_initial_coins(eth_address, 'ETH', config)
        except RuntimeError as e:
            logger.critical(f'Failed to get enough ETH or ENG to start - {e}')
            exit(-2)
        except ConnectionError as e:
            logger.critical(f'Failed to connect to remote address: {e}')
            exit(-1)

    logger.info(f'Getting enigma-contract...')
    enigma_address = provider.enigma_contract_address
    logger.info(f'Got address {enigma_address} for enigma contract')

    # engima_contract_address is passed to km application without 0x
    config['ENIGMA_CONTRACT_ADDRESS'] = enigma_address[2:]

    enigma_contract_abi = provider.key_management_abi

    # this name doesn't actually matter, since we're just pointing the config file here
    contract_target = config['CONTRACTS_FOLDER']+'Enigma.json'
    save_to_path(contract_target, enigma_contract_abi)
    if not os.path.exists(contract_target):
        logger.critical(f'Contract ABI file doesn\'t exist @ {contract_target} -- initializing must have failed')
        exit(-1)

    config['ENIGMA_CONTRACT_PATH'] = contract_target

    # generate config file
    generate_config_file(config, config['DEFAULT_CONFIG_PATH'], config['TEMP_CONFIG_PATH'])

    # Take if rust_backtrace is not set try to take from config file. If the value is '0' just don't set it
    if not os.getenv('RUST_BACKTRACE'):
        if config['RUST_BACKTRACE'] != '0':
            os.environ["RUST_BACKTRACE"] = config['RUST_BACKTRACE']

    exec_args = [f'{executable}', f'--principal-config', f'{config["TEMP_CONFIG_PATH"]}']

    log_level = config.get('LOG_LEVEL', '').lower()
    if log_level:
        exec_args.append('-l')
        exec_args.append('log_level')

    subprocess.call(exec_args)
