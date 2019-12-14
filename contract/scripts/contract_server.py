import logging
import json
import os

from flask import Flask, request
from flask_cors import CORS
from flask_restplus import Api, Resource
from flask_restplus import abort


from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger

env_defaults = {'K8S': './config/k8s_config.json',
                'TESTNET': './config/testnet_config.json',
                'MAINNET': './config/mainnet_config.json',
                'COMPOSE': './config/compose_config.json'}

config = Config(config_file=env_defaults[os.getenv('ENIGMA_ENV', 'COMPOSE')])

logger = get_logger('enigma-contract.server')

logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

application = Flask(__name__)
CORS(application)

api = Api(app=application, version='1.0')
contract_ns = api.namespace('contract', description='Contract operations')


@contract_ns.route("/address")
class GetAddress(Resource):
    """ returns a list of tracked addresses for a chain/network. If parameters are empty, will return
    all addresses """
    @contract_ns.param('name', 'contract name -- by default right now can only be enigmacontract.txt '
                               'or engimatokencontract.txt', 'query')
    def get(self):
        contract_name = request.args.get('name')
        try:
            if contract_name not in config["CONTRACT_FILES"]:
                logger.error(f'Tried to retrieve file which was not in allowed file names: {contract_name}')
                return abort(404)
            contract_filename = f'{config["CONTRACT_PATH"]}{contract_name}'
            with open(contract_filename) as f:
                return f.read()
        except FileNotFoundError as e:
            logger.error(f'File not found: {e}')
            return abort(404)
        except json.JSONDecodeError as e:
            logger.error(f'Error decoding config file. Is it valid JSON? {e}')
            return abort(500)


@contract_ns.route("/abi")
class GetAddress(Resource):
    """ Will return a contract ABI from the build/contracts folder """
    @contract_ns.param('name', 'contract name -- Must be a single json file', 'query')
    def get(self):
        contract_name: str = request.args.get('name')
        try:
            if not contract_name.endswith('.json'):
                logger.error(f'Tried to retrieve file which was not in allowed file names: {contract_name}')
                return abort(404)
            contract_filename = f'{config["BUILT_CONTRACT_FOLDER"]}{contract_name}'
            with open(contract_filename, 'r') as f:
                return f.read()
        except FileNotFoundError as e:
            logger.error(f'File not found: {e}')
            return abort(404)
        except json.JSONDecodeError as e:
            logger.error(f'Error decoding config file. Is it valid JSON? {e}')
            return abort(500)


def run(port):
    logger.debug("using port:"+str(port))
    application.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8081, type=int, help='port to listen on')
    args = parser.parse_args()
    run(args.port)
