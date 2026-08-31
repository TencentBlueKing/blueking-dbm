# -*- coding: utf-8 -*-
from types import SimpleNamespace

from backend.db_meta.enums import ClusterType
from backend.flow.utils.redis import redis_proxy_util as proxy_mod
from backend.flow.utils.redis.redis_util import get_redis_engine_family, is_cross_engine_version_change


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


class _FakePackageQuery:
    def __init__(self, names):
        self.names = names

    def order_by(self, *args):
        return self

    def values_list(self, *args, **kwargs):
        return self.names


def _stub_storage_upgrade_versions(monkeypatch, online_version, package_names):
    monkeypatch.setattr(
        proxy_mod.Cluster.objects,
        "get",
        lambda **kwargs: SimpleNamespace(id=1, cluster_type=ClusterType.TendisPredixyRedisCluster),
    )
    monkeypatch.setattr(proxy_mod, "get_cluster_redis_version", lambda *args, **kwargs: online_version)
    monkeypatch.setattr(proxy_mod.Package.objects, "filter", lambda **kwargs: _FakePackageQuery(package_names))


def test_upgrade_versions_hide_valkey_when_online_is_redis(monkeypatch):
    _stub_storage_upgrade_versions(
        monkeypatch,
        "redis-6.2.14",
        ["redis-7.2.4.tar.gz", "valkey-8.0.1.tar.gz", "redis-6.2.14.tar.gz"],
    )

    got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

    assert got == ["redis-7.2.4", "redis-6.2.14"]


def test_upgrade_versions_hide_redis_when_online_is_valkey(monkeypatch):
    _stub_storage_upgrade_versions(
        monkeypatch,
        "valkey-8.0.1",
        ["redis-7.2.4.tar.gz", "valkey-8.0.1.tar.gz", "valkey-9.0.0.tar.gz"],
    )

    got = proxy_mod.get_cluster_storage_versions_for_upgrade(1)

    assert got == ["valkey-8.0.1", "valkey-9.0.0"]
