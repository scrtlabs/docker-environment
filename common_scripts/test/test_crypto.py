from enigma_docker_common.crypto import encrypt, decrypt, EthereumKey, address_from_private, auto_w3


def test_enc_dec():
    encrypted = encrypt('cupcake', b'\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00')
    # print(f'len: {len(encrypted)} {encrypted.hex()}')
    assert len(encrypted) == 48
    expected = b'\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00'
    plaintext = decrypt('cupcake', encrypted)
    assert plaintext == expected


def test_address_from_private():
    key = '0x6c7adb28f9462347bcb30524030ed2f3e61a3bdf84e881a18b0c505d72b434d2'
    expected = '0x328a3CCf03bEC98FfA649e4Cc9bD31f0a353899c'
    result = auto_w3.toChecksumAddress(address_from_private(key))

    assert result == expected


def test_ethereum_key():
    eth_key = EthereumKey(key='0x61cabe95221171f4ee1d90d916a5f7f130f79c73dc818b3b38db734ab75ee55c')
    expected = EthereumKey(key='0x61cabe95221171f4ee1d90d916a5f7f130f79c73dc818b3b38db734ab75ee55c',
                           address='0x63C15192B8ED7294129b76A5a870bCFBf8D4c856')

    assert eth_key == expected
