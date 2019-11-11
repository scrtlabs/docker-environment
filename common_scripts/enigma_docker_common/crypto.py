import os
import pathlib
from typing import Tuple

from .logger import get_logger

from Crypto.Hash import keccak
from ecdsa import SigningKey, SECP256k1, VerifyingKey


logger = get_logger('enigma_common.crypto')

PRIVATE_KEY_NAME = 'keystore.bin'
ETHER_ADDRESS_NAME = 'eth_address.txt'


def generate_key() -> Tuple[str, bytes]:
    """
    Generate private key and public key
    Save as PEMs for management

    :return: ECDSA Key Object - pri_key, pub_key
    """
    pri_key = SigningKey.generate(curve=SECP256k1)
    pub_key = pri_key.get_verifying_key()
    return '0x' + pri_key.to_string().hex(), pub_key.to_string()


def pubkey_to_addr(pubkey: str) -> str:
    public_key_bytes = bytes.fromhex(pubkey)
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(public_key_bytes)
    keccak_digest = keccak_hash.hexdigest()
    # Take the last 20 bytes
    wallet_len = 40
    wallet = "0x" + keccak_digest[-wallet_len:]
    return wallet


def get_eth_address() -> Tuple[str, str]:
    priv, pub = generate_key()
    public_key = pubkey_to_addr(pub.hex())
    return priv, public_key


def save_to_path(path, file, flags='wb+'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, flags) as f:
        f.write(file)


def open_eth_keystore(path: str, config: dict, create: bool = True):
    """ Create"""
    privkey_path = pathlib.Path(path) / PRIVATE_KEY_NAME
    pubkey_path = pathlib.Path(path) / ETHER_ADDRESS_NAME

    if config.get('FORCE_NEW_ETH_ADDR', False):
        private_key, eth_address = get_eth_address()
        save_to_path(privkey_path, private_key, 'w+')
        save_to_path(pubkey_path, eth_address, 'w+')
    else:  # try to open address from filesystem
        try:
            with open(pubkey_path, 'r') as f:
                eth_address = f.read()
            with open(privkey_path, 'r') as f:
                private_key = f.read()

            logger.info(f'Loaded key from local filesystem, ethereum address: {eth_address}')
            # return private_key, eth_address

        except FileNotFoundError:
            logger.info('Ethereum address not found')
            if create:
                logger.info('Generating new address...')
                private_key, eth_address = get_eth_address()
                save_to_path(privkey_path, private_key, 'w+')
                save_to_path(pubkey_path, eth_address, 'w+')
                logger.info(f'Done! New address is {eth_address}')
                # todo: add a check it was properly saved
            else:
                raise
    return private_key, eth_address
