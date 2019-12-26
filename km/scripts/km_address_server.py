import logging

from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger
from flask import Flask, request
from flask_cors import CORS
from flask_restplus import Api, Resource
from flask_restplus import abort

config = Config()

logger = get_logger('km.server')

logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

application = Flask(__name__)
CORS(application)

api = Api(app=application, version='1.0')
ns = api.namespace('km', description='Contract operations')


@ns.route("/address")
class KMAddress(Resource):
    """ returns a list of tracked addresses for a chain/network. If parameters are empty, will return
    all addresses """
    @ns.param('name', 'Key management address filename -- by default right now can only be principal-sign-addr.txt', 'query')
    def get(self):  # pylint: disable=no-self-use
        filename = request.args.get('name')
        if filename not in config["KM_FILENAME"]:
            logger.error(f'Tried to retrieve file which was not in allowed file names: {filename}')
            return abort(404)
        contract_filename = f'{config["KEYPAIR_DIRECTORY"]}{filename}'
        try:
            with open(contract_filename) as f:
                return f.read()
        except FileNotFoundError:
            logger.critical(f'KM address not found -- probably misconfigured filename')
            return abort(500)


def start_server(port):
    application.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    start_server(8081)
