import web3
from web3.auto import w3 as auto_w3

from .logger import get_logger

logger = get_logger('enigma_common.enigma')


class Contract:

    max_gas_price = 20000000000
    gas_default = 300000

    def __init__(self, eth_node, contract_address, contract_abi):
        """
        :param eth_node: address of ethereum node (example: http://localhost:8545)
        :param contract_address: erc20 token contract address
        :param contract_abi: erc20 token contract ABI
        """
        self.eth_node = eth_node
        self.contract_address = contract_address
        self.contract_abi = contract_abi

        self.w3provider = web3.HTTPProvider(eth_node)
        self.w3 = web3.Web3(self.w3provider)
        self.contract = self.w3.eth.contract(contract_address, abi=contract_abi)

        self._gasprice = self.max_gas_price

    @staticmethod
    def toCheckSumAddress(address: str):
        return auto_w3.toChecksumAddress(address)

    @staticmethod
    def _sign(raw_tx, key: bytes) -> dict:
        # stupid_w3.eth.defaultAccount = public_key
        return auto_w3.eth.account.sign_transaction(raw_tx, private_key=key)

    def _send_and_wait(self, signed_tx):
        self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(signed_tx.hash)
        return tx_receipt

    @property
    def gasprice(self):
        est = self.w3.eth.generateGasPrice()
        if est:
            self._gasprice = max(int(est), self.max_gas_price)
        return self._gasprice

    def transact(self, sending_address, key, func, *args):
        transaction = self.build(sending_address, func, *args)
        signed_tx = self._sign(transaction, key)
        self._send_and_wait(signed_tx)

    def build(self, sending_address, func, *args):
        csum_addr = self.w3.toChecksumAddress(sending_address)
        nonce = self.w3.eth.getTransactionCount(csum_addr, 'pending')
        transaction = getattr(self.contract.functions, func)(*args).buildTransaction(
            {'from': csum_addr,
             'gasPrice': self.gasprice,
             'gas': self.gas_default,
             'nonce': nonce})
        return transaction


class EnigmaTokenContract(Contract):
    def _approve_build_transaction(self, approver: str, to: str, amount) -> dict:

        if not self.w3.isAddress(approver):
            raise ValueError(f'Invalid ethereum address {approver}')

        public_key = self.w3.toChecksumAddress(approver)
        nonce = self.w3.eth.getTransactionCount(public_key, 'pending')
        return self.contract.functions.approve(to, amount).buildTransaction({'from': public_key,
                                                                             'gasPrice': self.gasprice,
                                                                             'nonce': nonce})

    def approve(self, approver: str, to: str, amount, key: bytes):
        """
        Builds, signs, and sends approve command for {amount} ENG from {approver} to {to}

        :param amount amount to approve in fragments of ENG
        :param approver
        :param to
        :param key: [OPTIONAL] private key in bytes
        """
        self.transact(approver, key, 'approve', to, amount)

    def approve_build(self, approver: str, to: str, amount):
        """
        Builds approve command for {amount} ENG from {approver} to {to}

        :param amount amount to approve in fragments of ENG
        :param approver
        :param to
        :param key: [OPTIONAL] private key in bytes
        """
        return self.build(approver, 'approve', to, amount)

    def check_allowance(self, approver, to):
        approver = self.w3.toChecksumAddress(approver)
        to = self.w3.toChecksumAddress(to)
        val = self.contract.functions.allowance(approver, to).call()
        return val


class EnigmaContract(Contract):
    def deposit(self, staking_address: str, staking_key: bytes, eth_address: str, deposit_amount: int):
        self.transact(self.toCheckSumAddress(staking_address), staking_key, 'deposit',
                      self.toCheckSumAddress(eth_address), deposit_amount)

    # noinspection PyPep8Naming
    def setOperatingAddress(self, staking_address: str, eth_address: str):
        self.transact(self.toCheckSumAddress(staking_address), 'setOperatingAddress',
                      self.toCheckSumAddress(eth_address))

    def deposit_build(self, staking_address: str, eth_address: str, deposit_amount: int):
        return self.build(self.toCheckSumAddress(staking_address), 'deposit', self.toCheckSumAddress(eth_address),
                          deposit_amount)

    # noinspection PyPep8Naming
    def setOperatingAddress_build(self, staking_address: str, eth_address: str):
        return self.build(self.toCheckSumAddress(staking_address), 'setOperatingAddress', self.toCheckSumAddress(eth_address))
