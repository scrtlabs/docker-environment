#!/usr/bin/env python3

import sys
from enigma_docker_common.faucet_api import request_coins


def main():
    addresses = sys.argv[1:]
    for address in addresses:
        print(f'distributing ether to {address}')
        request_coins('http://contract.reuven.services.enigma.co:8001', address, 'ether')
        print(f'distributing eng to {address}')
        request_coins('http://contract.reuven.services.enigma.co:8001', address, 'eng')


if __name__ == '__main__':
    main()
