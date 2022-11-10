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

from typing import Any
from uuid import UUID

import importlib_resources
import requests
import yaml
from attrs import define
from openapi_core import create_spec
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from openapi_core.validation.response.validators import ResponseValidator
from yarl import URL

from .key_cache import KeyCacheEntry
from .wireguard import WireguardConfig, WireguardKey


@define
class CloudletDeployment:
    uuid: UUID
    application_key: WireguardKey
    status: str
    tunnel_config: WireguardConfig
    deployment_name: str
    created: str | None

    @classmethod
    def from_dict(
        cls, private_key: WireguardKey, resp: dict[str, Any]
    ) -> CloudletDeployment:
        return cls(
            resp["UUID"],
            resp["ApplicationKey"],
            resp["Status"],
            WireguardConfig.from_dict(private_key, resp["TunnelConfig"]),
            resp.get("DeploymentName", ""),
            resp.get("Created"),
        )


class WireguardKeyFormatter:
    def validate(self, value: str) -> bool:
        try:
            WireguardKey(value)
            return True
        except ValueError:
            return False

    def unmarshal(self, value: str) -> WireguardKey:
        return WireguardKey(value)


def sinfonia_deploy(
    tier1_url: URL, application_uuid: UUID, debug: bool = False, zeroconf: bool = False
) -> list[CloudletDeployment]:
    """Request a backend (re)deployment from the orchestrator"""
    deploy_base = tier1_url
    if zeroconf:
        raise NotImplementedError("Zeroconf functionality is still unfinished")
        # - perform MDNS lookup for "cloudlet._sinfonia._tcp.local."
        # override tier1_url and pass original tier1_url as a request header

    deployment_keys = KeyCacheEntry.load(application_uuid)
    deployment_url = (
        deploy_base
        / "api/v1/deploy"
        / str(application_uuid)
        / deployment_keys.public_key.urlsafe
    )

    if debug:
        print("\ndeployment_url:", deployment_url)

    # fire off deployment request
    response = requests.post(str(deployment_url))
    response.raise_for_status()

    # load openapi specification to validate the response
    spec_text = (
        importlib_resources.files("sinfonia_tier3.openapi")
        .joinpath("sinfonia_tier2.yaml")
        .read_text()
    )
    spec_dict = yaml.safe_load(spec_text)
    spec = create_spec(spec_dict)

    # create request/response wrappers for validation
    openapi_request = RequestsOpenAPIRequest(response.request)
    openapi_response = RequestsOpenAPIResponse(response)

    # validate the response
    validator = ResponseValidator(
        spec, custom_formatters={"wireguard_public_key": WireguardKeyFormatter()}
    )
    result = validator.validate(openapi_request, openapi_response)
    result.raise_for_errors()

    return [
        CloudletDeployment.from_dict(deployment_keys.private_key, deployment)
        for deployment in result.data
    ]
