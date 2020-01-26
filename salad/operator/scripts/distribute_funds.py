#!/usr/bin/env python3

import sys
from enigma_docker_common.faucet_api import request_coins


def main():
    addresses = sys.argv[1:]
    for address in addresses:
        for i in range(20):
            print(f'{i} - distributing ether to {address}')
            request_coins('http://contract.reuven.services.enigma.co:8001', address, 'ether')


if __name__ == '__main__':
    main()
