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

import socket
import time
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceStateChange, ServiceInfo


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

################ 
# I used zeroconf library: https://github.com/python-zeroconf/python-zeroconf/blob/master/README.rst
# but can also do with Avahi-browse if you want (I know you mentioned this 
# it's a very simple change) 
# ###############
def discover_local_tier2_service(
    service_type: str = "cloudlet._sinfonia._tcp.local.",
    timeout: float = 10.0
) -> URL | None:
    """
    Discover a local Tier2 endpoint via mDNS for the specified service type.
    Returns the first discovered URL (http://host:port) or None if none found.
    """

    # Store discovered addresses here
    discovered_urls: list[URL] = []

    class CloudletListener:
        # A listener to handle newly added services.
        def add_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                # Use IP from TXT records if available, otherwise use the address from mDNS
                if b'ip' in info.properties:
                    host = info.properties[b'ip'].decode('utf-8')
                elif info.addresses:
                    host = socket.inet_ntoa(info.addresses[0])
                else:
                    print("No host address found in service info.")
                    return

                url = URL.build(scheme="http", host=host)
                discovered_urls.append(url)
        
        def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str) -> None:
            # Handle service removal if needed
            print(f"Service {name} removed")
        def update_service(
            self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        ) -> None:
            # Handle service update if needed
            print(f"Service {name} updated")

    zc = Zeroconf()
    listener = CloudletListener()
    browser = ServiceBrowser(zc, service_type, listener=listener)

    # Wait briefly to see if we discover anything
    # In a future implementation, we could optimize to concurrently discover tier 1 compute
    time.sleep(timeout)


    zc.close()

    if discovered_urls:
        return discovered_urls[0]
    return None


def sinfonia_deploy(
    tier1_url: URL, application_uuid: UUID, debug: bool = False, zeroconf: bool = False
) -> list[CloudletDeployment]:
    """Request a backend (re)deployment from the orchestrator"""
    deploy_base = tier1_url
    extra_headers = {}

    if zeroconf:
        # - perform MDNS lookup for "cloudlet._sinfonia._tcp.local."
        # override tier1_url and pass original tier1_url as a request header
        ## FOR ANNOUNCING WE WANT IT TO BE AUTOMATIC
        discovered_url = discover_local_tier2_service()
        if discovered_url is not None:
            print(f"[zeroconf] Discovered local Tier2 at {discovered_url}")
            # Override deploy_base if found
            deploy_base = discovered_url
            # Also pass original Tier1 URL along
            extra_headers["X-Sinfonia-Original-Tier1"] = str(tier1_url)
        else:
            print("[zeroconf] No local Tier2 discovered; continuing with provided tier1_url")

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
