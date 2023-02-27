#
# Sinfonia
#
# deploy helm charts to a cloudlet kubernetes cluster for edge-native applications
#
# Copyright (c) 2022-2023 Carnegie Mellon University
#
# SPDX-License-Identifier: MIT
#

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
