# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.configuration.constants import DBType
from backend.db_package.exceptions import PackageNotExistException
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis import redis_util as redis_util_mod
from backend.flow.utils.redis.redis_package_resolver import RedisUpgradeTarget
from backend.flow.utils.redis.redis_util import get_latest_redis_package_by_version, get_redis_package_v2_release
from backend.tests.mock_data.db_package.v2 import create_redis_package


@pytest.fixture
def clean_redis_packages(db):
    Package.objects.filter(db_type=DBType.Redis.value).delete()


@pytest.mark.usefixtures("clean_redis_packages")
class TestLatestRedisPackageByVersion:
    def test_upgrade_target_resolves_alpha_package(self):
        create_redis_package("redis-7.2.4.tar.gz", series="Redis-7", full_version="7.2.4.0.0.0", phase="release")
        alpha = create_redis_package("redis-7.2.5.tar.gz", series="Redis-7", full_version="7.2.5.0.0.0", phase="alpha")

        pkg = get_latest_redis_package_by_version(
            "Redis-7", upgrade_target=RedisUpgradeTarget(alpha.db_version_id, "redis-7.2.5")
        )

        assert pkg.id == alpha.id

    def test_regular_deploy_only_takes_release(self):
        create_redis_package("redis-7.2.4.tar.gz", series="Redis-7", full_version="7.2.4.0.0.0", phase="release")
        create_redis_package("redis-7.2.5.tar.gz", series="Redis-7", full_version="7.2.5.0.0.0", phase="alpha")

        assert get_latest_redis_package_by_version("Redis-7").name == "redis-7.2.4.tar.gz"


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
