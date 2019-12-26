import web3

from .logger import get_logger

logger = get_logger('enigma_common.enigma')


class EthereumGateway:
    def __init__(self, eth_node: str):
        self.provider = web3.HTTPProvider(eth_node)
        self.w3 = web3.Web3(self.provider)

    def balance(self, account: str) -> str:
        if not self.w3.isAddress(account):
            raise ValueError(f'Trying to get balance for malformed ethereum account {account}')
        account = self.w3.toChecksumAddress(account)
        val = self.w3.fromWei(self.w3.eth.getBalance(account), 'ether')
        return str(val)


def check_eth_limit(account: str,
                    min_ether: float,
                    eth_node: str) -> bool:
    eth_gateway = EthereumGateway(eth_node)
    cur_balance = float(eth_gateway.balance(account))
    if min_ether > cur_balance:
        logger.info(f'Ethereum balance {cur_balance} is less than the minimum amount {min_ether} ETH required to start '
                    f'the worker. Please transfer currency to the worker account: {account} and restart the worker')
        return False
    return True
