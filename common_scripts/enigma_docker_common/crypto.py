import binascii
import os
import pathlib
from typing import Tuple

from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Hash import keccak
from Crypto.Util import Counter
from ecdsa import SigningKey, SECP256k1
from web3.auto import w3 as auto_w3

from .logger import get_logger
from .utils import remove_0x

logger = get_logger('enigma_common.crypto')

PRIVATE_KEY_NAME = 'keystore.bin'
ETHER_ADDRESS_NAME = 'eth_address.txt'

# AES supports multiple key sizes: 16 (AES128), 24 (AES192), or 32 (AES256).
KEY_BYTES = 32
IV_LEN = AES.block_size


def _derive_key(password: str) -> bytes:
    """ keccak256(password) """
    passwd_bytes = password.encode()
    keccak_hash = keccak.new(digest_bits=256)
    keccak_hash.update(passwd_bytes)
    key = keccak_hash.hexdigest()
    return bytes.fromhex(key)


def encrypt(password: str, plaintext: bytes) -> bytes:
    key = _derive_key(password)
    if len(key) != KEY_BYTES:
        raise RuntimeError(f'Wrong length in encryption key: expected:{KEY_BYTES}, got: {len(key)}')

    iv = Random.new().read(IV_LEN)
    iv_int = int(binascii.hexlify(iv), 16)

    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    ciphertext = aes.encrypt(plaintext)
    return iv+ciphertext


def decrypt(password, ciphertext: bytes) -> bytes:
    key = _derive_key(password)
    if len(key) != KEY_BYTES:
        raise RuntimeError(f'Wrong length in encryption key: expected:{KEY_BYTES}, got: {len(key)}')

    iv = ciphertext[:IV_LEN]
    iv_int = int(iv.hex(), 16)
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    plaintext = aes.decrypt(ciphertext[IV_LEN:])
    return plaintext


def generate_key() -> Tuple[str, bytes]:
    """
    Generate private key and public key
    Save as PEMs for management

    :return: ECDSA Key Object - pri_key, pub_key
    """
    pri_key = SigningKey.generate(curve=SECP256k1)
    pub_key = pri_key.get_verifying_key()
    return '0x' + pri_key.to_string().hex(), pub_key.to_string()


def address_from_private(pk) -> str:
    """
    Generate private key and public key
    Save as PEMs for management

    :return: ECDSA Key Object - pri_key, pub_key
    """
    pri_key = SigningKey.from_string(string=bytes.fromhex(remove_0x(pk)), curve=SECP256k1)
    pub_key = pri_key.get_verifying_key()
    return pubkey_to_addr(pub_key.to_string().hex())


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


def _create_keystore(privkey_path: pathlib.Path, pubkey_path: pathlib.Path, password: str = '') -> Tuple[str, str]:
    private_key, eth_address = get_eth_address()
    eth_address = auto_w3.toChecksumAddress(eth_address)
    if password:
        enc_key = encrypt(password, bytes.fromhex(private_key[2:])).hex()
        save_to_path(privkey_path, enc_key, 'w+')
    else:
        save_to_path(privkey_path, private_key, 'w+')
    save_to_path(pubkey_path, eth_address, 'w+')
    return private_key, eth_address


def open_eth_keystore(path: str, config: dict, password: str = '', create: bool = True):
    """ Create """
    privkey_path = pathlib.Path(path) / PRIVATE_KEY_NAME
    pubkey_path = pathlib.Path(path) / ETHER_ADDRESS_NAME

    if config.get('FORCE_NEW_ETH_ADDR', False):
        logger.info('Generating new address (forced)...')
        private_key, eth_address = _create_keystore(privkey_path, pubkey_path, password)
        logger.info(f'Done! New address is {eth_address}')
    else:  # try to open address from filesystem
        try:
            with open(pubkey_path, 'r') as f:
                eth_address = f.read()
            with open(privkey_path, 'r') as f:
                private_key = f.read()
                if password:
                    private_key = '0x' + decrypt(password, bytes.fromhex(private_key)).hex()
            logger.info(f'Loaded key from local filesystem, ethereum address: {eth_address}')
            # return private_key, eth_address

        except FileNotFoundError:
            logger.info('Ethereum address not found')
            if create:
                logger.info('Generating new address...')
                private_key, eth_address = _create_keystore(privkey_path, pubkey_path, password)
                logger.info(f'Done! New address is {eth_address}')
                # todo: add a check it was properly saved
            else:
                raise
    return private_key, eth_address
