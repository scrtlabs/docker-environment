import web3


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
