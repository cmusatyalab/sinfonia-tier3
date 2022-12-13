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

import os
from pathlib import Path
from uuid import UUID

import yaml
from attrs import define
from wireguard_tools import WireguardKey
from xdg import xdg_cache_home


@define
class KeyCacheEntry:
    private_key: WireguardKey
    public_key: WireguardKey

    @classmethod
    def new(cls) -> KeyCacheEntry:
        private_key = WireguardKey.generate()
        public_key = private_key.public_key()
        return cls(private_key, public_key)

    @classmethod
    def from_yaml(cls, text: str) -> KeyCacheEntry:
        # raises ValueError when input is incorrectly formatted
        try:
            keys = yaml.safe_load(text)
            return cls(
                WireguardKey(keys["private_key"]), WireguardKey(keys["public_key"])
            )
        except (TypeError, KeyError, ValueError) as exc:
            raise ValueError("Unexpected cache file format") from exc

    @classmethod
    def from_file(cls, cache_file: Path) -> KeyCacheEntry:
        # raises FileNotFoundError when file doesn't exist
        # raises ValueError when input is incorrectly formatted
        text = cache_file.read_text()
        return cls.from_yaml(text)

    def to_dict(self) -> dict[str, str]:
        # return attrs.asdict(self, value_serializer=lambda _inst, _fld, val: str(val))
        return dict(public_key=str(self.public_key), private_key=str(self.private_key))

    def to_file(self, cache_file: Path) -> None:
        cache_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with cache_file.open("w") as fh:
            os.fchmod(fh.fileno(), 0o600)
            return yaml.dump(self.to_dict(), fh)

    @classmethod
    def load(cls, application_uuid: UUID) -> KeyCacheEntry:
        """Return a new public/private for the application

        Reuse a cached copy from ~/.cache/sinfonia/<application-uuid> if it exists.
        """
        cache_file = xdg_cache_home() / "sinfonia" / str(application_uuid)
        try:
            return cls.from_file(cache_file)
        except ValueError:
            # unexpected cache content, discard and create a new one
            cache_file.unlink()
        except FileNotFoundError:
            pass

        cache_entry = cls.new()
        cache_entry.to_file(cache_file)
        return cache_entry
