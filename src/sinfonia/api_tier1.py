#
# Sinfonia
#
# proxy requests to a nearby cloudlet
#
# Copyright (c) 2022 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#

import logging
from itertools import chain, filterfalse, islice, zip_longest

from connexion import NoContent
from connexion.exceptions import ProblemException
from flask import current_app, request
from flask.views import MethodView

from . import cloudlets
from .client_info import ClientInfo
from .deployment_score import DeploymentScore

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# don't try to deploy to more than MAX_RESULTS cloudlets at a time
MAX_RESULTS = 3


class DeployView(MethodView):
    def post(self, uuid, application_key, results=1):
        # set number of returned results between 1 and MAX_RESULTS
        max_results = max(1, min(results, MAX_RESULTS))

        try:
            requested = DeploymentScore.from_uuid(uuid)
            client_info = ClientInfo.from_request(application_key)
        except ValueError:
            raise ProblemException(400, "Bad Request", "Incorrectly formatted request")

        available = list(current_app.config["CLOUDLETS"].values())
        candidates = islice(
            cloudlets.find(client_info, requested, available), max_results
        )

        # fire off deployment requests
        requests = [
            cloudlet.deploy_async(requested.uuid, client_info)
            for cloudlet in candidates
        ]

        # gather the results,
        # - interleave results from cloudlets in case any returned more than requested.
        # - recombine into a single list, drop failed results, and limit to max_results.
        results = list(
            islice(
                filterfalse(
                    lambda r: r is None,
                    chain(*zip_longest(*(request.result() for request in requests))),
                ),
                max_results,
            )
        )

        # all requests failed?
        if not results:
            raise ProblemException(500, "Error", "Something went wrong")

        return results

    def get(self, uuid, application_key):
        raise ProblemException(500, "Error", "Not implemented")


class CloudletsView(MethodView):
    def post(self):
        body = request.json
        if not isinstance(body, dict) or "uuid" not in body:
            return "Bad Request, missing UUID", 400

        cloudlet = cloudlets.Cloudlet.new_from_api(body)
        CLOUDLETS = current_app.config["CLOUDLETS"]
        CLOUDLETS[cloudlet.uuid] = cloudlet
        return NoContent, 204

    def search(self):
        CLOUDLETS = current_app.config["CLOUDLETS"]
        return [cloudlet.summary() for cloudlet in CLOUDLETS.values()]
