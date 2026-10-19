# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import ConfigTypeEnum
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_databases import (
    parse_databases_value_allowed,
    query_plat_databases_range,
    validate_apply_databases,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("[1,16]", (1, 16)),
        ("[1,64]", (1, 64)),
        ("[2, 16]", (2, 16)),
        ("(1,64]", (1, 64)),
        ("1|2|16", None),
        ("", None),
        (None, None),
        ("[10,1]", None),
    ],
)
def test_parse_databases_value_allowed(raw, expected):
    assert parse_databases_value_allowed(raw) == expected


def test_validate_without_plat_range_allows_64(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: None,
    )
    assert validate_apply_databases(64, "RedisInstance", "Redis-74") == 64


def test_validate_rejects_out_of_plat_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: (1, 16),
    )
    with pytest.raises(ValueError, match=r"\[1, 16\]"):
        validate_apply_databases(64, "RedisInstance", "Redis-74")


def test_validate_accepts_in_plat_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.query_plat_databases_range",
        lambda *args, **kwargs: (1, 64),
    )
    assert validate_apply_databases(64, "RedisInstance", "Redis-74") == 64


def test_query_plat_databases_range(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        lambda params: {"conf_names": {"databases": {"value_allowed": "[1,64]"}}},
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") == (1, 64)


def test_query_plat_databases_range_list_format(monkeypatch):
    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        lambda params: {"conf_names": [{"conf_name": "databases", "value_allowed": "[1,64]"}]},
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") == (1, 64)


def test_query_plat_databases_range_api_error(monkeypatch):
    def _boom(params):
        raise RuntimeError("dbconfig down")

    monkeypatch.setattr(
        "backend.flow.utils.redis.redis_databases.DBConfigApi.list_conf_name",
        _boom,
    )
    assert query_plat_databases_range("RedisInstance", "Redis-74") is None


@pytest.mark.parametrize("cluster_type", [ClusterType.TendisRedisInstance, ClusterType.TendisTendisplusInsance])
def test_redis_password_fallback_without_proxy_queries_only_dbconf(monkeypatch, cluster_type):
    cluster = SimpleNamespace(
        id=1,
        bk_cloud_id=0,
        bk_biz_id=2,
        db_module_id=3,
        immute_domain="redis.example.com",
        cluster_type=cluster_type,
        major_version="Redis-6",
    )
    query_conf_item = Mock(return_value={"content": {"requirepass": "redis-secret"}})
    monkeypatch.setattr(Cluster.objects, "get", lambda **kwargs: cluster)
    monkeypatch.setattr(
        "backend.flow.utils.base.payload_handler.DBPrivManagerApi.get_password", Mock(return_value={"items": []})
    )
    monkeypatch.setattr("backend.flow.utils.base.payload_handler.DBConfigApi.query_conf_item", query_conf_item)

    passwords = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)

    assert passwords == {
        "redis_password": "redis-secret",
        "redis_proxy_password": "",
        "redis_proxy_admin_password": "",
    }
    query_conf_item.assert_called_once()
    params = query_conf_item.call_args.kwargs["params"]
    assert params["namespace"] == cluster_type
    assert params["conf_type"] == ConfigTypeEnum.DBConf
    assert params["conf_file"] == "Redis-6"


@pytest.mark.parametrize(
    "cluster_type,proxy_version,proxy_content",
    [
        (
            ClusterType.TendisPredixyRedisCluster,
            "Predixy-latest",
            {"password": "proxy-secret", "predixy_admin_passwd": "admin-secret"},
        ),
        (ClusterType.TendisTwemproxyRedisInstance, "Twemproxy-latest", {"password": "proxy-secret"}),
    ],
)
def test_redis_password_fallback_with_proxy_queries_both_configs(
    monkeypatch, cluster_type, proxy_version, proxy_content
):
    cluster = SimpleNamespace(
        bk_biz_id=2,
        db_module_id=3,
        immute_domain="redis.example.com",
        cluster_type=cluster_type,
        major_version="Redis-6",
        proxy_version=proxy_version,
    )
    query_conf_item = Mock(side_effect=[{"content": proxy_content}, {"content": {"requirepass": "redis-secret"}}])
    monkeypatch.setattr("backend.flow.utils.base.payload_handler.DBConfigApi.query_conf_item", query_conf_item)

    passwords = PayloadHandler.redis_get_cluster_pass_from_dbconfig(cluster)

    assert passwords == {
        "redis_password": "redis-secret",
        "redis_proxy_password": "proxy-secret",
        "redis_proxy_admin_password": proxy_content.get("predixy_admin_passwd", ""),
    }
    assert query_conf_item.call_count == 2
    proxy_params, redis_params = [call.kwargs["params"] for call in query_conf_item.call_args_list]
    assert proxy_params["namespace"] == redis_params["namespace"] == cluster_type
    assert proxy_params["conf_type"] == ConfigTypeEnum.ProxyConf
    assert proxy_params["conf_file"] == proxy_version
    assert redis_params["conf_type"] == ConfigTypeEnum.DBConf
    assert redis_params["conf_file"] == "Redis-6"
