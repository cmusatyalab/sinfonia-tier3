#
# Sinfonia
#
# deploy helm charts to a cloudlet kubernetes cluster for edge-native applications
#
# Copyright (c) 2021-2023 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#

__version__ = "0.7.4"

from .cli import sinfonia_tier3

__all__ = ["sinfonia_tier3"]
