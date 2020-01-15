from collections import UserDict

from enigma_docker_common.crypto import EthereumKey
from enigma_docker_common.logger import get_logger

try:
    import utils
except ImportError:
    from ..p2p import utils

logger = get_logger('p2p.startup.environment')


class Environment: # pylint: disable=too-many-instance-attributes

    testing_env = ["K8S", "COMPOSE"]

    def __init__(self, config: UserDict):
        self.is_bootstrap = bool(config.get('BOOTSTRAP', ''))
        self.env = config['ENIGMA_ENV']
        self.config = config

        self.log_level = config.get('LOG_LEVEL', 'info')
        # todo: unhardcode this
        self.executable = '/root/p2p/src/cli/cli_app.js'
        self.ethereum_node = config["ETH_NODE_ADDRESS"]
        self.enigma_abi_path = f'{config["CONTRACTS_FOLDER"]}{config["ENIGMA_CONTRACT_FILE_NAME"]}'
        self.deposit_amount = int(config['DEPOSIT_AMOUNT'])
        self.confirmations = config["MIN_CONFIRMATIONS"]

    def bootstrap(self):
        return self.is_bootstrap

    def testing(self):
        return self.env in self.testing_env

    def testnet(self):
        return self.env == "TESTNET"

    def mainnet(self):
        return self.env == "MAINNET"

    def load_staking_from_config(self):
        return self.is_bootstrap and not self.testing_env

    def load_operating_key_from_config(self):
        return self.is_bootstrap and self.testnet()

    def should_auto_deposit(self):
        return self.testing() or (self.is_bootstrap and self.testnet())

    def load_staking_from_cli(self):
        return not self.is_bootstrap and not self.testing_env

    def load_operating_address(self):
        if self.load_operating_key_from_config():
            logger.info(f'Loading from configuration...')
            operating = EthereumKey(key=self.config["OPERATING_PRIVATE_KEY"])
        else:
            operating = utils.load_ethereum_keys(self.config)
        return operating

    def load_staking_address(self):
        if self.load_staking_from_cli():
            logger.info('Waiting for staking address... Set it up using the CLI')
            staking = EthereumKey(address=utils.wait_for_staking_address(self.config))
        elif self.load_staking_from_config():
            staking = self.load_staking_key_from_config()
        #  will not try a faucet if we're in mainnet or testing environment
        else:
            staking = self.generate_staking_key_local()

        return staking

    def load_staking_key_from_config(self):
        staking_key = self.config["STAKING_PRIVATE_KEY"]
        return EthereumKey(key=staking_key)

    def generate_staking_key_local(self):
        return utils.load_staking_keys(self.config)
