#
# Sinfonia
#
# Copyright (c) 2022 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#
"""Wireguard key handling.

Validate and convert between standard and urlsafe encodings.
"""

from __future__ import annotations

import os
from base64 import standard_b64encode, urlsafe_b64decode, urlsafe_b64encode
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv6Address,
    IPv6Interface,
    ip_address,
    ip_interface,
)
from pathlib import Path
from typing import Any

import wgconfig
from attrs import define, field


def convert_wireguard_key(value: str | WireguardKey) -> bytes:
    """Accepts urlsafe encoded base64 keys with possibly missing padding.
    Checks if the (decoded) key is a 32-byte byte string
    """
    if isinstance(value, WireguardKey):
        return value.keydata

    raw_key = urlsafe_b64decode(value + "==")

    if len(raw_key) != 32:
        raise ValueError

    return raw_key


@define
class WireguardKey:
    keydata: bytes = field(converter=convert_wireguard_key)

    def __str__(self) -> str:
        return standard_b64encode(self.keydata).decode("utf-8")

    @property
    def urlsafe(self) -> str:
        return urlsafe_b64encode(self.keydata).decode("utf-8").rstrip("=")

    @property
    def k8s_label(self) -> str:
        """Kubernetes label values have to begin and end with alphanumeric
        characters and be less than 63 byte."""
        return f"wg-{self.urlsafe}-pubkey"

    @classmethod
    def validate(cls, value: str) -> bool:
        try:
            cls(value)
            return True
        except ValueError:
            return False

    @classmethod
    def unmarshal(cls, value):
        return value


def is_ipaddress(value: str) -> bool:
    try:
        return ip_address(value) is not None
    except ValueError:
        return False


@define
class WireguardConfig:
    # Interface
    private_key: WireguardKey
    addresses: list[IPv4Interface | IPv6Interface]
    dns_servers: list[IPv4Address | IPv6Address]
    search_domains: list[str]
    # Peer
    public_key: WireguardKey
    endpoint_host: IPv4Address | IPv6Address | str
    endpoint_port: int
    allowed_ips: list[IPv4Interface | IPv6Interface]

    @classmethod
    def from_dict(
        cls, private_key: WireguardKey, config: dict[str, Any]
    ) -> WireguardConfig:
        addresses = [ip_interface(addr) for addr in config["address"]]
        dns_servers = [
            ip_address(value) for value in config["dns"] if is_ipaddress(value)
        ]
        search_domains = [value for value in config["dns"] if not is_ipaddress(value)]
        public_key = WireguardKey(config["publicKey"])
        endpoint_addr, endpoint_port = config["endpoint"].rsplit(":")
        endpoint_host = (
            ip_address(endpoint_addr) if is_ipaddress(endpoint_addr) else endpoint_addr
        )
        endpoint_port = int(endpoint_port)
        allowed_ips = [ip_interface(addr) for addr in config["allowedIPs"]]
        return cls(
            private_key,
            addresses,
            dns_servers,
            search_domains,
            public_key,
            endpoint_host,
            endpoint_port,
            allowed_ips,
        )

    def write_wireguard_conf(self, filename: os.PathLike | str) -> None:
        """Create wireguard tunnel configuration"""
        wireguard_config = wgconfig.WGConfig(Path(filename).resolve())

        # [Interface]
        wireguard_config.add_attr(None, "PrivateKey", self.private_key)

        # [Peer]
        peer_key = str(self.public_key)
        wireguard_config.add_peer(peer_key)
        wireguard_config.add_attr(
            peer_key,
            "AllowedIPs",
            ", ".join(str(addr) for addr in self.allowed_ips),
        )
        wireguard_config.add_attr(
            peer_key, "Endpoint", f"{self.endpoint_host}:{self.endpoint_port}"
        )

        wireguard_config.write_file()

    def dump_resolv_conf(self) -> str:
        name_servers = [f"nameserver {entry}" for entry in self.dns_servers]
        search_domains = [entry for entry in self.search_domains]

        resolvconf_config = "\n".join(name_servers)
        if search_domains:
            resolvconf_config += " ".join(["\nsearch"] + search_domains)
        resolvconf_config += "\noptions ndots:5"
        return resolvconf_config

    def write_resolv_conf(self, filename: os.PathLike | str) -> None:
        Path(filename).write_text(self.dump_resolv_conf())
