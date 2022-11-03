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

import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory

import randomname

from .wireguard import WireguardConfig

ip = which("ip")
mkdir = which("mkdir")
rm = which("rm")
rmdir = which("rmdir")
sudo = which("sudo")
tee = which("tee")
wg = which("wg") or which("echo")


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


@contextmanager
def network_namespace(namespace: str, resolv_conf: Path):
    assert ip is not None
    assert mkdir is not None
    assert rm is not None
    assert rmdir is not None
    assert sudo is not None
    assert tee is not None

    try:
        # ip netns wants the resolv.conf replacement in a specific location
        resolvconf = Path("/etc", "netns", namespace, "resolv.conf")
        resolvconf_config = resolv_conf.read_text()

        subprocess.run([sudo, mkdir, "-p", str(resolvconf.parent)], check=True)
        subprocess.run(
            [sudo, tee, str(resolvconf)],
            input=resolvconf_config,
            stdout=subprocess.DEVNULL,
            encoding="utf-8",
            check=True,
        )

        # now we can create the network namespace
        subprocess.run([sudo, ip, "netns", "add", namespace], check=True)
        yield [sudo, "-E", ip, "netns", "exec", namespace]

    finally:
        subprocess.run([sudo, ip, "netns", "delete", namespace])
        subprocess.run([sudo, rm, "-f", str(resolvconf)])
        subprocess.run([sudo, rmdir, str(resolvconf.parent)])


def sinfonia_runapp(
    deployment_name: str,
    tunnel_config: WireguardConfig,
    application: list[str],
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

        assert ip is not None
        assert sudo is not None
        assert wg is not None

        NS = unique_namespace_name(deployment_name)
        WG = f"wg-{NS}"[:15]

        with network_namespace(NS, resolv_conf) as netns_exec:
            uid, gid = os.getuid(), os.getgid()

            subprocess.run(
                [sudo, ip, "link", "add", WG, "type", "wireguard"], check=True
            )
            subprocess.run([sudo, ip, "link", "set", WG, "netns", NS], check=True)

            # ip_addr_add = "\n".join(f"ip addr add {address] dev {WG}"
            #                         for address in tunnel_config.addresses)
            """
            set -e
            wg setconf {WG} {tmpdir}/wg.conf
            {ip_addr_add}
            ip link set {WG} up
            ip route add default dev {WG}
            export PS1="sinfonia$ "
            sudo -E -u #{uid} -g #{gid} {*application}
            """

            subprocess.run(
                netns_exec + [wg, "setconf", WG, f"{tmpdir}/wg.conf"], check=True
            )
            for address in tunnel_config.addresses:
                subprocess.run(
                    netns_exec + [ip, "addr", "add", str(address), "dev", WG],
                    check=True,
                )
            subprocess.run(netns_exec + [ip, "link", "set", WG, "up"], check=True)
            subprocess.run(
                netns_exec + [ip, "route", "add", "default", "dev", WG], check=True
            )

            env = os.environ.copy()
            env["PS1"] = "sinfonia$ "
            subprocess.run(
                netns_exec
                + ["sudo", "-E", "-u", f"#{uid}", "-g", f"#{gid}"]
                + application,
                env=env,
            )
    return 0
