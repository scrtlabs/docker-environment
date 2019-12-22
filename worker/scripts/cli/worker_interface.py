import asyncio
import requests
import aiohttp
import subprocess
import json
from typing import Union

from aiofile import AIOFile
from enigma_docker_common import storage

from enigma_docker_common.provider import Provider
from enigma_docker_common.utils import remove_0x
from enigma_docker_common.crypto import open_eth_keystore, address_from_private
from enigma_docker_common.enigma import EnigmaTokenContract, EnigmaContract


class WorkerInterface:

    available_actions = ["register", "login", "logout"]

    def __init__(self, config):
        self.worker_config = config
        self.cli_config = storage.LocalStorage(directory=config["STAKE_KEY_PATH"], flags='+')
        self.provider = Provider(config=config)
        eng_contract_addr = self._address_as_string(self.provider.enigma_contract_address)
        token_contract_addr = self._address_as_string(self.provider.token_contract_address)

        self.eng_contract = EnigmaContract(config["ETH_NODE_ADDRESS"],
                                      self.provider.enigma_contract_address,
                                      json.loads(self.provider.enigma_abi)['abi'])

        self.erc20_contract = EnigmaTokenContract(config["ETH_NODE_ADDRESS"],
                                             token_contract_addr,
                                             json.loads(self.provider.enigma_token_abi)['abi'])

    @staticmethod
    def restart():
        subprocess.Popen([f'supervisorctl', 'restart', 'p2p'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    # http: // localhost: 23456 / mgmt /
    async def do_action(self, action: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.worker_config["MGMT_URL"]}{action}') as response:
                resp = await response.text()
                if response.status == 200:
                    return 'Success!'
                           
                else:
                    return 'Failed - See detailed logs located in your worker-p2p ssh window for more information!'

    async def get_status(self):
        filename = f'{self.worker_config["ETH_KEY_PATH"]}{self.worker_config["STATUS_FILENAME"]}'
        async with AIOFile(filename, 'r') as f:
            status = await f.read()
            return status

    async def get_staking_address(self):
        filename = f'{self.worker_config["STAKE_KEY_PATH"]}{self.worker_config["ETHEREUM_ADDR_FILENAME"]}'
        async with AIOFile(filename, 'r') as f:
            staking_address = await f.read()
            return staking_address

    async def get_eth_address(self):
        filename = f'{self.worker_config["ETH_KEY_PATH"]}{self.worker_config["ETHEREUM_ADDR_FILENAME"]}'
        async with AIOFile(filename, 'r') as f:
            eth_address = await f.read()
            return eth_address

    async def set_staking_address(self, address):
        filename = f'{self.worker_config["STAKE_KEY_PATH"]}{self.worker_config["ETHEREUM_ADDR_FILENAME"]}'
        async with AIOFile(filename, 'w+') as f:
            await f.write(address)

    async def get_connections(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.worker_config["MGMT_URL"]}connections') as response:
                resp = await response.text()
                if response.status == 200:
                    return resp
                else:
                    return 0

    @staticmethod
    def _address_as_string(addr: Union[bytes, str]) -> str:
        if isinstance(addr, bytes):
            addr = addr.decode()
        return addr

    def generate_set_operating_address(self, staking_address, eth_address):
        tx = self.eng_contract.setOperatingAddress_build(staking_address, eth_address)
        if 'data' in tx:
            return str(tx['data'])
        else:
            return "Failed to generate transaction data"

    def generate_deposit(self, staking_address, deposit_amount):
        tx = self.eng_contract.build(staking_address, 'deposit', staking_address, deposit_amount)
        if 'data' in tx:
            return str(tx['data'])
        else:
            return "Failed to generate transaction data"

    def generate_approve(self, staking_address, deposit_amount):
        tx = self.erc20_contract.approve_build(staking_address, self.provider.enigma_contract_address, deposit_amount)
        if 'data' in tx:
            return str(tx['data'])
        else:
            return "Failed to generate transaction data"
