# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.configuration.constants import DBType
from backend.db_package.exceptions import PackageNotExistException
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis import redis_util as redis_util_mod
from backend.flow.utils.redis.redis_util import get_latest_redis_package_by_version, get_redis_package_v2_release


def test_get_latest_redis_package_by_version_forwards_name_prefix(monkeypatch):
    captured = {}

    def fake_get_latest_package_v2_release(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="tendisplus-2.7.4-rocksdb-v8.5.3.tgz")

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package_v2_release", fake_get_latest_package_v2_release)

    pkg = get_latest_redis_package_by_version("Tendisplus-2.7", name_prefix="tendisplus-2.7.4-rocksdb-v8.5.3")

    assert pkg.name == "tendisplus-2.7.4-rocksdb-v8.5.3.tgz"
    assert captured["series"] == "Tendisplus-2.7"
    assert captured["pkg_type"] == MediumEnum.TendisPlus
    assert captured["db_type"] == DBType.Redis
    assert captured["name_prefix"] == "tendisplus-2.7.4-rocksdb-v8.5.3"


def test_get_latest_redis_package_by_version_maps_db_version_to_series(monkeypatch):
    captured = {}

    def fake_get_latest_package_v2_release(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="redis-6.2.14.tar.gz")

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package_v2_release", fake_get_latest_package_v2_release)

    get_latest_redis_package_by_version("Redis-6")

    assert captured["series"] == "Redis-6"
    assert captured["pkg_type"] == MediumEnum.Redis
    assert captured["name_prefix"] is None


def test_get_latest_redis_package_by_version_raises_when_missing(monkeypatch):
    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package_v2_release", lambda **kwargs: None)
    monkeypatch.setattr(
        redis_util_mod.Package,
        "get_latest_package",
        MagicMock(side_effect=PackageNotExistException(version="Redis-7", pkg_type="redis", db_type="redis")),
    )

    with pytest.raises(PackageNotExistException):
        get_latest_redis_package_by_version("Redis-7")


def test_get_redis_package_v2_release_falls_back_to_v1(monkeypatch):
    """存量环境未补挂 db_version 时，V2 查不到需回退 V1 查询。"""
    sentinel = SimpleNamespace(name="legacy-dbtools.tar.gz")
    captured = {}

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package_v2_release", lambda **kwargs: None)

    def fake_get_latest_package(**kwargs):
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package", fake_get_latest_package)

    pkg = get_redis_package_v2_release(pkg_type=MediumEnum.RedisTools)

    assert pkg is sentinel
    assert captured["version"] == MediumEnum.Latest.value
    assert captured["pkg_type"] == MediumEnum.RedisTools
    assert captured["db_type"] == DBType.Redis
