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
import ctypes
import ctypes.util
import errno
import fcntl
import importlib_resources
import os
import socket
import struct
import subprocess
import sys
import time
from contextlib import contextmanager
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.reduction import recv_handle, send_handle
from pathlib import Path
from typing import Iterator, Literal

from pyroute2 import NDB

from . import __version__
from .wireguard import WireguardConfig

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def setns(target_ns_pid: int, ns_type: Literal["user", "net"]) -> None:
    ns_path = Path("/proc", str(target_ns_pid), "ns", ns_type)
    with ns_path.open() as nsfd:
        if _libc.setns(nsfd.fileno(), 0) == -1:
            e = ctypes.get_errno()
            raise OSError(e, errno.errorcode[e])


def _create_tun_child(target_ns_pid: int, tundev_name: str, writer: Connection) -> None:
    # join target user and network namespaces
    setns(target_ns_pid, "user")
    setns(target_ns_pid, "net")

    # create tuntap device
    tundev = os.open("/dev/net/tun", os.O_RDWR)
    assert tundev != -1

    TUNSETIFF = 0x400454CA
    IFF_TUN = 0x0001

    ifreq = struct.pack("16sH22x", tundev_name.encode(), IFF_TUN)
    fcntl.ioctl(tundev, TUNSETIFF, ifreq)

    # pass tunnel device handle back to parent
    send_handle(writer, tundev, None)

    # set interface mtu
    with NDB() as ndb:
        ndb.interfaces[tundev_name].set("mtu", 1420).commit()


def create_tun_in_netns(target_ns_pid: int, tundev_name: str) -> int:
    reader, writer = Pipe()
    p = Process(target=_create_tun_child, args=(target_ns_pid, tundev_name, writer))
    p.start()
    tundev = recv_handle(reader)
    p.join()
    return tundev


@contextmanager
def fork_wireguard_go(
    ns_pid: int, interface: str, tmpdir: Path
) -> Iterator[socket.socket]:
    tundev = create_tun_in_netns(ns_pid, interface)

    wireguard_go = importlib_resources.files("sinfonia_tier3").joinpath("wireguard-go")

    try:
        subprocess.Popen(
            [wireguard_go, interface],
            env=dict(
                WG_PROCESS_FOREGROUND="1",
                WG_TUN_FD=str(tundev),
                # LOG_LEVEL="debug",
            ),
            pass_fds=(tundev,),
            cwd=tmpdir,
        )
    except FileNotFoundError:
        os.close(tundev)
        raise

    # wait for uapi socket
    uapi_path = Path(tmpdir, interface).with_suffix(".sock")
    while not uapi_path.exists():
        time.sleep(0.1)

    # connect to uapi socket
    uapi_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    uapi_sock.connect(str(uapi_path.resolve()))

    yield uapi_sock
    uapi_sock.close()

    # do we even care to wait for the child to exit?
    # no we don't, it will terminate when the device or tmpdir are cleaned up


def create_wireguard_tunnel(
    ns_pid: int, interface: str, wg_config: WireguardConfig, tmpdir: Path = Path()
) -> None:
    with fork_wireguard_go(ns_pid, interface, tmpdir) as uapi_sock:
        # wg set <interface> private-key <...> peer <...> endpoint <...>
        #    persistent-keepalive <...> allowed-ips <...>
        config = [
            "set=1",
            f"private_key={wg_config.private_key.hex()}",
            "replace_peers=true",
            f"public_key={wg_config.public_key.hex()}",
            f"endpoint={wg_config.endpoint_host}:{wg_config.endpoint_port}",
            "persistent_keepalive_interval=30",
            "replace_allowed_ips=true",
        ]
        for address in wg_config.allowed_ips:
            config.append(f"allowed_ip={address}")
        config.append("")
        uapi_sock.sendall("\n".join(config).encode())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--tmpdir", type=Path, default=".")
    parser.add_argument("ns_pid", type=int)
    parser.add_argument("interface")
    parser.add_argument("config", metavar="wireguard.conf", type=argparse.FileType("r"))
    args = parser.parse_args()

    wg_config = WireguardConfig.from_conf_file(args.config)
    create_wireguard_tunnel(args.ns_pid, args.interface, wg_config, args.tmpdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
