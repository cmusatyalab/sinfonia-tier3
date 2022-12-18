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

from pyroute2 import IPRoute
from wireguard_tools import WireguardConfig, WireguardDevice

from . import __version__

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
        device = WireguardDevice.get(interface)
        device.set_config(config)

        # ip set dev <interface> netns <netns>
        with network_namespace(netns) as net_ns_fd:
            ipr.link("set", index=iface["index"], net_ns_fd=net_ns_fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("netns")
    parser.add_argument("interface")
    parser.add_argument(
        "wgconfig",
        metavar="wireguard.conf",
        type=argparse.FileType("r"),
        default=sys.stdin,
    )
    args = parser.parse_args()

    wgconfig = WireguardConfig.from_wgconfig(args.wgconfig)

    create_config_attach(args.interface, wgconfig, args.netns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
