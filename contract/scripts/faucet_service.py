import logging
import json
import os
import random
import time
import web3
import threading

from flask import Flask, request
from flask_cors import CORS
from flask_restplus import Api, Resource, abort

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger
from enigma_docker_common.provider import Provider

logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

# use this logger if you need to add logs. No need to customize the logger further
logger = get_logger('enigma-contract.faucet')

required = [
            "ETH_NODE_ADDRESS", "CONTRACT_DISCOVERY_ADDRESS",
            "FAUCET_PORT", "BLOCK_TIME"]

env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}

config = Config(required=required, config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])
eng_provider = Provider(config=config)

PORT = config['FAUCET_PORT']
NODE_URL = config["ETH_NODE_ADDRESS"]

ETH_ALLOWANCE_AMT = config.get('ALLOWANCE_AMOUNT', web3.Web3.toWei(1, 'ether'))
ENG_ALLOWANCE_AMT = config.get('ENG_ALLOWANCE_AMOUNT', 100000)

token_contract_abi = json.loads(eng_provider.enigma_token_abi)
token_contract_address = eng_provider.token_contract_address

enigma_abi = json.loads(eng_provider.enigma_abi)
enigma_contract_address = eng_provider.enigma_contract_address

provider = web3.HTTPProvider(NODE_URL)
w3 = web3.Web3(provider)
erc20 = w3.eth.contract(token_contract_address, abi=token_contract_abi['abi'])
enigma_contract = w3.eth.contract(enigma_contract_address, abi=enigma_abi['abi'])


class CoinBaseProvider:
    @staticmethod
    def address():
        """ returns an unlocked address """
        return random.choice(['0x90f8bf6a479f320ead074411a4b0e7944ea8c9c1',
                              '0xffcf8fdee72ac11b5c542428b35eef5769c409f0',
                              '0x22d491bde2303f2f43325b2108d26f1eaba1e32b',
                              '0xe11ba2b4d45eaed5996cd0823791e0c93114882d',
                              '0xd03ea8624c8c5987235048901fb614fdca89b117',
                              '0x95ced938f7991cd0dfcb48f0a06a40fa1af46ebc',
                              '0x3e5e9111ae8eb78fe1cc3bb8915d5d461f3ef9a9',
                              '0x28a8746e75304c0780e011bed21c72cd78cd535e',
                              '0xaca94ef8bd5ffee41947b4585a84bda5a3d3da6e'])

    @staticmethod
    def eng_token_acc():
        return w3.eth.accounts[0]


application = Flask(__name__)
CORS(application)

api = Api(app=application)

faucet_ns = api.namespace('faucet', description='faucet operations')


@faucet_ns.route("/balance/ether")
class BalanceEther(Resource):
    """ Returns the balance of an account """
    @faucet_ns.param('account', 'Address to send currency to', 'query')
    def get(self):
        # your code here
        account = request.args.get('account')
        if not w3.isAddress(account):
            return abort(400, f'Invalid ethereum address {account}')
        account = w3.toChecksumAddress(account)
        val = w3.fromWei(w3.eth.getBalance(account), 'ether')
        return str(val)


@faucet_ns.route("/balance/eng")
class BalanceEng(Resource):
    """ Returns the balance of an account """
    @faucet_ns.param('account', 'Address to send currency to', 'query')
    def get(self):
        # your code here
        account = request.args.get('account')
        if not w3.isAddress(account):
            return abort(400, f'Invalid ethereum address {account}')
        account = w3.toChecksumAddress(account)
        val = erc20.functions.balanceOf(account).call()
        return str(val)


@faucet_ns.route("/ether")
class TransferEther(Resource):
    """ Returns a  """
    @faucet_ns.param('account', 'Address to send currency to', 'query')
    def get(self):
        # your code here
        account = request.args.get('account')
        if not w3.isAddress(account):
            return abort(400, f'Invalid ethereum address {account}')
        account = w3.toChecksumAddress(account)
        coinbase = w3.toChecksumAddress(CoinBaseProvider.address())
        w3.eth.sendTransaction({'to': account, 'from': coinbase, 'value': ETH_ALLOWANCE_AMT})

        return {'status': 'success',
                'result': {'to': account, 'from': coinbase, 'value': ETH_ALLOWANCE_AMT}}


@faucet_ns.route("/eng")
class TransferEng(Resource):
    """ placeholder till we figure out what to do with this """
    @faucet_ns.param('account', 'Address to send currency to', 'query')
    def get(self):
        # your code here
        account = request.args.get('account')
        if not w3.isAddress(account):
            return abort(400, f'Invalid ethereum address {account}')

        account = w3.toChecksumAddress(account)
        coinbase = w3.toChecksumAddress(CoinBaseProvider.eng_token_acc())

        val = erc20.functions.balanceOf(coinbase).call()
        logger.debug(f'{account} ENG balance: {val}')

        tx_hash = erc20.functions.transfer(account, ENG_ALLOWANCE_AMT).transact({'from': coinbase})
        _ = w3.eth.waitForTransactionReceipt(tx_hash)
        val = erc20.functions.balanceOf(account).call()
        logger.debug(f'{account} ENG balance: {val}')

        # tx_hash = erc20.functions.approve(coinbase, 90).transact({'from': account})
        # tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)

        # tx_hash = enigma_contract.functions.deposit(account, 90).transact({'from': account})
        # logger.info(f'Deposit tx_hash: {tx_hash}')
        # # tx_receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        #

        return {'status': 'success',
                'result': {'to': account, 'from': coinbase, 'value': ENG_ALLOWANCE_AMT}}

######################################


def block_miner():
    if config.get('AUTO_MINER', None):
        logger.info('Starting auto miner')
        mining_delay = int(config.get('TIME_BETWEEN_BLOCKS', 60))
        logger.info(f'Time between transactions: {mining_delay}')
        logger.info(f'Time to confirm block: {config["BLOCK_TIME"]}')
        block_time = int(config["BLOCK_TIME"])
        epoch_time = int(config["EPOCH_SIZE"]) * max(mining_delay, block_time)
        logger.info(f'Min epoch time: {epoch_time}s')
        random_acc = '0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b'
        while True:
            coinbase = w3.toChecksumAddress(CoinBaseProvider.address())
            w3.eth.sendTransaction({'to': random_acc, 'from': coinbase, 'value': 1})
            logger.debug('Sent Transaction -- should create new block')
            time.sleep(mining_delay)


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        logging.warning('Not running with the Werkzeug Server')
    else:
        func()


def run(port: int = None):
    listen = config.get("FAUCET_ADDRESS", '0.0.0.0')
    application.run(host=listen, port=port or PORT)


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=0, type=int, help='port to listen on')
    args = parser.parse_args()

    miner_thread = threading.Thread(target=block_miner, args=())
    miner_thread.start()

    run(args.port)
