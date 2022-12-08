# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

import copy

import pytest

from sinfonia_tier3.wireguard import WireguardConfig, WireguardKey

IFNAME = "wg-test"
UUID = "00000000-0000-0000-0000-000000000000"
PRIVATE_KEY = "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg="
TUNNEL_CONFIG = {
    "publicKey": "ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE=",
    "allowedIPs": ["10.0.0.1/32"],
    "endpoint": "127.0.0.1:51820",
    "address": ["10.0.0.2/32"],
    "dns": ["10.0.0.1", "test.svc.cluster.local"],
    "privateKey": "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=",
}
TUNNEL_WGCONFIG = """\
[Interface]
PrivateKey = DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=

[Peer]
PublicKey = ba8AwcolBVDuhR/MKFU8O6CZrAjh7c20h6EOnQx0VRE=
AllowedIPs = 10.0.0.1/32
Endpoint = 127.0.0.1:51820
"""
TUNNEL_RESOLV_CONF = """\
nameserver 10.0.0.1
search test.svc.cluster.local
options ndots:5
"""


def test_create_wireguard_config() -> None:
    private_key = WireguardKey(PRIVATE_KEY)
    config = WireguardConfig.from_dict(private_key, TUNNEL_CONFIG)
    assert config.wireguard_conf() == TUNNEL_WGCONFIG


def test_create_wireguard_missing_config() -> None:
    bad_config = copy.deepcopy(TUNNEL_CONFIG)
    del bad_config["publicKey"]

    with pytest.raises(KeyError):
        private_key = WireguardKey(PRIVATE_KEY)
        WireguardConfig.from_dict(private_key, bad_config)


def test_create_resolv_conf() -> None:
    private_key = WireguardKey(PRIVATE_KEY)
    config = WireguardConfig.from_dict(private_key, TUNNEL_CONFIG)
    assert config.resolv_conf() == TUNNEL_RESOLV_CONF
