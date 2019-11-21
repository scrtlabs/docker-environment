import time
import signal
import threading
import atexit
import subprocess

from typing import List

from enigma_docker_common.logger import get_logger

logger = get_logger('worker.p2p-node')


class P2PNode(threading.Thread):
    exec_file = 'cli_app.js'
    runner = 'node'
    kill_now = False

    def __init__(self,
                 ether_node: str,
                 public_address: str,
                 contract_address: str,
                 key_mgmt_node: str,
                 abi_path: str,
                 proxy: int = 3346,
                 core_addr: str = 'localhost:5552',
                 peer_name: str = 'peer1',
                 random_db: bool = True,
                 auto_init: bool = True,
                 bootstrap: bool = False,
                 bootstrap_address: str = 'B1',
                 bootstrap_id: str = 'B1',
                 deposit_amount: int = 0,
                 login_and_deposit: bool = False,
                 ethereum_key: str = '',
                 bootstrap_path: str = "B1",
                 bootstrap_port: str = "B1",
                 min_confirmations: int = 12,
                 executable_name: str = 'cli_app.js', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exec_file = executable_name
        self.km_node = key_mgmt_node

        # dirty hack because P2P CLI wants the address without prefix.. remove when that's fixed
        if ether_node.startswith('https://'):
            ether_node = ether_node[8:]
        if ether_node.startswith('http://'):
            ether_node = ether_node[7:]
        self.ether_gateway = ether_node
        self.proxy = proxy
        self.core_addr = core_addr
        self.name = peer_name
        self.random_db = random_db
        self.auto_init = auto_init
        self.bootstrap = bootstrap
        self.abi_path = abi_path
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
        self.proc = None
        atexit.register(self.stop)
        signal.signal(signal.SIGINT, self._kill)
        signal.signal(signal.SIGTERM, self._kill)

    def run(self):
        self._start()

    def stop(self):
        if self.proc:
            self._kill(None, None)

    def _kill(self, signum, frame):
        if self.proc:
            logger.info('Logging out...')
            self.proc.stdin.write(b'logout\n')
            self.proc.stdin.flush()
            time.sleep(2)
            self.proc.send_signal(signal.SIGINT)
            time.sleep(2)
            self.proc.terminate()
            self.proc.wait(timeout=0.2)
            del self.proc
            self.proc = None
            self.kill_now = True
            logger.info('Killed p2p cli')

    def _map_params_to_exec(self) -> List[str]:
        """ build executable params -- if cli params change just change the keys and everything should still work """
        params = {'core': f'{self.core_addr}',
                  'ethereum-websocket-provider': f'ws://{self.ether_gateway}',
                  'proxy': f'{self.proxy}',
                  'ethereum-address': f'{self.ether_public}',
                  'principal-node': f'{self.km_node}',
                  'ethereum-contract-address': f'{self.contract_addr}',
                  'ethereum-contract-abi-path': self.abi_path}

        if self.min_confirmations:
            params.update({'min_confirmations': self.min_confirmations})
        if self.ethereum_key:
            params.update({'ethereum-key': self.ethereum_key})

        if self.login_and_deposit:
            params.update({'deposit-and-login': f'{self.deposit_amount}'})

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
