# -*- coding: utf-8 -*-
import pytest
from rest_framework.exceptions import ValidationError

from backend.configuration.constants import DBType
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis.redis_package_resolver import RedisUpgradeTargetError, resolve_ticket_upgrade_targets
from backend.tests.mock_data.db_package.v2 import create_redis_package
from backend.ticket.builders.redis import redis_cluster_version_update as serializer_mod
from backend.ticket.builders.redis.redis_cluster_version_update import RedisVersionUpdateDetailSerializer

pytestmark = pytest.mark.usefixtures("clean_redis_packages")


@pytest.fixture
def clean_redis_packages(db):
    Package.objects.filter(db_type=DBType.Redis.value).delete()


def _version(name, full_version, series="Redis-7", **kwargs):
    return create_redis_package(
        f"{name}.tar.gz", series=series, full_version=full_version, phase="release", version_name=name, **kwargs
    ).db_version_id


def _attrs(current_versions, target_versions, node_type=RedisVerUpdateNodeType.Backend.value):
    return {
        "infos": [
            {
                "cluster_id": 1,
                "node_type": node_type,
                "current_versions": current_versions,
                "target_versions": target_versions,
            }
        ]
    }


def _backend_attrs(current_versions, db_version_id):
    return _attrs(current_versions, [{"ip": "1.1.1.1", "db_version_id": db_version_id}])


def _validate_targets(attrs):
    RedisVersionUpdateDetailSerializer.validate_backend_targets(attrs, resolve_ticket_upgrade_targets(attrs["infos"]))


class TestValidateBackendTargets:
    @pytest.mark.parametrize(
        "current, target_name, target_full, series",
        [
            ("redis-6.2.14", "valkey-8.0.1", "8.0.1.0.0.0", "Valkey-8"),
            ("valkey-8.0.1", "redis-7.2.4", "7.2.4.0.0.0", "Redis-7"),
        ],
    )
    def test_rejects_cross_engine(self, current, target_name, target_full, series):
        attrs = _backend_attrs([current], _version(target_name, target_full, series))

        with pytest.raises(ValidationError, match="请使用 DTS 数据迁移"):
            _validate_targets(attrs)

    def test_allows_same_engine_and_same_version(self):
        _validate_targets(_backend_attrs(["redis-6.2.14"], _version("redis-7.2.4", "7.2.4.0.0.0")))
        _validate_targets(_backend_attrs(["redis-7.2.5"], _version("redis-7.2.5", "7.2.5.0.0.0")))
        _validate_targets(_backend_attrs(["valkey-8.0.1"], _version("valkey-9.0.0", "9.0.0.0.0.0", "Valkey-9")))

    def test_rejects_target_below_all_current_versions(self):
        attrs = _backend_attrs(["redis-7.2.4", "redis-7.0.15"], _version("redis-6.2.14", "6.2.14.0.0.0"))

        with pytest.raises(ValidationError, match="不支持降级"):
            _validate_targets(attrs)

    def test_allows_target_above_some_current_versions(self):
        _validate_targets(_backend_attrs(["redis-7.2.4", "redis-6.2.7"], _version("redis-6.2.14", "6.2.14.0.0.0")))

    def test_rejects_empty_current_versions(self):
        with pytest.raises(ValidationError, match="当前版本列表不能为空"):
            _validate_targets(_backend_attrs([], _version("redis-7.2.4", "7.2.4.0.0.0")))

    def test_skips_proxy(self):
        proxy_id = create_redis_package(
            "twemproxy-0.4.1-v28.tar.gz",
            pkg_type=MediumEnum.Twemproxy.value,
            series="Twemproxy-latest",
            full_version="0.4.1.28.0.0",
            phase="release",
        ).db_version_id
        attrs = _attrs(
            ["twemproxy-0.4.1-v30"],
            [{"ip": "1.1.1.1", "db_version_id": proxy_id}],
            node_type=RedisVerUpdateNodeType.Proxy.value,
        )

        _validate_targets(attrs)


class TestValidate:
    def test_rejects_disabled_version(self):
        attrs = _backend_attrs(["redis-6.2.14"], _version("redis-7.2.5", "7.2.5.0.0.0", version_enable=False))

        with pytest.raises(ValidationError, match="已禁用"):
            RedisVersionUpdateDetailSerializer().validate(attrs)

    def test_rejects_entry_without_id(self):
        attrs = _attrs(["redis-6.2.14"], [{"ip": "1.1.1.1", "version": "redis-7.2.5"}])

        with pytest.raises(ValidationError, match="格式不合法"):
            RedisVersionUpdateDetailSerializer().validate(attrs)

    def test_converts_resolver_errors(self, monkeypatch):
        def reject(infos, require_enabled=False):
            assert require_enabled
            raise RedisUpgradeTargetError("db_version_id=9 下找不到 redis 介质包")

        monkeypatch.setattr(serializer_mod, "resolve_ticket_upgrade_targets", reject)

        with pytest.raises(ValidationError, match="db_version_id=9"):
            RedisVersionUpdateDetailSerializer().validate(_backend_attrs(["redis-6.2.14"], 9))
