import atexit
import enum
import signal
import subprocess
import threading
from collections import UserDict
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import List, Union

import requests
import urllib3.exceptions
from enigma_docker_common.logger import get_logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = get_logger('worker.p2p.node')


@dataclass
class RequiredParameters:
    ether_node: str
    public_address: str
    contract_address: str
    key_mgmt_node: str
    abi_path: str
    staking_address: str
    ethereum_key: str


@dataclass
class OptionalParameters:  # pylint: disable=too-many-instance-attributes
    proxy: int = 3346
    core_addr: str = 'localhost:5552'
    peer_name: str = 'peer1'
    random_db: bool = True
    auto_init: bool = True
    log_level: str = 'info'
    bootstrap: bool = False
    bootstrap_address: str = 'B1'
    bootstrap_id: str = 'B1'
    health_check_port: int = 12345
    deposit_amount: int = 0
    bootstrap_path: str = "B1"
    bootstrap_port: str = "B1"
    min_confirmations: Union[str, int] = "12"
    login_and_deposit: bool = False
    executable_name: str = 'cli_app.js'


class P2PStatuses(enum.Enum):
    UNAVAILABLE = "unavailable"
    INITIALIZING = "initializing"
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    LOGGEDIN = "logged-in"
    # LOGGEDOUT = "logged-out"


retry = Retry(connect=3, backoff_factor=0.5)
node_adapter = HTTPAdapter(max_retries=retry)


def p2p_parse_url(env: str, ethereum_node: str, config: UserDict) -> str:
    p = urlparse(ethereum_node)
    hostname = p.hostname
    port = p.port
    if not port:
        raise ValueError('No port specified in ethereum node')
    # in ganache WS and HTTP are in the same port. In our testnet it isn't (8546 and 8545 respectively)
    if env in ['TESTNET', 'MAINNET']:
        ether_gateway = config.get('ETHEREUM_NODE_ADDRESS_WEBSOCKET', f'ws://{hostname}:{port + 1}')
    else:
        ether_gateway = config.get('ETHEREUM_NODE_ADDRESS_WEBSOCKET', f'ws://{hostname}:{port}')

    return ether_gateway


# todo: pylint is totally right though. TBD
class P2PNode(threading.Thread):
    exec_file = 'cli_app.js'
    runner = 'node'
    kill_now = False

    def __init__(self,
                 required: RequiredParameters,
                 optional: OptionalParameters = OptionalParameters()):
        super().__init__()

        self.optional = optional
        self.required = required
        self.proc = None

        atexit.register(self.stop)
        signal.signal(signal.SIGINT, self._kill)
        signal.signal(signal.SIGTERM, self._kill)

        self.session = requests.Session()

        self.session.mount(f'http://', node_adapter)
        self.session.mount(f'https://', node_adapter)

    def run(self):
        self._start()

    def stop(self):
        if self.proc:
            self._kill(None, None)

    def _kill(self, signum, frame):  # pylint: disable=unused-argument
        if self.proc:
            logger.info('Logging out...')
            self.logout()
            self.kill_now = True
            logger.info('Killed p2p cli')

    def status(self) -> P2PStatuses:
        try:
            resp = self.session.get(f'http://localhost:{self.optional.health_check_port}/status')
            if resp.status_code == 200:
                try:
                    logger.debug(f'Got status from P2P: {resp.content.decode()}')
                    return P2PStatuses(resp.content.decode())
                except ValueError:
                    logger.error(f'P2P returned unknown status: {resp.json()}')
                    raise ValueError from None
            logger.warning(f'Error getting status from p2p -- status server not ready')
            return P2PStatuses.INITIALIZING
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError) as e:
            logger.info(f'Seems that P2P is not yet available -- status service unavailable: {e}')
            return P2PStatuses.UNAVAILABLE

    def register(self):
        try:
            resp = self.session.get('http://localhost:23456/mgmt/register')
            return bool(resp.status_code == 200)
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with register, cannot connect to p2p management API')
            return False

    def login(self):
        try:
            resp = self.session.get('http://localhost:23456/mgmt/login')
            return bool(resp.status_code == 200)
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with login, falling back to old-style commands')
            try:
                if self.proc:
                    logger.debug('Passing login to P2P')
                    self.proc.stdin.write(b'login\n')
                    self.proc.stdin.flush()
                    return True
            except AttributeError:
                logger.critical('P2P process doesn\'t exist (was it killed prematurely?)')
                raise RuntimeError from None
            return False

    def logout(self):
        try:
            resp = self.session.get('http://localhost:23456/mgmt/logout')
            return bool(resp.status_code == 200)
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with logout, falling back to old-style commands')
            try:
                if self.proc:
                    logger.debug('Passing logout to P2P')
                    self.proc.stdin.write(b'logout\n')
                    self.proc.stdin.flush()
                    return True
            except AttributeError:
                logger.critical('P2P process doesn\'t exist (was it killed prematurely?)')
                raise RuntimeError from None
            return False

    def _map_params_to_exec(self) -> List[str]:
        """ build executable params -- if cli params change just change the keys and everything should still work """
        params = {'core': f'{self.optional.core_addr}',
                  'ethereum-websocket-provider': f'{self.required.ether_node}',
                  'proxy': f'{self.optional.proxy}',
                  'ethereum-address': f'{self.required.public_address}',
                  'principal-node': f'{self.required.key_mgmt_node}',
                  'ethereum-contract-address': f'{self.required.contract_address}',
                  'ethereum-contract-abi-path': self.required.abi_path,
                  'health': f'{self.optional.health_check_port}',
                  'log-level': f'{self.optional.log_level}',
                  'ethereum-key': self.required.ethereum_key,
                  'staking-address': f'{self.required.staking_address}',
                  'min-confirmations': str(self.optional.min_confirmations)}

        if self.optional.bootstrap:
            params.update({
                'path': self.optional.bootstrap_path,
                'bnodes': f'{self.optional.bootstrap_address}',  # f'{self.bootstrap_addr}'
                'port': self.optional.bootstrap_port
            })
        else:
            params.update({
                'bnodes': f'{self.optional.bootstrap_address}',
                'nickname': f'{self.name}'
            })

        params_list = []
        for k, v in params.items():
            # create a list of [--parameter, value] that we will append to the executable
            params_list.append(f'--{k}')
            params_list.append(v)

        if self.optional.auto_init:
            params_list.append(f'--auto-init')

        if self.optional.random_db:
            params_list.append(f'--random-db')

        return params_list

    def _start(self):

        params = self._map_params_to_exec()

        logger.info(f'Running p2p: {self.exec_file} {params}')

        self.proc = subprocess.Popen([f'{self.runner}', f'--inspect=0.0.0.0', f'{self.exec_file}', *params],
                                     stdin=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, shell=False)
