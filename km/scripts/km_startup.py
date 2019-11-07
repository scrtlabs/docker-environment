# Environment options: COMPOSE, K8S, TESTNET, MAINNET
import os
import json
import subprocess
import pathlib

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger

logger = get_logger('key_management.startup')


required = [  # global environment setting
              'ENIGMA_ENV',
              # required by provider AND locally
              'CONTRACT_DISCOVERY_PORT', 'CONTRACT_DISCOVERY_ADDRESS',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'ETH_NODE_PORT',
              'CONTRACTS_FOLDER', 'DEFAULT_CONFIG_PATH',
              'FAUCET_URL', 'STORAGE_CONNECTION_STRING', 'KEYPAIR_FILE_NAME', 'TEMP_CONFIG_PATH']

env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}


def generate_config_file(app_config: dict, default_config_path: str, config_file_path: str) -> None:
    """ Generates a configuration file based on environment variables set in env_map variable above """
    with open(default_config_path, 'r') as f:
        default_config = json.load(f)

    # for each value either use the environment variable set as key.upper() or take the value from the default config
    temp_conf = {k: app_config.get(k.upper(), v) for k, v in default_config.items()}

    logger.debug(f'Running with config file at {config_file_path} with parameters: {temp_conf}')

    with open(config_file_path, 'w') as f:
        f.write(json.dumps(temp_conf))


def generate_keypair(keypair_path, km_executable: str):
    import subprocess
    subprocess.run([km_executable, "-w"])


def save_to_path(path, file):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb+') as f:
        f.write(file)


def map_log_level_to_exec_flags(loglevel: str) -> str:
    level = loglevel.upper()
    if level == "DEBUG":
        return '-vvv'
    if level == "INFO":
        return '-vv'
    if level == "WARNING":
        return '-v'
    else:
        return ''


if __name__ == '__main__':
    # parse arguments
    logger.info('STARTING KEY MANAGEMENT STARTUP.....')

    env = os.getenv('ENIGMA_ENV', 'COMPOSE')

    config = Config(required=required, config_file=env_defaults[env])
    provider = Provider(config=config)

    keypair = config['KEYPAIR_PATH']
    public = config['KEYPAIR_PUBLIC_PATH']

    # not sure we want to let people set the executable from outside, especially
    # since we're running as root atm O.o
    if 'EXECUTABLE_PATH' in os.environ:
        del os.environ['EXECUTABLE_PATH']

    executable = config['EXECUTABLE_PATH']

    if env == "LOCAL":  # allow a self-generating option for independent scenarios
        generate_keypair(keypair, executable)
    else:
        # get Keypair file -- environment variable STORAGE_CONNECTION_STRING must be set
        if os.getenv('SGX_MODE', 'HW') == 'SW':
            sealed_km = provider.get_file(config['KEYPAIR_STORAGE_DIRECTORY'], config['KEYPAIR_FILE_NAME_SW'])
        else:
            sealed_km = provider.get_file(config['KEYPAIR_STORAGE_DIRECTORY'], config['KEYPAIR_FILE_NAME'])
        save_to_path(keypair, sealed_km)

        # get public key file
        public_key = provider.principal_address
        save_to_path(public, public_key)

    if not os.path.exists(keypair):
        logger.critical(f'Keypair file doesn\'t exist -- initializing must have failed')
        exit(-1)
    if not os.path.exists(public):
        logger.critical(f'Public key file doesn\'t exist -- initializing must have failed')
        exit(-1)

    CONFIG_FILE_PATH = '/tmp/config.json'

    # set the URL of the ethereum node we're going to use -- this will be picked up by the application config
    config['URL'] = f'http://{config["ETH_NODE_ADDRESS"]}:{config["ETH_NODE_PORT"]}'

    logger.info(f'Waiting for enigma-contract @ '
                f'http://{config["CONTRACT_DISCOVERY_ADDRESS"]}:{config["CONTRACT_DISCOVERY_PORT"]} for enigma contract')
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

    os.chdir(pathlib.Path(executable).parent)

    debug_trace_flags = map_log_level_to_exec_flags(config.get('LOG_LEVEL', 'INFO'))

    subprocess.call([f'{executable}', f'{debug_trace_flags}', f'--principal-config', f'{CONFIG_FILE_PATH}'])
