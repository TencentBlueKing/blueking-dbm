# -*- coding: utf-8 -*-
from types import SimpleNamespace

from backend.configuration.constants import DBType
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis import redis_util as redis_util_mod
from backend.flow.utils.redis.redis_util import get_latest_redis_package_by_version


def test_get_latest_redis_package_by_version_forwards_name_prefix(monkeypatch):
    captured = {}

    def fake_get_latest_package(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="tendisplus-2.7.4-rocksdb-v8.5.3.tgz")

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package", fake_get_latest_package)

    pkg = get_latest_redis_package_by_version("Tendisplus-2.7", name_prefix="tendisplus-2.7.4-rocksdb-v8.5.3")

    assert pkg.name == "tendisplus-2.7.4-rocksdb-v8.5.3.tgz"
    assert captured["version"] == "Tendisplus-2.7"
    assert captured["pkg_type"] == MediumEnum.TendisPlus
    assert captured["db_type"] == DBType.Redis
    assert captured["name_prefix"] == "tendisplus-2.7.4-rocksdb-v8.5.3"


def test_get_latest_redis_package_by_version_without_prefix_is_series_latest(monkeypatch):
    captured = {}

    def fake_get_latest_package(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(name="redis-6.2.14.tar.gz")

    monkeypatch.setattr(redis_util_mod.Package, "get_latest_package", fake_get_latest_package)

    get_latest_redis_package_by_version("Redis-6")

    assert captured["version"] == "Redis-6"
    assert captured["pkg_type"] == MediumEnum.Redis
    assert captured["name_prefix"] is None
