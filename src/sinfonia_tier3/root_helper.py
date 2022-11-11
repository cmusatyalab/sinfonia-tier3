#
# Sinfonia
#
# deploy helm charts to a cloudlet kubernetes cluster for edge-native applications
#
# Copyright (c) 2022 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#

from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from pyroute2 import IPRoute, WireGuard

from . import __version__
from .wireguard import WireguardConfig

#
# Things we have to do as root
#
# - Create wireguard interface in the primary (routed) namespace.
# - Set wireguard tunnel/peer configuration.
# - Attach wireguard interface to network namespace.
#


@contextmanager
def network_namespace(netns: str) -> Iterator[str | int]:
    try:
        pid = int(netns)
        with Path("/proc/", str(pid), "ns", "net").open("r") as ns:
            yield ns.fileno()
    except ValueError:
        yield netns


def create_config_attach(interface: str, config: WireguardConfig, netns: str) -> None:
    with IPRoute() as ipr:
        # ip link add <interface> type wireguard
        ipr.link("add", ifname=interface, kind="wireguard")

        # wait for interface creation
        (iface,) = ipr.poll(ipr.link, "dump", timeout=5, ifname=interface)

        # wg set <interface> private-key <...> peer <...> endpoint <...>
        #    persistent-keepalive <...> allowed-ips <...>
        wg = WireGuard()
        wg.set(
            interface,
            private_key=str(config.private_key),
            peer=dict(
                public_key=str(config.public_key),
                endpoint_addr=str(config.endpoint_host),
                endpoint_port=config.endpoint_port,
                allowed_ips=[str(address) for address in config.allowed_ips],
                persistent_keepalive=30,
            ),
        )

        # ip set dev <interface> netns <netns>
        with network_namespace(netns) as net_ns_fd:
            ipr.link("set", index=iface["index"], net_ns_fd=net_ns_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("interface")
    parser.add_argument("netns")
    parser.add_argument(
        "config",
        metavar="wireguard.conf",
        type=argparse.FileType("r"),
        default=sys.stdin,
    )
    args = parser.parse_args()

    wg_config = WireguardConfig.from_conf_file(args.config)

    create_config_attach(args.interface, wg_config, args.netns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
