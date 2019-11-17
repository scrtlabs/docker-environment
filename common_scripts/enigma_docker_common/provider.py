import os
import functools
import zipfile
from .logger import get_logger
from . import storage

logger = get_logger('enigma_common.provider')


class Provider:
    def __init__(self, config: dict):
        self.eth_node_address = config['CONTRACT_DISCOVERY_ADDRESS']
        self.CONTRACT_DISCOVERY_PORT = config['CONTRACT_DISCOVERY_PORT']
        self.CONTRACT_DISCOVERY_ADDRESS = f'http://{self.eth_node_address}:{self.CONTRACT_DISCOVERY_PORT}'
        self.KM_DISCOVERY_ADDRESS = config['KEY_MANAGEMENT_DISCOVERY']

        self._enigma_contract_filename = config.get('ENIGMA_CONTRACT_FILENAME', 'enigmacontract.txt')
        self._token_contract_filename = config.get('TOKEN_CONTRACT_FILENAME', 'enigmatokencontract.txt')

        self._principal_address_directory = config.get('PRINCIPAL_ADDRESS_DIRECTORY', 'public')
        # if os.getenv('SGX_MODE', 'HW') == 'SW':
        #     self._principal_address_filename = config.get('PRINCIPAL_ADDRESS_FILENAME', 'principal-sign-addr_sw.txt')
        # else:
        self._principal_address_filename = config.get('PRINCIPAL_ADDRESS_FILENAME', 'principal-sign-addr.txt')
        self._enigma_token_abi_directory = config.get('TOKEN_CONTRACT_ABI_DIRECTORY', 'contract')
        self._enigma_token_abi_filename = config.get('TOKEN_CONTRACT_ABI_FILENAME', 'EnigmaToken.json')
        self._enigma_token_abi_filename_zip = config.get('ENIGMA_CONTRACT_ABI_FILENAME_ZIPPED', 'EnigmaToken.zip')

        self._enigma_contract_abi_directory = config.get('ENIGMA_CONTRACT_ABI_DIRECTORY', 'contract')

        self._km_abi_directory = config.get('PRINCIPAL_ADDRESS_DIRECTORY', 'contract')
        self._km_abi_filename = config.get('PRINCIPAL_ADDRESS_FILENAME', 'IEnigma.json')

        if os.getenv('SGX_MODE', 'HW') == 'SW':
            self._enigma_contract_abi_filename = config.get('ENIGMA_CONTRACT_ABI_FILENAME_SW',
                                                            'EnigmaSimulation.json')
            self._enigma_contract_abi_filename_zip = config.get('ENIGMA_CONTRACT_ABI_FILENAME_ZIPPED_SW',
                                                                'EnigmaSimulation.zip')
        else:
            self._enigma_contract_abi_filename = config.get('ENIGMA_CONTRACT_ABI_FILENAME', 'Enigma.json')
            self._enigma_contract_abi_filename_zip = config.get('ENIGMA_CONTRACT_ABI_FILENAME_ZIPPED', 'Enigma.zip')

        # strategy for information we get from enigma-contract
        self.contract_strategy = {"COMPOSE": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS),
                                  "COMPOSE_DEV": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS),
                                  "K8S": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS),
                                  "TESTNET": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS),
                                  "MAINNET": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS)}

        self.key_management_discovery = {"COMPOSE": storage.HttpFileService(self.KM_DISCOVERY_ADDRESS, namespace='km'),
                                        "COMPOSE_DEV": storage.HttpFileService(self.KM_DISCOVERY_ADDRESS, namespace='km'),
                                        "K8S": storage.HttpFileService(self.KM_DISCOVERY_ADDRESS, namespace='km'),
                                        "TESTNET": storage.HttpFileService(self.KM_DISCOVERY_ADDRESS, namespace='km'),
                                        "MAINNET": storage.HttpFileService(self.KM_DISCOVERY_ADDRESS, namespace='km')}

        # information stored in global storage
        self.backend_strategy = {"COMPOSE": storage.AzureContainerFileService,
                                 "COMPOSE_DEV": storage.HttpFileService(self.CONTRACT_DISCOVERY_ADDRESS),
                                 "K8S": storage.AzureContainerFileService,
                                 "TESTNET": storage.AzureContainerFileService,
                                 "MAINNET": storage.AzureContainerFileService}

        self._enigma_abi = None
        self._enigma_token_abi = None
        self._enigma_contract_address = None
        self._principal_address = None
        self._token_contract_address = None
        self._key_management_abi = None

    @property
    @functools.lru_cache()
    def key_management_abi(self):
        return self.get_file(directory_name=self._km_abi_directory,
                             file_name=self._km_abi_filename)

    @property
    @functools.lru_cache()
    def enigma_contract_address(self):
        return self._deployed_contract_address(contract_name=self._enigma_contract_filename)

    @property
    @functools.lru_cache()
    def token_contract_address(self):
        return self._deployed_contract_address(contract_name=self._token_contract_filename)

    @property
    @functools.lru_cache()
    def principal_address(self):
        fs = self.key_management_discovery[os.getenv('ENIGMA_ENV', 'COMPOSE')]
        is_contract_ready = self._wait_till_open(timeout=120, fs=fs)
        if not is_contract_ready:
            logger.error(f'Key management address wasn\'t ready before timeout (120s) expired')
            raise TimeoutError(f'Timeout for server @ {self.KM_DISCOVERY_ADDRESS}')
        return fs[self._principal_address_filename]

    @property
    @functools.lru_cache()
    def enigma_abi(self):
        zipped = self.get_file(directory_name=self._enigma_contract_abi_directory,
                               file_name=self._enigma_contract_abi_filename_zip)

        return self._unzip_bytes(zipped, self._enigma_contract_abi_filename)

    @property
    @functools.lru_cache()
    def enigma_token_abi(self):
        zipped = self.get_file(directory_name=self._enigma_token_abi_directory,
                               file_name=self._enigma_token_abi_filename_zip)

        return self._unzip_bytes(zipped, self._enigma_token_abi_filename)

    def get_file(self, directory_name: str, file_name) -> bytes:
        fs = self.backend_strategy[os.getenv('ENIGMA_ENV', 'COMPOSE')](directory_name)
        try:
            return fs[file_name]
        except PermissionError as e:
            logger.critical(f'Failed to get file, probably missing credentials. {e}')
        except ValueError as e:  # not sure what Exceptions right now
            logger.critical(f'Failed to get file: {e}')
        except Exception as e:  # not sure what Exceptions right now
            logger.critical(f'Failed to get file: {type(e)} - {e}')
            exit(-1)

    def _wait_till_open(self, timeout: int = 60, fs: storage.HttpFileService = None) -> bool:
        _fs = fs or self.contract_strategy[os.getenv('ENIGMA_ENV', 'COMPOSE')]
        import time
        for _ in range(timeout):
            if _fs.is_ready():
                return True
            time.sleep(1)
        return False

    def _get_contract_address(self, contract_name):
        fs = self.contract_strategy[os.getenv('ENIGMA_ENV', 'COMPOSE')]
        return fs[contract_name]

    def _deployed_contract_address(self, contract_name, timeout: int = 60):
        logger.debug(f'Waiting for enigma-contract @ http://{self.CONTRACT_DISCOVERY_ADDRESS} for enigma contract')
        # wait for contract to be ready
        is_contract_ready = self._wait_till_open(timeout=timeout)
        if not is_contract_ready:
            logger.error(f'Contract address wasn\'t ready before timeout ({timeout}s) expired')
            raise TimeoutError(f'Timeout for server @ {self.CONTRACT_DISCOVERY_ADDRESS}')
        return self._get_contract_address(contract_name)

    @staticmethod
    def _unzip_bytes(file_bytes: bytes, file_name: str) -> bytes:
        """ unzip a file to a path """
        import io
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as zip_ref:
            return zip_ref.read(file_name)
