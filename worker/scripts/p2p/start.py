import json
import os
import pathlib
import sys
import time
from collections import UserDict
from typing import Tuple

from enigma_docker_common import enigma
from enigma_docker_common.config import Config
from enigma_docker_common.ethereum import check_eth_limit
from enigma_docker_common.faucet_api import get_initial_coins
from enigma_docker_common.logger import get_logger
from enigma_docker_common.provider import Provider
from enigma_docker_common.utils import remove_0x

try:
    from environment import Environment
except ImportError:
    from .environment import Environment  # for IDE autocomplete

try:
    from bootstrap_loader import load_bootstrap_parameters
except ImportError:
    from .bootstrap_loader import load_bootstrap_parameters  # for IDE autocomplete

try:
    from node import P2PNode, P2PStatuses, RequiredParameters, OptionalParameters, p2p_parse_url
except ImportError:
    from .node import P2PNode, P2PStatuses, RequiredParameters, OptionalParameters, p2p_parse_url  # for IDE autocomplete

try:
    import utils
except ImportError:
    from ..p2p import utils

logger = get_logger('worker.p2p.start')

# required configuration parameters -- these can all be overridden as environment variables
required_config = ['ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CORE_ADDRESS', 'CORE_PORT', 'CONTRACTS_FOLDER',
                   'KEY_MANAGEMENT_ADDRESS', 'MINIMUM_ETHER_BALANCE', 'MIN_CONFIRMATIONS']

env_defaults = {'K8S': '/root/p2p/config/k8s_config.json',
                'TESTNET': '/root/p2p/config/testnet_config.json',
                'MAINNET': '/root/p2p/config/mainnet_config.json',
                'COMPOSE': '/root/p2p/config/compose_config.json'}

env = os.getenv('ENIGMA_ENV', 'COMPOSE')


def wait_for_register(p2p: P2PNode) -> P2PStatuses:
    while True:
        status = p2p.status()
        if status in (P2PStatuses.REGISTERED, P2PStatuses.LOGGEDIN):
            logger.info(f'P2P server is available and registered!')
            return status
        time.sleep(10)


def load_contracts(config: UserDict, provider: Provider) -> Tuple[enigma.EnigmaContract, enigma.EnigmaTokenContract]:
    erc20_contract = enigma.EnigmaTokenContract(config["ETH_NODE_ADDRESS"],
                                                provider.token_contract_address,
                                                json.loads(provider.enigma_token_abi)['abi'])
    eng_contract = enigma.EnigmaContract(config["ETH_NODE_ADDRESS"],
                                         provider.enigma_contract_address,
                                         json.loads(provider.enigma_abi)['abi'])

    return eng_contract, erc20_contract


def request_coins_from_faucet(config: UserDict, operating_address: str, staking_address: str):
    try:
        get_initial_coins(operating_address, 'ETH', config)
        get_initial_coins(staking_address, 'ETH', config)
    except RuntimeError as e:
        logger.critical(f'Failed to get enough ETH from faucet to start. Error: {e}')
        sys.exit(-2)
    except ConnectionError:
        logger.critical(f'Failed to connect to faucet address. Exiting...')
        sys.exit(-1)

    try:
        get_initial_coins(staking_address, 'ENG', config)
    except RuntimeError as e:
        logger.critical(f'Failed to get enough ENG for staking address - Error: {e}')
        sys.exit(-2)
    except ConnectionError:
        logger.critical(f'Failed to connect to faucet address. Exiting...')
        sys.exit(-1)


def main():  # pylint: disable=too-many-statements

    config = Config(required=required_config, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])

    worker_env = Environment(config=config)
    worker_env.set_status('Down')
    provider = Provider(config=config)

    logger.debug(f'Running with config: {config.items()}')

    logger.info('Setting up worker...')
    logger.info('Loading contract addresses and ABI files...')
    utils.save_to_path(worker_env.enigma_abi_path, provider.enigma_abi)
    eng_contract, erc20_contract = load_contracts(config, provider)
    logger.info('Done')

    logger.info('Loading ethereum address...')
    worker_env.set_status('Loading Ethereum Address...')
    # load operating key from configuration -- used in testnet to automatically start bootstrap nodes
    operating = worker_env.load_operating_address()
    logger.info(f'Loaded operating address. Operating address is: {operating.address}')

    logger.info('Loading staking address...')
    worker_env.set_status('Loading Staking Address...')
    staking = worker_env.load_staking_address()
    logger.info(f'Got staking address {staking.address}')

    if worker_env.testing_env:
        worker_env.set_status('Compose local setup...')
        request_coins_from_faucet(config, operating.address, staking.address)

    worker_env.set_status('Reticulating Splines...')
    bootstrap_params = load_bootstrap_parameters(config, worker_env.bootstrap())

    while not check_eth_limit(operating.address, float(config["MINIMUM_ETHER_BALANCE"]), worker_env.ethereum_node):
        worker_env.set_status('Waiting for ETH...')
        time.sleep(5)

    required = RequiredParameters(
        public_address=operating.address,
        ethereum_key=remove_0x(operating.key),
        ether_node=p2p_parse_url(env, worker_env.ethereum_node, config),
        staking_address=staking.address,
        abi_path=worker_env.enigma_abi_path,
        contract_address=eng_contract.contract_address,
        key_mgmt_node=config["KEY_MANAGEMENT_ADDRESS"]
    )

    optional = OptionalParameters(
        min_confirmations=worker_env.confirmations,
        deposit_amount=worker_env.deposit_amount,
        bootstrap_address=bootstrap_params.address,
        health_check_port=config["HEALTH_CHECK_PORT"],
        log_level=worker_env.log_level,
        auto_init=True,
        bootstrap=bool(worker_env.is_bootstrap)
    )

    if optional.bootstrap:
        optional.bootstrap_path = bootstrap_params.path
        optional.bootstrap_id = bootstrap_params.id
        optional.bootstrap_port = bootstrap_params.port

    # Setting workdir to the base path of the executable, because everything is fragile
    os.chdir(pathlib.Path(worker_env.executable).parent)
    p2p_runner = P2PNode(required, optional)
    p2p_runner.start()

    logger.info('Waiting for node to finish registering...')
    worker_env.set_status('Registering...')
    status = wait_for_register(p2p_runner)
    logger.info(f'Node is registered!')

    # now perform the part of the deposit that comes after the p2p registers
    if worker_env.should_auto_deposit() and status != P2PStatuses.LOGGEDIN:
        erc20_contract.approve(staking.address,
                               provider.enigma_contract_address,
                               worker_env.deposit_amount,
                               key=bytes.fromhex(remove_0x(staking.key)))

        val = erc20_contract.check_allowance(staking.address, provider.enigma_contract_address)
        logger.debug(f'Current allowance for {provider.enigma_contract_address}, from {staking.address}:'
                     f' {val / (10 ** 8)} ENG')

        worker_env.set_status('Setting staking address...')
        logger.info(f'Attempting to set operating address -- staking:{staking.address} operating: {operating.address}')
        # todo: wait for confirmations
        try:
            eng_contract.setOperatingAddress(staking.address, staking.key, operating.address, int(worker_env.confirmations))
            logger.info(f'Done waiting for {worker_env.confirmations} confirmations for setOperatingAddress')
            worker_env.set_status('Depositing...')

            logger.info(f'Attempting deposit from {staking.address} on behalf of worker {operating.address}')
            eng_contract.deposit(staking.address, staking.key, worker_env.deposit_amount, int(worker_env.confirmations))
            logger.info(f'Done waiting for {worker_env.confirmations} confirmations for deposit')
        except enigma.StakingAddressAlreadySet:
            logger.warning('Staking address already set. Probably due to restarting the node with the same staking address')

        worker_env.set_status('Logging in...')
        if p2p_runner.login():
            worker_env.set_status('Running')
        else:
            worker_env.set_status('Failed to login')
    elif status != P2PStatuses.LOGGEDIN:
        worker_env.set_status('Waiting for login...')
        logger.info('Waiting for deposit & login...')
    else:
        worker_env.set_status('Running')
        logger.info('Worker is up')

    while not p2p_runner.kill_now:
        # snooze
        time.sleep(2)
    worker_env.set_status('Down')


if __name__ == '__main__':
    main()
