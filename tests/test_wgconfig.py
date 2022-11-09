# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

import copy
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from sinfonia_tier3.wireguard import WireguardConfig, WireguardKey

IFNAME = "wg-test"
UUID = "00000000-0000-0000-0000-000000000000"
PRIVATE_KEY = "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg="
TUNNEL_CONFIG = {
    "publicKey": "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=",
    "allowedIPs": ["10.0.0.1/32"],
    "endpoint": "127.0.0.1:51820",
    "address": ["10.0.0.2/32"],
    "dns": ["10.0.0.1", "test.svc.cluster.local"],
    "privateKey": "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=",
}
TUNNEL_CONFIG_CONTENT = """\
[Interface]
PrivateKey = DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=

[Peer]
PublicKey = DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=
AllowedIPs = 10.0.0.1/32
Endpoint = 127.0.0.1:51820
"""


def test_create_wireguard_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    private_key = WireguardKey(PRIVATE_KEY)
    config = WireguardConfig.from_dict(private_key, TUNNEL_CONFIG)
    config.write_wireguard_conf(f"./{IFNAME}.conf")

    generated_conffile = tmp_path / f"{IFNAME}.conf"
    assert generated_conffile.exists()
    assert generated_conffile.read_text() == TUNNEL_CONFIG_CONTENT


def test_create_wireguard_missing_config(
    monkeypatch: MonkeyPatch, tmp_path: str
) -> None:
    monkeypatch.chdir(tmp_path)

    bad_config = copy.deepcopy(TUNNEL_CONFIG)
    del bad_config["publicKey"]

    with pytest.raises(KeyError):
        private_key = WireguardKey(PRIVATE_KEY)
        WireguardConfig.from_dict(private_key, bad_config)
