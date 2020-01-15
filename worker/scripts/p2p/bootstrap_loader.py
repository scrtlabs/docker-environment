import json
from dataclasses import dataclass
from collections import UserDict

from enigma_docker_common import storage
from enigma_docker_common.logger import get_logger

try:
    import utils
except ImportError:
    from ..p2p import utils

logger = get_logger('bootstrap-loader')


@dataclass
class BootstrapParams:
    address: str
    id: str
    path: str
    port: str


class BootstrapLoader:
    """ Manages the bootstrap startup parameters -- handy to load the private/public/ID file based on different
    strategies. Also used by the non-bootstrap workers to get a list of all bootstrap nodes

    Future work: Think about separating all_bootstrap_addresses()
    """
    bootstrap_file_name = "bootstrap_addresses.json"

    def __init__(self, cfg: UserDict, bootstrap_id: str = ''):
        self.env = cfg.get('ENIGMA_ENV', 'COMPOSE')
        self.bootstrap_id = bootstrap_id
        if self.env == 'COMPOSE':
            self.storage = storage.LocalStorage(directory=cfg["LOCAL_LIBP2P_KEY_PATH"])
            self.storage_public = storage.LocalStorage(directory=cfg["LOCAL_LIBP2P_KEY_PATH"])
        else:
            self.storage = storage.AzureContainerFileService(directory='bootstrap')
            self.storage_public = storage.AzureContainerFileService(directory='bootstrap-public')
        self._address: str = ''
        self._key: str = ''
        self._public: str = ''
        self.keyfile: str = ''

    def all_bootstrap_addresses(self) -> str:
        """ returns a comma-separated list of all the bootstrap nodes in libp2p format
            example: /dnsaddr/bootstrap/tcp/10300/ajsdfasidfjeijfajwe
        """
        return self.storage_public[self.bootstrap_file_name].decode()

    def to_json(self) -> str:
        """ returns the libp2p key file as json string """
        self.load()
        return self.keyfile

    def load(self):
        """ Load the bootstrap key file and parse it """
        if self.env != 'COMPOSE' and not self.storage.credential:
            raise RuntimeError('Cannot get bootstrap configuration from '
                               'Azure storage without parameter: STORAGE_CONNECTION_STRING')
        if not self.keyfile:  # don't need to run this more than once
            logger.info(f'Bootstrap ID: {self.bootstrap_id}')
            self.keyfile = self._get_file(self.bootstrap_id)

            as_dict = json.loads(self.keyfile)
            logger.debug(f'Got bootstrap configuration file: {as_dict}')
            self._address = as_dict["id"]
            self._key = as_dict["privKey"]
            self._public = as_dict["pubKey"]

    @property
    def address(self):
        """ libp2p ID """
        self.load()
        return self._address

    @property
    def key(self):
        """ libp2p private key (privKey field) """
        self.load()
        return self._key

    @property
    def public(self):
        """ libp2p public key (pubKey field) """
        self.load()
        return self._public

    def _get_file(self, file_name) -> bytes:
        """ used internally to get the key file from storage """
        try:
            return self.storage[file_name]
        except PermissionError as e:
            logger.error(f'Failed to get file, probably missing credentials. {e}')
            raise
        except ValueError as e:  # not sure what Exceptions right now
            logger.error(f'Failed to get file: {e}')
            raise


def load_bootstrap_parameters(config: UserDict, is_bootstrap: bool):
    bootstrap_id = config.get('BOOTSTRAP_ID', '') if is_bootstrap else ''
    bootstrap_address = config.get('BOOTSTRAP_ADDRESS', '')
    bootstrap_loader = BootstrapLoader(config, bootstrap_id)
    # file must be .json since p2p will try to use require(). Can remove when p2p is changed
    bootstrap_path: str = config['BOOTSTRAP_PATH'] + bootstrap_id
    bootstrap_port: str = config['BOOTSTRAP_PORT']

    # #### bootstrap params #####
    if is_bootstrap:
        logger.info('Loading bootstrap node parameters')

        bootstrap_id = bootstrap_loader.address

        # we save the keyfile to disk so we can send it to p2p runner
        bootstrap_path += '.json'

        keyfile = bootstrap_loader.to_json()
        utils.save_to_path(bootstrap_path, keyfile)

    if not bootstrap_address:  # if bootstrap addresses are not configured, try to pull
        logger.info('Loading bootstrap addresses...')
        bootstrap_address = bootstrap_loader.all_bootstrap_addresses()
        logger.info(f'Got bootstrap addresses: {bootstrap_address}')
    else:
        logger.info(f'Bootstrap addresses already set: {bootstrap_address}')

    return BootstrapParams(address=bootstrap_address, id=bootstrap_id, path=bootstrap_path, port=bootstrap_port)
