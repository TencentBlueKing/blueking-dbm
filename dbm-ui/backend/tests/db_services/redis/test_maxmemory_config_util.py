# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_services.redis.maxmemory_set import util
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, NameSpaceEnum


def test_business_config_uses_architecture_namespace(monkeypatch):
    query = Mock(
        return_value={
            "level_name": "app",
            "revision": "1",
            "content": {
                "enable": "false",
                "used_memory_change_threshold": "500MiB",
                "used_memory_change_percent": "25",
            },
        }
    )
    monkeypatch.setattr(util.DBConfigApi, "query_conf_item", query)

    result = util.get_dbmon_maxmemory_config_by_bkbizid(100, namespace=NameSpaceEnum.RedisInstance)

    assert result == {
        "enable": "false",
        "used_memory_change_threshold": "500MiB",
        "used_memory_change_percent": "25",
    }
    assert query.call_args.kwargs["params"] == {
        "bk_biz_id": "100",
        "level_name": LevelName.APP,
        "level_value": "100",
        "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
        "conf_file": ConfigFileEnum.MaxMemorySet,
        "conf_type": ConfigTypeEnum.Config,
        "namespace": NameSpaceEnum.RedisInstance,
        "format": FormatType.MAP,
    }


def test_business_config_without_namespace_returns_unmodified_rediscomm_content(monkeypatch):
    content = {
        "bk_biz_id_blacklist": "10, 100, 200",
        "master_used_memory_change_threshold": "200MB",
        "master_used_memory_change_percent": "20",
    }
    query = Mock(return_value={"content": content})
    monkeypatch.setattr(util.DBConfigApi, "query_conf_item", query)

    assert util.get_dbmon_maxmemory_config_by_bkbizid(100) == content
    assert query.call_args.kwargs["params"]["namespace"] == NameSpaceEnum.RedisCommon


def test_cluster_config_uses_cluster_namespace_and_domain(monkeypatch):
    cluster = SimpleNamespace(bk_biz_id=100, cluster_type=NameSpaceEnum.RedisInstance, immute_domain="redis.test.db")
    monkeypatch.setattr(util.Cluster.objects, "get", Mock(return_value=cluster))
    query = Mock(
        return_value={
            "content": {
                "enable": "true",
                "used_memory_change_threshold": "500MiB",
                "used_memory_change_percent": "30",
            }
        }
    )
    monkeypatch.setattr(util.DBConfigApi, "query_conf_item", query)

    assert util.get_dbmon_maxmemory_config_by_cluster_ids([1]) == {
        "enable": "true",
        "used_memory_change_threshold": "500MiB",
        "used_memory_change_percent": "30",
    }
    assert query.call_args.kwargs["params"] == {
        "bk_biz_id": "100",
        "level_name": LevelName.CLUSTER,
        "level_value": "redis.test.db",
        "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
        "conf_file": ConfigFileEnum.MaxMemorySet,
        "conf_type": ConfigTypeEnum.Config,
        "namespace": NameSpaceEnum.RedisInstance,
        "format": FormatType.MAP,
    }


def test_multiple_clusters_with_same_content_return_content(monkeypatch):
    monkeypatch.setattr(
        util.Cluster.objects,
        "get",
        lambda id: SimpleNamespace(bk_biz_id=100, cluster_type=NameSpaceEnum.RedisInstance, immute_domain=str(id)),
    )
    content = {"enable": "false", "used_memory_change_threshold": "500MiB", "used_memory_change_percent": "20"}
    query = Mock(return_value={"content": content})
    monkeypatch.setattr(util.DBConfigApi, "query_conf_item", query)

    result = util.get_dbmon_maxmemory_config_by_cluster_ids([2, 1, 1])

    assert result == content
    assert [call.kwargs["params"]["level_value"] for call in query.call_args_list] == ["1", "2"]


def test_multiple_clusters_with_different_content_fail(monkeypatch):
    monkeypatch.setattr(
        util.Cluster.objects,
        "get",
        lambda id: SimpleNamespace(bk_biz_id=100, cluster_type=NameSpaceEnum.RedisInstance, immute_domain=str(id)),
    )
    monkeypatch.setattr(
        util.DBConfigApi,
        "query_conf_item",
        Mock(
            side_effect=[
                {
                    "content": {
                        "enable": "true",
                        "used_memory_change_threshold": "500MiB",
                        "used_memory_change_percent": "20",
                    }
                },
                {
                    "content": {
                        "enable": "false",
                        "used_memory_change_threshold": "500MiB",
                        "used_memory_change_percent": "20",
                    }
                },
            ]
        ),
    )

    with pytest.raises(ValueError, match="配置不一致"):
        util.get_dbmon_maxmemory_config_by_cluster_ids([1, 2])


def test_empty_cluster_ids_fail():
    with pytest.raises(ValueError, match="cluster_ids cannot be empty"):
        util.get_dbmon_maxmemory_config_by_cluster_ids([])
