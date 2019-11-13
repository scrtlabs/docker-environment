from enigma_docker_common.crypto import encrypt, decrypt


def test_enc_dec():
    encrypted = encrypt('cupcake', b'\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00')
    # print(f'len: {len(encrypted)} {encrypted.hex()}')
    assert len(encrypted) == 48
    expected = b'\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00'
    plaintext = decrypt('cupcake', encrypted)
    assert plaintext == expected
