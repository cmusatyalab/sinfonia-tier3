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
import os
import struct
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.reduction import recv_handle, send_handle
from pathlib import Path
from typing import Iterator

import importlib_resources
from pyroute2 import NDB
from typing_extensions import Literal
from wireguard_tools import WireguardConfig
from wireguard_tools.wireguard_device import WireguardUAPIDevice

from . import __version__

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
) -> Iterator[WireguardUAPIDevice]:
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

    with closing(WireguardUAPIDevice(uapi_path)) as device:
        yield device

    # do we even care to wait for the child to exit?
    # no we don't, it will terminate when the device or tmpdir are cleaned up


def create_wireguard_tunnel(
    ns_pid: int, interface: str, config: WireguardConfig, tmpdir: Path | None = None
) -> None:
    if tmpdir is None:
        tmpdir = Path()
    with fork_wireguard_go(ns_pid, interface, tmpdir) as device:
        # wg set <interface> private-key <...> peer <...> endpoint <...>
        #    persistent-keepalive <...> allowed-ips <...>
        device.set_config(config)


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

    config = WireguardConfig.from_wgconfig(args.config)
    create_wireguard_tunnel(args.ns_pid, args.interface, config, args.tmpdir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
