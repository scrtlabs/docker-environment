from typing import Tuple

from Crypto.Hash import keccak
from ecdsa import SigningKey, SECP256k1, VerifyingKey


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
