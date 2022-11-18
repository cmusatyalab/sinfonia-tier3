#
# Sinfonia
#
# deploy helm charts to a cloudlet kubernetes cluster for edge-native applications
#
# Copyright (c) 2021-2022 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#

from __future__ import annotations

import subprocess
import sys
from itertools import chain
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Sequence

import randomname

from .wireguard import WireguardConfig


def unique_namespace_name(name: str) -> str:
    """Returns a name with only ascii lowercase letters.

    Deriving it from the deployment name helps during development to match the
    deployed kubenetes environment with the local namespace, but it is not
    functionally required.
    """
    # str.translate is probably faster, but we only do this once...
    return "".join(c for c in name.lower() if c.islower()) or randomname.get_name(
        sep=""
    )


def sinfonia_runapp(
    deployment_name: str,
    tunnel_config: WireguardConfig,
    application: Sequence[str],
    config_debug: bool = False,
) -> int:
    """Run applicaiton in an isolated network namespace with wireguard tunnel"""
    with TemporaryDirectory() as temporary_directory:
        if config_debug:
            temporary_directory = "."
        tmpdir = Path(temporary_directory)

        wireguard_conf = tmpdir / "wg.conf"
        tunnel_config.write_wireguard_conf(wireguard_conf)

        resolv_conf = tmpdir / "resolv.conf"
        tunnel_config.write_resolv_conf(resolv_conf)

        if config_debug:
            return 0

        sudo = which("sudo")
        unshare = which("unshare")
        assert sudo is not None
        assert unshare is not None

        NS = unique_namespace_name(deployment_name)
        WG = f"wg-{NS}"[:15]

        # Running two processes pretty much in parallel here, the first one
        # creates a new network namespace and then waits for the wireguard
        # interface.
        # The second process runs as root and creates and configures the
        # wireguard interface and attaches it to the new network namespace.
        with subprocess.Popen(
            [
                unshare,
                "--user",
                "--map-root-user",
                "--net",
                "--mount",
                "--",
                sys.executable,
                "-m",
                "sinfonia_tier3.netns_helper",
                "--resolvconf",
                str(resolv_conf.resolve()),
            ]
            + list(
                chain.from_iterable(
                    ("--address", str(address)) for address in tunnel_config.addresses
                )
            )
            + [WG]
            + list(application)
        ) as netns_proc:

            # create, configure and attach WireGuard interface
            subprocess.run(
                [
                    sudo,
                    sys.executable,
                    "-m",
                    "sinfonia_tier3.root_helper",
                    WG,
                    str(netns_proc.pid),
                    str(wireguard_conf.resolve()),
                ],
                check=True,
            )
            # leaving the context will wait for the application to exit
    return 0
