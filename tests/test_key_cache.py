# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

from pathlib import Path
from uuid import UUID

from _pytest.monkeypatch import MonkeyPatch

from sinfonia_tier3.key_cache import KeyCacheEntry


def test_cached_keys(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """test that the key for a uuid persists"""
    cache_dir = Path(tmp_path, "cache").resolve()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    uuid = UUID("00000000-0000-0000-0000-000000000000")

    generated = KeyCacheEntry.load(uuid)
    cached = KeyCacheEntry.load(uuid)
    assert generated.private_key == cached.private_key
    assert generated.public_key == cached.public_key
    assert generated == cached

    cl_cache_dir = cache_dir / "sinfonia"
    assert (cl_cache_dir / str(uuid)).exists()


def test_unique_keys(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """validate that different uuids return different keys"""
    cache_dir = Path(tmp_path, "cache").resolve()
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_dir))

    uuid0 = UUID("00000000-0000-0000-0000-000000000000")
    uuid1 = UUID("00000000-0000-0000-0000-000000000001")

    generated = KeyCacheEntry.load(uuid0)
    cached = KeyCacheEntry.load(uuid1)
    assert generated != cached
    assert generated.private_key != cached.private_key
    assert generated.public_key != cached.public_key

    cl_cache_dir = cache_dir / "sinfonia"
    assert (cl_cache_dir / str(uuid0)).exists()
    assert (cl_cache_dir / str(uuid1)).exists()
