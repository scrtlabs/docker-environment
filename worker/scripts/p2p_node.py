import signal
import threading
import atexit
import subprocess
import enum
from typing import List

import requests
import urllib3.exceptions

from enigma_docker_common.logger import get_logger

logger = get_logger('worker.p2p-node')


class P2PStatuses(enum.Enum):
    INITIALIZING = "initializing"
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    LOGGEDIN = "logged-in"
    # LOGGEDOUT = "logged-out"


# todo: pylint is totally right though. TBD
class P2PNode(threading.Thread):  # pylint: disable=too-many-instance-attributes
    exec_file = 'cli_app.js'
    runner = 'node'
    kill_now = False

    def __init__(self,  # pylint: disable=too-many-arguments,too-many-locals
                 ether_node: str,
                 public_address: str,
                 contract_address: str,
                 key_mgmt_node: str,
                 abi_path: str,
                 staking_address: str = '',  # remove default value when staking address is added to p2p
                 proxy: int = 3346,
                 core_addr: str = 'localhost:5552',
                 peer_name: str = 'peer1',
                 random_db: bool = True,
                 auto_init: bool = True,
                 log_level: str = 'info',
                 bootstrap: bool = False,
                 bootstrap_address: str = 'B1',
                 bootstrap_id: str = 'B1',
                 health_check_port: int = 12345,
                 deposit_amount: int = 0,
                 login_and_deposit: bool = False,
                 ethereum_key: str = '',
                 bootstrap_path: str = "B1",
                 bootstrap_port: str = "B1",
                 min_confirmations: int = 12,
                 executable_name: str = 'cli_app.js'):
        super().__init__()
        self.exec_file = executable_name
        self.km_node = key_mgmt_node
        self.ether_gateway = ether_node
        self.proxy = proxy
        self.core_addr = core_addr
        self.name = peer_name
        self.random_db = random_db
        self.auto_init = auto_init
        self.log_level = log_level
        self.bootstrap = bootstrap
        self.abi_path = abi_path
        self.staking_address = staking_address
        self.bootstrap_addr = bootstrap_address
        self.ether_public = public_address
        self.contract_addr = contract_address
        self.deposit_amount = deposit_amount
        self.login_and_deposit = login_and_deposit
        self.ethereum_key = ethereum_key
        self.bootstrap_id: str = bootstrap_id
        self.bootstrap_path: str = bootstrap_path
        self.bootstrap_port: str = bootstrap_port
        self.min_confirmations = str(min_confirmations) if int(min_confirmations) != 12 else None
        self.health_check_port = health_check_port
        self.proc = None
        atexit.register(self.stop)
        signal.signal(signal.SIGINT, self._kill)
        signal.signal(signal.SIGTERM, self._kill)

    def run(self):
        self._start()

    def stop(self):
        if self.proc:
            self._kill(None, None)

    def _kill(self, signum, frame):  # pylint: disable=unused-argument
        if self.proc:
            logger.info('Logging out...')

            self.logout()
            try:
                self.proc.send_signal(signal.SIGINT)
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.send_signal(signal.SIGTERM)
            self.kill_now = True
            logger.info('Killed p2p cli')

    def status(self) -> P2PStatuses:
        try:
            resp = requests.get(f'http://localhost:{self.health_check_port}/status')
            if resp.status_code == 200:
                try:
                    return P2PStatuses(resp.json())
                except ValueError as e:
                    logger.error(f'P2P returned unknown status: {resp.json()}')
                    raise ValueError from None

        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with register')
            return False

    @staticmethod
    def register():
        try:
            resp = requests.get('http://localhost:23456/mgmt/register')
            return bool(resp.status_code == 200)
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with register, cannot connect to p2p management API')
            return False

    def login(self):
        try:
            resp = requests.get('http://localhost:23456/mgmt/login')
            return bool(resp.status_code == 200)
        except (requests.RequestException, ConnectionError, urllib3.exceptions.HTTPError):
            logger.error(f'Error with login, falling back to old-style commands')
            try:
                if self.proc:
                    logger.debug('Passing logout to P2P')
                    self.proc.stdin.write(b'login\n')
                    self.proc.stdin.flush()
                    return True
            except AttributeError:
                logger.critical('P2P process doesn\'t exist (was it killed prematurely?)')
                raise RuntimeError from None
            return False

    def logout(self):
        try:
            resp = requests.get('http://localhost:23456/mgmt/logout')
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
        params = {'core': f'{self.core_addr}',
                  'ethereum-websocket-provider': f'{self.ether_gateway}',
                  'proxy': f'{self.proxy}',
                  'ethereum-address': f'{self.ether_public}',
                  'principal-node': f'{self.km_node}',
                  'ethereum-contract-address': f'{self.contract_addr}',
                  'ethereum-contract-abi-path': self.abi_path,
                  'health': f'{self.health_check_port}',
                  'log-level': f'{self.log_level}'}

        # optional values
        if self.staking_address:
            params.update({'staking-address': f'{self.staking_address}'})
        if self.min_confirmations:
            params.update({'min-confirmations': self.min_confirmations})
        if self.ethereum_key:
            params.update({'ethereum-key': self.ethereum_key})

        if self.bootstrap:
            params.update({
                'path': self.bootstrap_path,
                'bnodes': f'{self.bootstrap_addr}',  # f'{self.bootstrap_addr}'
                'port': self.bootstrap_port
            })
        else:
            params.update({
                'bnodes': f'{self.bootstrap_addr}',
                'nickname': f'{self.name}'
            })

        params_list = []
        for k, v in params.items():
            # create a list of [--parameter, value] that we will append to the executable
            params_list.append(f'--{k}')
            params_list.append(v)

        if self.auto_init:
            params_list.append(f'--auto-init')

        if self.random_db:
            params_list.append(f'--random-db')

        return params_list

    def _start(self):

        params = self._map_params_to_exec()

        logger.info(f'Running p2p: {self.exec_file} {params}')

        self.proc = subprocess.Popen([f'{self.runner}', f'--inspect=0.0.0.0', f'{self.exec_file}', *params],
                                     stdin=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True, shell=False)
