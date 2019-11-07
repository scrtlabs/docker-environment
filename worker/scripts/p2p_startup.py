import os
from typing import Tuple
import argparse
import json
import pathlib
from typing import List

import requests

from Crypto.Hash import keccak
from ecdsa import SigningKey, SECP256k1, VerifyingKey

from enigma_docker_common.config import Config
from enigma_docker_common.provider import Provider
from enigma_docker_common.logger import get_logger


logger = get_logger('worker.p2p-startup')

# required configuration parameters -- these can all be overridden as environment variables
required = [  # required by provider AND locally
              'CONTRACT_DISCOVERY_PORT', 'CONTRACT_DISCOVERY_ADDRESS',
              # defaults in local config file
              'ETH_NODE_ADDRESS', 'ENIGMA_CONTRACT_FILE_NAME', 'CORE_ADDRESS', 'CORE_PORT', 'CONTRACTS_FOLDER',
              'KEY_MANAGEMENT_ADDRESS', 'FAUCET_URL', 'MINIMUM_ETHER_BALANCE', 'ETH_NODE_PORT']

# local path to where we save the private key/public key if we generate it locally
KEY_PAIR_PATH = os.path.dirname(os.path.dirname(__file__))

env_defaults = {'K8S': './p2p/config/k8s_config.json',
                'TESTNET': './p2p/config/testnet_config.json',
                'MAINNET': './p2p/config/mainnet_config.json',
                'COMPOSE': './p2p/config/compose_config.json'}


def init_arg_parse() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("-e", "--executable", help="Path to Key Management executable", type=str,
                   default='/root/p2p/src/cli/cli_app.js')
    p.add_argument("-k", "--keypair", help="Path to KeyPair file", type=str,
                   default='/root/.enigma/keypair.sealed')
    p.add_argument("-b", "--bootstrap", help="Run worker as a bootstrap node",
                   dest='bootstrap', action='store_true', default=False)
    p.add_argument("-t", "--backtrace", help="Rust Backtrace", type=int, default=1)
    return p


class P2PNode:
    exec_file = 'cli_app.js'
    runner = 'node'

    def __init__(self,
                 ether_node: str,
                 public_address: str,
                 contract_address: str,
                 key_mgmt_node: str,
                 abi_path: str,
                 proxy: int = 3346,
                 core_addr: str = 'localhost:5552',
                 name: str = 'peer1',
                 random_db: bool = True,
                 auto_init: bool = True,
                 bootstrap: bool = False,
                 bootstrap_address: str = '',
                 deposit_amount: int = 0,
                 login_and_deposit: bool = False,
                 ethereum_key: str = '',
                 executable_name: str = 'cli_app.js'):
        self.exec_file = executable_name
        self.km_node = key_mgmt_node
        self.ether_gateway = ether_node
        self.proxy = proxy
        self.core_addr = core_addr
        self.name = name
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

    def _map_params_to_exec(self) -> List[str]:
        """ build executable params -- if cli params change just change the keys and everything should still work """
        params = {'core': f'{self.core_addr}',
                  'ethereum-websocket-provider': f'ws://{self.ether_gateway}',
                  'proxy': f'{self.proxy}',
                  'ethereum-address': f'{self.ether_public}',
                  'principal-node': f'{self.km_node}',
                  'ethereum-contract-address': f'{self.contract_addr}',
                  'ethereum-contract-abi-path': self.abi_path}

        if self.ethereum_key:
            params.update({'ethereum-key': self.ethereum_key})

        if self.login_and_deposit:
            params.update({'deposit-and-login': f'{self.deposit_amount}'})

        if self.bootstrap:
            params.update({
                'path': 'B1',
                'bnodes': 'B1',
                'port': 'B1'
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

    def run(self):
        import subprocess

        params = self._map_params_to_exec()

        logger.info(f'Running p2p: {self.exec_file} {params}')

        subprocess.call([f'{self.runner}', f'--inspect=0.0.0.0', f'{self.exec_file}', *params])


def generate_key() -> Tuple[str, bytes]:
    """
    Generate private key and public key
    Save as PEMs for management

    :return: ECDSA Key Object - pri_key, pub_key
    """
    key_path = KEY_PAIR_PATH

    pri_key = SigningKey.generate(curve=SECP256k1)
    pub_key = pri_key.get_verifying_key()
    print(f'{KEY_PAIR_PATH}')
    open(key_path + "private.pem", "w").write(pri_key.to_pem().decode())
    open(key_path + "public.pem", "w").write(pub_key.to_pem().decode())

    return '0x' + pri_key.to_string().hex(), pub_key.to_string()


def pubkey_to_addr(pubkey: str) -> str:
    public_key_bytes = bytes.fromhex(pubkey)
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(public_key_bytes)
    keccak_digest = keccak_hash.hexdigest()
    # Take the last 20 bytes
    wallet_len = 40
    wallet = "0x" + keccak_digest[-wallet_len:]
    return wallet


def save_to_path(path, file, flags='wb+'):
    logger.info(f'Saving file to path: {path}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, flags) as f:
        f.write(file)


def get_coins_faucet(faucet_url, account: str, currency: str) -> bool:
    if currency not in ['ether', 'eng']:
        raise ValueError(f'Requested balance for invalid currency {currency}')
    logger.info(f'Trying to get ether for account: {account}')
    try:
        resp = requests.get(f'{faucet_url}/faucet/{currency}?account={account}', timeout=120)
        if resp.status_code == 200:
            logger.info(f'Successfully got ether from faucet')
            return True
        else:
            logger.error(f'Failed to get ether from faucet: {resp.status_code}')
    except requests.exceptions.RequestException as e:
        logger.critical(f'Failed to connect to faucet: {e}')
        return False


def get_balance(faucet_url, account: str, currency: str) -> float:
    if currency not in ['ether', 'eng']:
        raise ValueError(f'Requested balance for invalid currency {currency}')
    logger.info(f'Trying to get {currency} balance account: {account}')
    try:
        resp = requests.get(f'{faucet_url}/faucet/balance/{currency}?account={account}', timeout=120)
        if resp.status_code == 200:
            logger.info(f'Current {currency} balance is: {resp.json()}')
            return resp.json()
        else:
            logger.error(f'Failed to get balance from faucet: {resp.status_code}')
            exit(-1)
    except requests.exceptions.RequestException as e:
        logger.critical(f'Failed to connect to faucet: {e}')
        exit(-1)


def generate_address() -> Tuple[str, str]:
    # todo: conditional generate
    priv, pub = generate_key()
    public_key = pubkey_to_addr(pub.hex())

    save_to_path(privkey_path, priv, 'w+')
    save_to_path(pubkey_path, public_key, 'w+')
    logger.info(f'Generated new ethereum key, address: {public_key}')
    return priv, public_key


if __name__ == '__main__':
    parser = init_arg_parse()
    args = parser.parse_args()

    logger.info('STARTING P2P STARTUP')

    is_bootstrap = os.getenv('BOOTSTRAP', '')

    if not is_bootstrap:
        required.append('BOOTSTRAP_ADDRESS')

    config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
    provider = Provider(config=config)

    # *** Load parameters from config

    eng_abi_path = config['CONTRACTS_FOLDER']
    enigma_abi_filename = config['ENIGMA_CONTRACT_FILE_NAME']
    eth_node_address = f'{config["ETH_NODE_ADDRESS"]}:{config["ETH_NODE_PORT"]}'
    km_node = f'http://{config["KEY_MANAGEMENT_ADDRESS"]}:{config["KEY_MANAGEMENT_PORT"]}'
    enigma_abi_path = eng_abi_path+enigma_abi_filename

    # bootstrap params
    if is_bootstrap:
        bootstrap_id = config.get('BOOTSTRAP_ID', 'B1')
    else:
        peer_name = config.get('PEER_NAME', 'peer1')

    deposit_amount = int(config['DEPOSIT_AMOUNT'])
    eth_key_path = config['ETH_KEY_PATH']

    # Load Enigma.json ABI
    enigma_contract_abi = provider.enigma_abi
    save_to_path(enigma_abi_path, enigma_contract_abi)

    token_contract_abi = json.loads(provider.enigma_token_abi)
    token_contract_address = provider.token_contract_address
    eng_contract_addr = provider.enigma_contract_address
    logger.info(f'Got address {eng_contract_addr} for enigma contract')

    PRIV_KEY_FILENAME = "id_rsa"
    PUB_KEY_FILENAME = "id_rsa.pub"

    pubkey_path = f'{eth_key_path}{PUB_KEY_FILENAME}'
    privkey_path = f'{eth_key_path}{PRIV_KEY_FILENAME}'

    login_and_deposit = False

    if config.get('FORCE_NEW_ETH_ADDR', False):
        logger.info('Forcing new ethereum address')
        generate_address()
    else:  # try to open address from filesystem
        try:
            with open(pubkey_path, 'r') as f:
                public_key = f.read()
            with open(privkey_path, 'r') as f:
                priv = f.read()

            logger.info(f'Loaded key from local filesystem, ethereum address: {public_key}')

        except FileNotFoundError:
            priv, public_key = generate_address()

    # todo: write code to decide if we want to use a faucet or not
    if os.getenv('ENIGMA_ENV', 'COMPOSE') in ['COMPOSE', 'TESTNET', 'K8S']:
        import web3

        if float(config['MINIMUM_ETHER_BALANCE']) > float(get_balance(config['FAUCET_URL'], public_key, 'ether')):
            logger.info('Ether balance is less than the minimum amount to start the worker')
            if not get_coins_faucet(config['FAUCET_URL'], public_key, 'ether'):
                exit(-1)
            if float(config['MINIMUM_ETHER_BALANCE']) > float(get_balance(config['FAUCET_URL'], public_key, 'ether')):
                logger.error('Not enough ether to run the worker, exiting')
                exit(-2)

        if float(config['MINIMUM_ENG_BALANCE']) > float(get_balance(config['FAUCET_URL'], public_key, 'eng')):
            logger.info('Eng balance is less than the minimum amount to start the worker')
            if not get_coins_faucet(config['FAUCET_URL'], public_key, 'eng'):
                exit(-1)
            if float(config['MINIMUM_ENG_BALANCE']) > float(get_balance(config['FAUCET_URL'], public_key, 'eng')):
                logger.error('Not enough eng to run the worker, exiting')
                exit(-2)
        login_and_deposit = True

        w3provider = web3.HTTPProvider(f'http://{eth_node_address}')
        w3 = web3.Web3(w3provider)

        if not w3.isAddress(public_key):
            logger.error(f'Invalid ethereum address {public_key}')
            exit(-1)

        public_key = w3.toChecksumAddress(public_key)

        nonce = w3.eth.getTransactionCount(public_key)

        erc20 = w3.eth.contract(token_contract_address, abi=token_contract_abi['abi'])

        transaction = erc20.functions.approve(eng_contract_addr, deposit_amount).buildTransaction({'from': public_key,
                                                                                                   'gasPrice': 100000,
                                                                                                   'nonce': nonce})

        # logger.error(f'{transaction.items()}')

        from web3.auto import w3 as auto_w3

        # stupid_w3.eth.defaultAccount = public_key
        signed_tx = auto_w3.eth.account.sign_transaction(transaction, private_key=bytes.fromhex(priv[2:]))
        w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = w3.eth.waitForTransactionReceipt(signed_tx.hash)

        val = erc20.functions.allowance(eng_contract_addr, public_key).call()
        logger.info(f'{eng_contract_addr} ENG allowance: {val}')

    if is_bootstrap:
        p2p_runner = P2PNode(bootstrap=True,
                             ethereum_key=priv,
                             contract_address=eng_contract_addr,
                             public_address=public_key,
                             ether_node=eth_node_address,
                             abi_path=enigma_abi_path,
                             key_mgmt_node=km_node,
                             deposit_amount=deposit_amount,
                             login_and_deposit=login_and_deposit)
    else:
        bootstrap_node = config['BOOTSTRAP_ADDRESS']
        p2p_runner = P2PNode(bootstrap=False,
                             ethereum_key=priv,
                             contract_address=eng_contract_addr,
                             public_address=public_key,
                             ether_node=eth_node_address,
                             key_mgmt_node=km_node,
                             abi_path=enigma_abi_path,
                             bootstrap_address=bootstrap_node,
                             deposit_amount=deposit_amount,
                             login_and_deposit=login_and_deposit)

    # Setting workdir to the base path of the executable, because everything is fragile
    os.chdir(pathlib.Path(args.executable).parent)

    p2p_runner.run()
