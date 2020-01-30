#!/usr/bin/env python3

import sys
from enigma_docker_common.faucet_api import request_coins
from enigma_docker_common.config import Config
from enigma_docker_common.logger import get_logger

logger = get_logger('operator-startup')

try:
    config = Config(required=['FAUCET_URL'])
except (ValueError, IOError) as e:
    logger.critical(f'encountered unexpected error while configuring the operator: {e!r}')
    raise


def main():
    addresses = sys.argv[1:]
    faucet_url = config['FAUCET_URL']
    for address in addresses:
        print(f'distributing ether to {address}')
        request_coins(faucet_url, address, 'ether')
        print(f'distributing eng to {address}')
        request_coins(faucet_url, address, 'eng')


if __name__ == '__main__':
    main()
