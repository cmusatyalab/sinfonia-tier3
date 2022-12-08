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
TUNNEL_UAPI_CONF = """\
set=1
private_key=0e72c499f2735680912585f37525c8853aa78f2827861e8ef88dc4acc4ba3948
replace_peers=true
public_key=6daf00c1ca250550ee851fcc28553c3ba099ac08e1edcdb487a10e9d0c745511
endpoint=127.0.0.1:51820
persistent_keepalive_interval=30
replace_allowed_ips=true
allowed_ip=10.0.0.1/32
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


def test_create_uapi_conf() -> None:
    private_key = WireguardKey(PRIVATE_KEY)
    config = WireguardConfig.from_dict(private_key, TUNNEL_CONFIG)
    assert config.uapi_conf() == TUNNEL_UAPI_CONF
