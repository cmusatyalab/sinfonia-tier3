# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

from binascii import hexlify, unhexlify
from secrets import token_bytes

from sinfonia_tier3.curve25519 import X25519PrivateKey

# test vectors from
# https://github.com/TomCrypto/pycurve25519/blob/6cb15d7610c921956d7b33435fdf362ef7bf2ca4/test_curve25519.py
# https://www.rfc-editor.org/rfc/rfc7748#section-6.1
KEYPAIRS = [
    # TomCrypto pycurve25519/test_curve.py
    (
        b"a8abababababababababababababababababababababababababababababab6b",
        b"e3712d851a0e5d79b831c5e34ab22b41a198171de209b8b8faca23a11c624859",
    ),
    (
        b"c8cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd4d",
        b"b5bea823d9c9ff576091c54b7c596c0ae296884f0e150290e88455d7fba6126f",
    ),
    # RFC7748 6.1
    (
        b"77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a",
        b"8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a",
    ),
    (
        b"5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb",
        b"de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f",
    ),
]

# https://www.rfc-editor.org/rfc/rfc7748#section-5.2
RFC7748 = [
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"e6db6867583030db3594c1a424b15f7c726624ec26b3353b10a903a6d0ab1c4c",
        b"c3da55379de9c6908e94ea4df28d084f32eccf03491c71f754b4075577a28552",
    ),
    (
        b"4b66e9d4d1b4673c5ad22691957d6af5c11b6421e0ea01d42ca4169e7918ba0d",
        b"e5210f12786811d3f4b7959d0538ae2c31dbe7106fc03c3efc4cd549c715a493",
        b"95cbde9476e8907d7aade45cb4b873f88b595a68799fa152e6f8f7647aac7957",
    ),
    (
        b"0900000000000000000000000000000000000000000000000000000000000000",
        b"0900000000000000000000000000000000000000000000000000000000000000",
        b"422c8e7a6227d7bca1350b3e2bb7279f7897b87bb6854b783c60e80311ae3079",
    ),
]

# https://github.com/gpg/libgcrypt/blob/ccfa9f2c1427b40483984198c3df41f8057f69f8/tests/t-cv25519.c#L514  # noqa: E501
GCRYPT = [
    # Seven tests which result in 0.
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"0000000000000000000000000000000000000000000000000000000000000000",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"0100000000000000000000000000000000000000000000000000000000000000",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b800",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"5f9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f1157",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"eeffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
        b"0000000000000000000000000000000000000000000000000000000000000000",
    ),
    # Five tests which result in 0 if decodeUCoordinate didn't change MSB.
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"cdeb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b880",
        b"7ce548bc4919008436244d2da7a9906528fe3a6d278047654bd32d8acde9707b",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"4c9c95bca3508c24b1d0b1559c83ef5b04445cc4581c8e86d8224eddd09f11d7",
        b"e17902e989a034acdf7248260e2c94cdaf2fe1e72aaac7024a128058b6189939",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"d9ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        b"ea6e6ddf0685c31e152d5818441ac9ac8db1a01f3d6cb5041b07443a901e7145",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"daffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        b"845ddce7b3a9b3ee01a2f1fd4282ad293310f7a232cbc5459fb35d94bccc9d05",
    ),
    (
        b"a546e36bf0527c9d3b16154b82465edd62144c0ac1fc5a18506a2244ba449ac4",
        b"dbffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        b"6989e2cb1cea159acf121b0af6bf77493189c9bd32c2dac71669b540f9488247",
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
        private_bytes = unhexlify(private_hex)
        private_key = X25519PrivateKey.from_private_bytes(private_bytes)
        public_bytes = private_key.public_key()
        assert hexlify(public_bytes) == public_hex


def test_shared_1():
    # TomCrypt
    pri1, pub1 = map(unhexlify, KEYPAIRS[0])
    pri2, pub2 = map(unhexlify, KEYPAIRS[1])

    private_key1 = X25519PrivateKey.from_private_bytes(pri1)
    private_key2 = X25519PrivateKey.from_private_bytes(pri2)

    shared1 = private_key1.exchange(pub2)
    shared2 = private_key2.exchange(pub1)

    assert shared1 == shared2
    assert (
        hexlify(shared1)
        == b"235101b705734aae8d4c2d9d0f1baf90bbb2a8c233d831a80d43815bb47ead10"
    )

    # RFC7748 6.1
    pri3, pub3 = map(unhexlify, KEYPAIRS[2])
    pri4, pub4 = map(unhexlify, KEYPAIRS[3])

    private_key3 = X25519PrivateKey.from_private_bytes(pri3)
    private_key4 = X25519PrivateKey.from_private_bytes(pri4)

    shared3 = private_key3.exchange(pub4)
    shared4 = private_key4.exchange(pub3)

    assert shared3 == shared4
    assert (
        hexlify(shared3)
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


def test_rfc7748():
    for scalar, input_ucoord, output_ucoord in RFC7748:
        scalar_bytes = unhexlify(scalar)
        ucoord_bytes = unhexlify(input_ucoord)
        private_key = X25519PrivateKey.from_private_bytes(scalar_bytes)
        output_bytes = private_key.exchange(ucoord_bytes)
        assert hexlify(output_bytes) == output_ucoord

    # keep iterating on the last one one
    for _ in range(1000 - 1):
        ucoord_bytes, scalar_bytes = scalar_bytes, output_bytes
        private_key = X25519PrivateKey.from_private_bytes(scalar_bytes)
        output_bytes = private_key.exchange(ucoord_bytes)
    assert (
        hexlify(output_bytes)
        == b"684cf59ba83309552800ef566f2f4d3c1c3887c49360e3875f2eb94d99532c51"
    )

    # this test ran for about 2 1/2 hours, so we'll keep it commented
    # for _ in range(1000000-1000):
    #     ucoord_bytes, scalar_bytes = scalar_bytes, output_bytes
    #     private_key = X25519PrivateKey.from_private_bytes(scalar_bytes)
    #     output_bytes = private_key.exchange(ucoord_bytes)
    # assert (
    #     hexlify(output_bytes)
    #     == b"7c3911e0ab2586fd864497297e575e6f3bc601c0883c30df5f4dd2d24f665424"
    # )


def test_gcrypt():
    for scalar, input_ucoord, output_ucoord in GCRYPT:
        scalar_bytes = unhexlify(scalar)
        ucoord_bytes = unhexlify(input_ucoord)
        private_key = X25519PrivateKey.from_private_bytes(scalar_bytes)
        output_bytes = private_key.exchange(ucoord_bytes)
        assert hexlify(output_bytes) == output_ucoord
