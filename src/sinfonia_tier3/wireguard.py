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
from configparser import ConfigParser, SectionProxy
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv6Address,
    IPv6Interface,
    ip_address,
    ip_interface,
)
from pathlib import Path
from secrets import token_bytes
from typing import Any, TextIO

from attrs import define, field

from .curve25519 import X25519PrivateKey


def convert_wireguard_key(value: str | bytes | WireguardKey) -> bytes:
    """Accepts urlsafe encoded base64 keys with possibly missing padding.
    Checks if the (decoded) key is a 32-byte byte string
    """
    if isinstance(value, WireguardKey):
        return value.keydata

    if isinstance(value, bytes):
        raw_key = value
    else:
        raw_key = urlsafe_b64decode(value + "==")

    if len(raw_key) != 32:
        raise ValueError("Invalid WireGuard key length")

    return raw_key


@define(frozen=True)
class WireguardKey:
    keydata: bytes = field(converter=convert_wireguard_key)

    @classmethod
    def generate(cls) -> WireguardKey:
        """Generate a new private key"""
        random_data = token_bytes(32)
        # turn it into a proper curve25519 private key by fixing/clamping the value
        private_bytes = X25519PrivateKey.from_private_bytes(random_data).private_bytes()
        return cls(private_bytes)

    def public_key(self) -> WireguardKey:
        """Derive public key from private key"""
        public_bytes = X25519PrivateKey.from_private_bytes(self.keydata).public_key()
        return WireguardKey(public_bytes)

    def __bool__(self) -> bool:
        return int.from_bytes(self.keydata, "little") != 0

    def __str__(self) -> str:
        return standard_b64encode(self.keydata).decode("utf-8")

    @property
    def urlsafe(self) -> str:
        return urlsafe_b64encode(self.keydata).decode("utf-8").rstrip("=")


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
    def from_conf_file(cls, config_file: TextIO) -> WireguardConfig:
        # For now we can get away with the default ConfigParser because
        # the sinfonia-tier3 generated configs only have one peer.
        config = ConfigParser()
        config.read_file(config_file)

        private_key = WireguardKey(config["Interface"]["PrivateKey"])
        return cls.from_dict(private_key, config["Peer"])

    @classmethod
    def from_dict(
        cls, private_key: WireguardKey, config: dict[str, Any] | SectionProxy
    ) -> WireguardConfig:
        if "address" in config:
            addresses = [ip_interface(addr) for addr in config["address"]]
        else:
            addresses = []

        if "dns" in config:
            dns_servers = [
                ip_address(value) for value in config["dns"] if is_ipaddress(value)
            ]
            search_domains = [
                value for value in config["dns"] if not is_ipaddress(value)
            ]
        else:
            dns_servers = []
            search_domains = []

        public_key = WireguardKey(config["publicKey"])

        endpoint_addr, endpoint_port = config["endpoint"].rsplit(":")
        endpoint_host = (
            ip_address(endpoint_addr) if is_ipaddress(endpoint_addr) else endpoint_addr
        )
        endpoint_port = int(endpoint_port)

        allowedips_opt: list[str] | str = config["allowedIPs"]
        if isinstance(allowedips_opt, str):
            allowedips_opt = [address.strip() for address in allowedips_opt.split(",")]
        allowed_ips = [ip_interface(addr) for addr in allowedips_opt]

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

    def write_wireguard_conf(self, filename: str | os.PathLike[str]) -> None:
        """Create wireguard tunnel configuration"""
        allowed_ips = ", ".join(str(addr) for addr in self.allowed_ips)
        Path(filename).write_text(
            f"""\
[Interface]
PrivateKey = {self.private_key}

[Peer]
PublicKey = {self.public_key}
AllowedIPs = {allowed_ips}
Endpoint = {self.endpoint_host}:{self.endpoint_port}
"""
        )

    def dump_resolv_conf(self) -> str:
        name_servers = [f"nameserver {entry}" for entry in self.dns_servers]
        search_domains = [entry for entry in self.search_domains]

        resolvconf_config = "\n".join(name_servers)
        if search_domains:
            resolvconf_config += " ".join(["\nsearch"] + search_domains)
        resolvconf_config += "\noptions ndots:5"
        return resolvconf_config

    def write_resolv_conf(self, filename: str | os.PathLike[str]) -> None:
        Path(filename).write_text(self.dump_resolv_conf())
