import requests
import aiohttp
from aiofile import AIOFile
from enigma_docker_common import storage


class WorkerInterface:

    available_actions = ["register", "login", "logout"]

    def __init__(self, config):
        staking_address = ''
        self.worker_config = config
        self.cli_config = storage.LocalStorage(directory=config["STAKE_KEY_PATH"], flags='+')

    # http: // localhost: 23456 / mgmt /
    async def do_action(self, action: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.worker_config["MGMT_URL"]}{action}') as response:
                resp = await response.text()
                if response.status == 200:
                    return 'YAY great success!'
                else:
                    return 'AWW it failed :('

    async def get_status(self):
        filename = f'{self.worker_config["ETH_KEY_PATH"]}{self.worker_config["STATUS_FILENAME"]}'
        async with AIOFile(filename, 'r') as f:
            status = await f.read()
            return status

    async def get_staking_address(self):
        filename = f'{self.worker_config["STAKE_KEY_PATH"]}{self.worker_config["STAKE_KEY_NAME"]}'
        async with AIOFile(filename, 'r') as f:
            staking_address = await f.read()
            return staking_address

    async def get_eth_address(self):
        filename = f'{self.worker_config["ETH_KEY_PATH"]}{self.worker_config["ETHEREUM_ADDR_FILENAME"]}'
        async with AIOFile(filename, 'r') as f:
            eth_address = await f.read()
            return eth_address

    async def set_staking_address(self, address):
        filename = f'{self.worker_config["STAKE_KEY_PATH"]}{self.worker_config["STAKE_KEY_NAME"]}'
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
