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
import os
import subprocess
import sys
from ipaddress import IPv4Interface, IPv6Interface, ip_interface
from pathlib import Path
from shutil import which

from pyroute2 import NDB

from . import __version__

#
# Things we do in the network namespace
#
# - Bind mount /etc/resolv.conf
# - Wait for wireguard interface to appear in our namespace.
# - Configure ip addresses on the wireguard interface.
# - Bring the wireguard interface up.
# - Add default route through the wireguard interface.
# - Launch application.
#


def bind_mount(resolvconf: Path) -> None:
    mount = which("mount")
    assert mount is not None
    subprocess.run(
        [mount, "--bind", str(resolvconf.resolve()), "/etc/resolv.conf"], check=True
    )


def finish_network_config(
    interface: str, addresses: list[IPv4Interface | IPv6Interface]
) -> None:
    with NDB() as ndb:
        with ndb.interfaces.wait(ifname=interface) as wg:
            # ip link set <interface> up
            wg.set(state="up")

            # ip addr add <address> dev <interface>
            for address in addresses:
                wg.add_ip(str(address))

        with ndb.interfaces[interface] as wg:
            # ip route add default dev <interface>
            ndb.routes.create(dst="default", oif=wg["index"]).commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--resolvconf",
        type=Path,
    )
    parser.add_argument(
        "--address",
        type=ip_interface,
        action="append",
    )
    parser.add_argument(
        "interface",
    )
    parser.add_argument(
        "application",
        nargs="+",
    )
    args = parser.parse_args()

    if args.resolvconf is not None:
        bind_mount(args.resolvconf)

    finish_network_config(args.interface, args.address)

    # Run application
    env = os.environ.copy()
    env["PS1"] = "sinfonia$ "

    # subprocess.run(args.application, env=env, check=True)
    # return 0

    try:
        os.execve(args.application[0], args.application, env=env)
    except Exception:
        print(f"executing {args.application} failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
