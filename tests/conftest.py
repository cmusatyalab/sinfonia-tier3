# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

import pytest
import wgconfig.wgexec


@pytest.fixture
def mock_generate_keypair(monkeypatch):
    """wgconfig.wgexec.generate_keypairs mocked so we don't `wg` binary"""
    keypairs = [
        (
            "mHJFze/rYugSqH5y5jYgJmJA+Xn+8GYankWDJx69Ymo=",
            "LaMgyk/jPiVRX1XFhBbbW7RlZQO976ZOcnpjlRIeSCc=",
        ),
        (
            "AB9y9TPUpZRYXdA/VEMmY1vjXN78xnG3W5u0kh+7H3c=",
            "P8+7aAk2FsUYkhX4CvJfFWWThus25+A9AeoIRdeEumU=",
        ),
        (
            "wDKetfz9LiQq1hu4E8x0woPmwFp/Oc6Zt69gglQHsV8=",
            "nyJ86rdfI7nxVk7CBoDV42e6gh6E2EzAbI/dVTGbdjs=",
        ),
    ]

    def generate_keypair():
        return keypairs.pop()

    monkeypatch.setattr(wgconfig.wgexec, "generate_keypair", generate_keypair)


@pytest.fixture(scope="session")
def example_wgkey():
    return "YpdTsMtb/QCdYKzHlzKkLcLzEbdTK0vP4ILmdcIvnhc="
