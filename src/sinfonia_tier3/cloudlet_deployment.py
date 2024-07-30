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

from typing import Any, cast
from uuid import UUID

import importlib_resources
import requests
import yaml
from attrs import define
from openapi_core import Spec, unmarshal_response
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from wireguard_tools import WireguardConfig, WireguardKey
from yarl import URL

from .key_cache import KeyCacheEntry


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
        config = resp["TunnelConfig"]

        wgconfig = WireguardConfig.from_dict(
            dict(
                private_key=private_key,
                addresses=config["address"],
                dns=config["dns"],
                peers=[
                    dict(
                        public_key=config["publicKey"],
                        endpoint=config["endpoint"],
                        allowed_ips=config["allowedIPs"],
                        persistent_keepalive=30,
                    )
                ],
            )
        )

        return cls(
            resp["UUID"],
            resp["ApplicationKey"],
            resp["Status"],
            wgconfig,
            resp.get("DeploymentName", ""),
            resp.get("Created"),
        )


def validate_wireguard_key(value: str) -> bool:
    try:
        WireguardKey(value)
        return True
    except ValueError:
        return False


def unmarshal_wireguard_key(value: str) -> WireguardKey:
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
    spec = Spec.create(spec_dict)

    # create request/response wrappers for validation
    openapi_request = RequestsOpenAPIRequest(response.request)
    openapi_response = RequestsOpenAPIResponse(response)

    # validate and unpack the response
    extra_validators = dict(wireguard_public_key=validate_wireguard_key)
    extra_unmarshallers = dict(wireguard_public_key=unmarshal_wireguard_key)
    result = unmarshal_response(
        openapi_request,
        openapi_response,
        spec=spec,
        extra_format_validators=extra_validators,
        extra_format_unmarshallers=extra_unmarshallers,
    )

    # validation should have failed if this is None, I think
    assert result.data is not None
    return [
        CloudletDeployment.from_dict(deployment_keys.private_key, deployment)
        for deployment in cast(Any, result.data)
    ]
