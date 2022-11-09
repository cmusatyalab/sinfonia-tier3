# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

from uuid import UUID

import pytest
from yarl import URL

from sinfonia_tier3.cli import parse_args

pytestmark = pytest.mark.filterwarnings(
    "ignore:.*Validator.iter_errors.*:DeprecationWarning"
)

NULL_UUID = "00000000-0000-0000-0000-000000000000"

SUCCESSFUL_DEPLOYMENT = [
    {
        "DeploymentName": "testing-test",
        "UUID": NULL_UUID,
        "ApplicationKey": "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=",
        "Status": "Deployed",
        "Created": "2050-12-31T00:00:00Z",
        "TunnelConfig": {
            "publicKey": "DnLEmfJzVoCRJYXzdSXIhTqnjygnhh6O+I3ErMS6OUg=",
            "allowedIPs": ["10.0.0.1/24"],
            "endpoint": "127.0.0.1:51820",
            "address": ["10.0.0.2/32"],
            "dns": ["10.0.0.1"],
        },
    }
]


def test_parser() -> None:
    with pytest.raises(SystemExit):
        parse_args([])

    args = parse_args(["--config-debug", "http://localhost:8080", NULL_UUID, "true"])
    print(args)
    assert args.config_debug is True
    assert args.tier1_url == URL("http://localhost:8080")
    assert args.application_uuid == UUID(NULL_UUID)
    assert args.application == ["true"]


# # switch back to Click so we can benefit from the better test harness?
#
# from pathlib import Path
# from click.testing import CliRunner
# from requests_mock import ANY as requests_mock_ANY
#
# def test_app(tmp_path, requests_mock, mock_generate_keypair):
#     # mock the tier2 server
#     requests_mock.post(
#         requests_mock_ANY,
#         json=SUCCESSFUL_DEPLOYMENT,
#         headers={"Content-Type": "application/json"},
#     )
#
#     runner = CliRunner()
#     with runner.isolated_filesystem():
#         cache_dir = Path("cache").resolve()
#         args = [
#             "--config-debug",
#             "http://localhost:8080",
#             "00000000-0000-0000-0000-000000000000",
#             "true",
#         ]
#
#         result = runner.invoke(app, args, env={"XDG_CACHE_HOME": str(cache_dir)})
#         assert result.exit_code == 0
#
#         assert Path(
#             "cache", "sinfonia", "00000000-0000-0000-0000-000000000000"
#         ).exists()
#         assert Path("wg-testingtest.conf").exists()
