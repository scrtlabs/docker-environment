from typing import Callable

import web3

from .logger import get_logger

logger = get_logger('enigma_common.enigma')


class EnigmaTokenContract:
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
        self.erc20 = self.w3.eth.contract(contract_address, abi=contract_abi)

    def approve_build_transaction(self, approver: str, to: str, amount) -> dict:

        if not self.w3.isAddress(approver):
            raise ValueError(f'Invalid ethereum address {approver}')

        public_key = self.w3.toChecksumAddress(approver)
        nonce = self.w3.eth.getTransactionCount(public_key)
        erc20 = self.w3.eth.contract(self.contract_address, abi=self.contract_abi)
        return erc20.functions.approve(to, amount).buildTransaction({'from': public_key,
                                                                     'gasPrice': 100000,
                                                                     'nonce': nonce})

    @staticmethod
    def _sign(raw_tx, key: bytes) -> dict:
        from web3.auto import w3 as auto_w3
        # stupid_w3.eth.defaultAccount = public_key
        return auto_w3.eth.account.sign_transaction(raw_tx, private_key=key)

    def send_and_wait(self, signed_tx):
        self.w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        tx_receipt = self.w3.eth.waitForTransactionReceipt(signed_tx.hash)
        return tx_receipt

    def approve(self, approver: str, to: str, amount, key: bytes):
        """
        Builds, signs, and sends approve command for {amount} ENG from {approver} to {to}

        :param amount amount to approve in fragments of ENG
        :param approver
        :param to
        :param key: [OPTIONAL] private key in bytes
        """
        raw_tx = self.approve_build_transaction(approver, to, amount)
        signed_tx = self._sign(raw_tx, key)
        self.send_and_wait(signed_tx)

    def check_allowance(self, approver, to):
        approver = self.w3.toChecksumAddress(approver)
        to = self.w3.toChecksumAddress(to)
        val = self.erc20.functions.allowance(approver, to).call()
        return val
