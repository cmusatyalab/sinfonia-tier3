# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest
import yaml
from openapi_core import Spec


class TestOpenApiSpecs:
    @pytest.fixture(scope="class")
    def specification_dir(self) -> Path:
        return Path(__file__).parents[1] / "src" / "sinfonia_tier3" / "openapi"

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_tier2_spec(self, specification_dir: Path) -> None:
        spec_yaml = specification_dir.joinpath("sinfonia_tier2.yaml").read_text()
        spec_dict = yaml.safe_load(spec_yaml)
        spec = Spec.create(spec_dict)
        assert spec is not None
