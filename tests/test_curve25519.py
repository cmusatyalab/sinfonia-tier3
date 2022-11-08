# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

import binascii
from secrets import token_bytes

from sinfonia_tier3.curve25519 import X25519PrivateKey

# test vectors from
# https://github.com/TomCrypto/pycurve25519/blob/6cb15d7610c921956d7b33435fdf362ef7bf2ca4/test_curve25519.py
# https://www.rfc-editor.org/rfc/rfc7748#section-6.1

KEYPAIRS = [
    # (private_key, public_key)
    (
        b"a8abababababababababababababababababababababababababababababab6b",
        b"e3712d851a0e5d79b831c5e34ab22b41a198171de209b8b8faca23a11c624859",
    ),
    (
        b"c8cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd4d",
        b"b5bea823d9c9ff576091c54b7c596c0ae296884f0e150290e88455d7fba6126f",
    ),
    (
        b"77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a",
        b"8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a",
    ),
    (
        b"5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb",
        b"de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f",
    ),
]


def test_private_key():
    for _ in range(1024):
        data = token_bytes(32)
        private_bytes = X25519PrivateKey.from_private_bytes(data).private_bytes()

        # check if the key is properly formatted
        assert (private_bytes[0] & (~248)) == 0
        assert (private_bytes[31] & (~127)) == 0
        assert (private_bytes[31] & 64) != 0


def test_public_key():
    for private_hex, public_hex in KEYPAIRS:
        private_bytes = binascii.unhexlify(private_hex)
        private_key = X25519PrivateKey.from_private_bytes(private_bytes)
        public_bytes = private_key.public_key()
        assert binascii.hexlify(public_bytes) == public_hex


def test_shared_1():
    # TomCrypt
    pri1, pub1 = map(binascii.unhexlify, KEYPAIRS[0])
    pri2, pub2 = map(binascii.unhexlify, KEYPAIRS[1])

    private_key1 = X25519PrivateKey.from_private_bytes(pri1)
    private_key2 = X25519PrivateKey.from_private_bytes(pri2)

    shared1 = private_key1.exchange(pub2)
    shared2 = private_key2.exchange(pub1)

    assert shared1 == shared2
    assert (
        binascii.hexlify(shared1)
        == b"235101b705734aae8d4c2d9d0f1baf90bbb2a8c233d831a80d43815bb47ead10"
    )

    # RFC7748
    pri3, pub3 = map(binascii.unhexlify, KEYPAIRS[2])
    pri4, pub4 = map(binascii.unhexlify, KEYPAIRS[3])

    private_key3 = X25519PrivateKey.from_private_bytes(pri3)
    private_key4 = X25519PrivateKey.from_private_bytes(pri4)

    shared3 = private_key3.exchange(pub4)
    shared4 = private_key4.exchange(pub3)

    assert shared3 == shared4
    assert (
        binascii.hexlify(shared3)
        == b"4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742"
    )


def test_shared_2():
    for _ in range(1024):
        pri1 = X25519PrivateKey.from_private_bytes(token_bytes(32))
        pri2 = X25519PrivateKey.from_private_bytes(token_bytes(32))
        pub1 = pri1.public_key()
        pub2 = pri2.public_key()
        shared1 = pri1.exchange(pub2)
        shared2 = pri2.exchange(pub1)
        assert shared1 == shared2
