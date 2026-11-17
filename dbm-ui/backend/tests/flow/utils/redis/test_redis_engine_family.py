# -*- coding: utf-8 -*-
import re
from types import SimpleNamespace

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis import redis_proxy_util as proxy_mod
from backend.flow.utils.redis.redis_package_resolver import strip_pkg_suffix
from backend.flow.utils.redis.redis_util import get_redis_engine_family, is_cross_engine_version_change
from backend.tests.mock_data.db_package.v2 import create_redis_package


def _full_version_of(name: str) -> str:
    segments = (re.findall(r"\d+", name) + ["0"] * 6)[:6]
    return ".".join(segments)


def make_pkg(name, *args, phase=VersionPhase.RELEASE.value, full_version=None, **kwargs):
    """默认登记为 V2 release 版本; phase=None 时为未关联 V2 的介质"""
    if phase and full_version is None:
        full_version = _full_version_of(name)
    kwargs.setdefault("version_name", strip_pkg_suffix(name))
    return create_redis_package(name, *args, full_version=full_version, phase=phase, **kwargs)


def _names(items):
    return [item["version_name"] for item in items]


def test_get_redis_engine_family_by_prefix():
    assert get_redis_engine_family("valkey-8.0.1") == "valkey"
    assert get_redis_engine_family("Valkey-8") == "valkey"
    assert get_redis_engine_family("VALKEY-9.0.0.tar.gz") == "valkey"
    assert get_redis_engine_family("redis-6.2.14") == "redis"
    assert get_redis_engine_family("Redis-7") == "redis"
    assert get_redis_engine_family("tendisplus-2.8.0") == "redis"
    assert get_redis_engine_family("") == "redis"
    assert get_redis_engine_family(None) == "redis"


def test_is_cross_engine_version_change():
    assert is_cross_engine_version_change("redis-6.2.14", "valkey-8.0.1")
    assert is_cross_engine_version_change("valkey-8.0.1", "redis-7.2.4")
    assert not is_cross_engine_version_change("redis-6.2.14", "redis-7.2.4")
    assert not is_cross_engine_version_change("valkey-8.0.1", "Valkey-9")


@pytest.fixture
def clean_redis_packages(db):
    Package.objects.filter(db_type=DBType.Redis.value).delete()


def _stub_cluster(
    monkeypatch,
    cluster_type=ClusterType.TendisPredixyRedisCluster,
    online_version="",
    major="Redis-6",
    proxy_versions=(),
):
    monkeypatch.setattr(
        proxy_mod.Cluster.objects,
        "get",
        lambda **kwargs: SimpleNamespace(id=1, cluster_type=cluster_type, major_version=major),
    )
    monkeypatch.setattr(proxy_mod, "get_cluster_redis_version", lambda *args, **kwargs: online_version)
    calls = []

    def proxy_versions_of(cluster_id, ips=None):
        calls.append(ips)
        return list(proxy_versions)

    monkeypatch.setattr(proxy_mod, "get_cluster_proxy_version", proxy_versions_of)
    return calls


@pytest.mark.usefixtures("clean_redis_packages")
class TestStorageUpgradeCandidates:
    def test_returns_db_version_item(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-6.2.7")
        pkg = make_pkg(
            "redis-6.2.14.tar.gz",
            full_version="6.2.14.0.0.0",
            phase=VersionPhase.RELEASE.value,
            version_name="redis_6.2.14",
            recommend=True,
        )

        got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

        assert got == [
            {
                "db_version_id": pkg.db_version_id,
                "version_name": "redis_6.2.14",
                "full_version": "6.2.14.0.0.0",
                "phase": "release",
                "series_name": "Redis-6",
                "recommend": True,
                "is_current": False,
            }
        ]

    def test_package_without_v2_version_is_excluded(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-6.2.7")
        make_pkg("redis-6.2.14.tar.gz", phase=None, priority=1)

        assert proxy_mod.get_cluster_storage_versions_for_upgrade(1) == []

    def test_hides_valkey_and_lower_versions_and_marks_current(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-6.2.14")
        make_pkg("redis-6.2.7.tar.gz")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7")
        make_pkg("valkey-8.0.1.tar.gz", series="Valkey-8")
        make_pkg("redis-6.2.14.tar.gz")

        got = proxy_mod.get_cluster_storage_versions_for_upgrade(1, "1.1.1.1")

        assert [(item["version_name"], item["is_current"]) for item in got] == [
            ("redis-7.2.4", False),
            ("redis-6.2.14", True),
        ]

    def test_hides_redis_when_online_is_valkey(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="valkey-8.0.1")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7")
        make_pkg("valkey-8.0.1.tar.gz", series="Valkey-8")
        make_pkg("valkey-9.0.0.tar.gz", series="Valkey-9")

        assert _names(proxy_mod.get_cluster_storage_versions_for_upgrade(1)) == ["valkey-9.0.0", "valkey-8.0.1"]

    def test_all_enabled_phases_are_returned(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-7.2.0")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7", phase=VersionPhase.RELEASE.value)
        make_pkg("redis-7.2.5.tar.gz", series="Redis-7", phase=VersionPhase.ALPHA.value)
        make_pkg("redis-7.2.6.tar.gz", series="Redis-7", phase=VersionPhase.BETA.value)
        make_pkg("redis-7.2.7.tar.gz", series="Redis-7", phase=VersionPhase.RC.value)

        got = {item["version_name"]: item["phase"] for item in proxy_mod.get_cluster_storage_versions_for_upgrade(1)}

        assert got == {"redis-7.2.7": "rc", "redis-7.2.6": "beta", "redis-7.2.5": "alpha", "redis-7.2.4": "release"}

    def test_disabled_version_and_version_without_enabled_package_are_excluded(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-7.2.0")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7")
        make_pkg("redis-7.2.5.tar.gz", series="Redis-7", phase="alpha", enable=False)
        make_pkg("redis-7.2.6.tar.gz", series="Redis-7", phase="beta", version_enable=False)

        assert _names(proxy_mod.get_cluster_storage_versions_for_upgrade(1)) == ["redis-7.2.4"]

    def test_recommend_first_then_version_desc(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-7.2.0")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7", recommend=True)
        make_pkg("redis-7.2.5.tar.gz", series="Redis-7", phase="alpha")
        make_pkg("redis-7.2.3.tar.gz", series="Redis-7")

        assert _names(proxy_mod.get_cluster_storage_versions_for_upgrade(1)) == [
            "redis-7.2.4",
            "redis-7.2.5",
            "redis-7.2.3",
        ]

    def test_same_full_version_in_two_distributions_yields_two_candidates(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-7.2.0")
        alpha = make_pkg("redis-7.2.4.tar.gz", series="Redis-7", phase="alpha", version_name="v-alpha")
        release = make_pkg(
            "redis-7.2.4.tar.gz", series="Redis-7", version_name="v-release", recommend=True, distribution="test-r2"
        )

        got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

        assert [(item["version_name"], item["db_version_id"]) for item in got] == [
            ("v-release", release.db_version_id),
            ("v-alpha", alpha.db_version_id),
        ]

    def test_packages_of_one_version_yield_one_candidate(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="redis-7.2.0")
        pkg = make_pkg("redis-7.2.4.tar.gz", series="Redis-7")
        Package.objects.create(
            name="redis-7.2.4.tgz",
            version="Redis-7",
            pkg_type=pkg.pkg_type,
            db_type=pkg.db_type,
            path="/tmp/redis-7.2.4.tgz",
            size=0,
            md5="",
            db_version_id=pkg.db_version_id,
            permit_os_type=pkg.permit_os_type,
            creator="admin",
            updater="admin",
        )

        got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

        assert [item["db_version_id"] for item in got] == [pkg.db_version_id]

    def test_tendisssd_only_returns_online_version(self, monkeypatch):
        online = "redis-4.0.9-rocksdb-v1.3"
        _stub_cluster(
            monkeypatch,
            cluster_type=ClusterType.TwemproxyTendisSSDInstance,
            online_version=online,
            major="TendisSSD-1.3",
        )
        tendisssd = MediumEnum.TendisSsd.value
        pkg = make_pkg(
            f"{online}.tar.gz",
            pkg_type=tendisssd,
            series="TendisSSD-1.3",
            full_version="4.0.9.0.0.0",
            version_name="tendisssd_1.3",
        )
        make_pkg("redis-4.0.10-rocksdb-v1.3.tar.gz", pkg_type=tendisssd, series="TendisSSD-1.3")

        got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

        assert [(item["db_version_id"], item["is_current"]) for item in got] == [(pkg.db_version_id, True)]

    def test_unparseable_online_version_returns_empty(self, monkeypatch):
        _stub_cluster(monkeypatch, online_version="bad")
        make_pkg("redis-6.2.7.tar.gz")
        make_pkg("redis-7.2.4.tar.gz", series="Redis-7")

        assert proxy_mod.get_cluster_storage_versions_for_upgrade(1) == []

    def test_tendisssd_without_package_returns_empty(self, monkeypatch):
        _stub_cluster(
            monkeypatch,
            cluster_type=ClusterType.TwemproxyTendisSSDInstance,
            online_version="redis-4.0.9-rocksdb-v1.3",
            major="TendisSSD-1.3",
        )

        assert proxy_mod.get_cluster_storage_versions_for_upgrade(1) == []


@pytest.mark.usefixtures("clean_redis_packages")
class TestProxyUpgradeCandidates:
    def test_returns_db_version_item(self, monkeypatch):
        _stub_cluster(
            monkeypatch, cluster_type=ClusterType.TendisPredixyRedisCluster, proxy_versions=["predixy-1.4.3"]
        )
        pkg = make_pkg(
            "predixy-1.4.3.tar.gz",
            pkg_type=MediumEnum.Predixy.value,
            series="Predixy-latest",
            phase=VersionPhase.RC.value,
            version_name="predixy_1.4.3_rc1",
        )

        got = proxy_mod.get_cluster_proxy_version_for_upgrade(1)

        assert got == [
            {
                "db_version_id": pkg.db_version_id,
                "version_name": "predixy_1.4.3_rc1",
                "full_version": "1.4.3.0.0.0",
                "phase": "rc",
                "series_name": "Predixy-latest",
                "recommend": False,
                "is_current": True,
            }
        ]

    def test_twemproxy_excludes_disabled_and_marks_current_by_build(self, monkeypatch):
        calls = _stub_cluster(
            monkeypatch,
            cluster_type=ClusterType.TendisTwemproxyRedisInstance,
            proxy_versions=["twemproxy-0.4.1-v28"],
        )
        twemproxy = MediumEnum.Twemproxy.value
        make_pkg("twemproxy-0.4.1-v28.tar.gz", pkg_type=twemproxy, series="Twemproxy-latest")
        make_pkg("twemproxy-0.4.1-v29.tar.gz", pkg_type=twemproxy, series="Twemproxy-latest", enable=False)
        make_pkg("twemproxy-0.4.1-v30.tar.gz", pkg_type=twemproxy, series="Twemproxy-latest", version_enable=False)
        make_pkg("twemproxy-0.4.1-v31.tar.gz", pkg_type=twemproxy, series="Twemproxy-latest", phase="alpha")

        got = proxy_mod.get_cluster_proxy_version_for_upgrade(1, "2.2.2.2")

        assert [(item["version_name"], item["is_current"]) for item in got] == [
            ("twemproxy-0.4.1-v31", False),
            ("twemproxy-0.4.1-v28", True),
        ]
        assert calls == [{"2.2.2.2"}]


@pytest.mark.usefixtures("clean_redis_packages")
class TestMajorVersionByVersionName:
    def test_prefers_v2_version_series_name(self):
        make_pkg("valkey-8.0.1.tar.gz", series="Valkey-8", phase="alpha", pkg_version="legacy-series")

        assert proxy_mod.get_major_version_by_version_name("valkey-8.0.1") == "Valkey-8"

    def test_unresolvable_or_ambiguous_returns_empty(self):
        make_pkg("redis-7.2.5.tar.gz", series="Redis-7-dev", phase="alpha", version_name="redis-7.2.5-dev")
        make_pkg("redis-7.2.5.tar.gz", series="Redis-7", recommend=True, version_name="r725", distribution="test-r2")

        assert proxy_mod.get_major_version_by_version_name("redis-7.2.5") == ""
        assert proxy_mod.get_major_version_by_version_name("redis-9.9.9") == ""
