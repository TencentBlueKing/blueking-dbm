# -*- coding: utf-8 -*-
import pytest
from rest_framework.exceptions import ValidationError

from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.ticket.builders.redis.redis_cluster_version_update import RedisVersionUpdateDetailSerializer


def _backend_attrs(current, target, target_as_dict=True):
    target_versions = [{"ip": "1.1.1.1", "version": target}] if target_as_dict else [target]
    return {
        "infos": [
            {
                "cluster_id": 1,
                "node_type": RedisVerUpdateNodeType.Backend.value,
                "current_versions": [current],
                "target_versions": target_versions,
            }
        ]
    }


def test_validate_engine_family_rejects_redis_to_valkey():
    serializer = RedisVersionUpdateDetailSerializer()
    with pytest.raises(ValidationError, match="请使用 DTS 数据迁移"):
        serializer.validate_engine_family(_backend_attrs("redis-6.2.14", "valkey-8.0.1"))


def test_validate_engine_family_rejects_valkey_to_redis():
    serializer = RedisVersionUpdateDetailSerializer()
    with pytest.raises(ValidationError, match="请使用 DTS 数据迁移"):
        serializer.validate_engine_family(_backend_attrs("valkey-8.0.1", "redis-7.2.4"))


def test_validate_engine_family_rejects_string_target_versions():
    serializer = RedisVersionUpdateDetailSerializer()
    with pytest.raises(ValidationError, match="请使用 DTS 数据迁移"):
        serializer.validate_engine_family(_backend_attrs("redis-6.2.14", "valkey-8.0.1", target_as_dict=False))


def test_validate_engine_family_allows_same_engine():
    serializer = RedisVersionUpdateDetailSerializer()
    serializer.validate_engine_family(_backend_attrs("redis-6.2.14", "redis-7.2.4"))
    serializer.validate_engine_family(_backend_attrs("valkey-8.0.1", "valkey-9.0.0"))


def test_validate_engine_family_allows_same_family_multiple_current_versions():
    serializer = RedisVersionUpdateDetailSerializer()
    serializer.validate_engine_family(
        {
            "infos": [
                {
                    "cluster_id": 1,
                    "node_type": RedisVerUpdateNodeType.Backend.value,
                    "current_versions": ["redis-6.2.14", "redis-6.2.7"],
                    "target_versions": [{"ip": "1.1.1.1", "version": "redis-7.2.4"}],
                }
            ]
        }
    )


def test_validate_engine_family_rejects_empty_current_versions():
    serializer = RedisVersionUpdateDetailSerializer()
    with pytest.raises(ValidationError, match="当前版本列表不能为空"):
        serializer.validate_engine_family(
            {
                "infos": [
                    {
                        "cluster_id": 1,
                        "node_type": RedisVerUpdateNodeType.Backend.value,
                        "current_versions": [],
                        "target_versions": [{"ip": "1.1.1.1", "version": "redis-7.2.4"}],
                    }
                ]
            }
        )


def test_validate_engine_family_skips_proxy():
    serializer = RedisVersionUpdateDetailSerializer()
    serializer.validate_engine_family(
        {
            "infos": [
                {
                    "cluster_id": 1,
                    "node_type": RedisVerUpdateNodeType.Proxy.value,
                    "current_versions": ["twemproxy-0.4.1-v30"],
                    "target_versions": [{"ip": "1.1.1.1", "version": "valkey-8.0.1"}],
                }
            ]
        }
    )
