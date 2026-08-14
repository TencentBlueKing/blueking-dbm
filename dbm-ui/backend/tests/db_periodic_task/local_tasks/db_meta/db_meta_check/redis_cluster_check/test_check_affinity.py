# -*- coding: utf-8 -*-
import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def redis_affinity_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(
            "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.redis_cluster_check.check_affinity"
        )


def _storage(ip: str, subzone_id: int, rack_id: str):
    return SimpleNamespace(machine=SimpleNamespace(ip=ip, bk_sub_zone_id=subzone_id, bk_rack_id=rack_id))


def test_same_subzone_cross_switch_suggests_moving_slave_to_expected_subzone(redis_affinity_module):
    checker = redis_affinity_module.RedisAffinityChecker
    checker._subzone_map_cache = {1: "test-subzone-a", 2: "test-subzone-b"}

    msg = checker._check_backend_same_subzone(
        master_obj=_storage("1.1.1.1", 1, "rack-a"),
        slave_obj=_storage("1.1.1.2", 2, "rack-b"),
        expected_subzone_id=1,
    )

    assert "请将副节点机器 1.1.1.2 替换或迁移到 园区(test-subzone-a) 且不同机架" in msg
    assert "主节点机器 1.1.1.1 替换" not in msg


def test_same_subzone_cross_switch_suggests_moving_master_when_slave_is_in_expected_subzone(redis_affinity_module):
    checker = redis_affinity_module.RedisAffinityChecker
    checker._subzone_map_cache = {1: "test-subzone-a", 2: "test-subzone-b"}

    msg = checker._check_backend_same_subzone(
        master_obj=_storage("1.1.1.2", 2, "rack-b"),
        slave_obj=_storage("1.1.1.1", 1, "rack-a"),
        expected_subzone_id=1,
    )

    assert "请将主节点机器 1.1.1.2 替换或迁移到 园区(test-subzone-a) 且不同机架" in msg
    assert "副节点机器 1.1.1.1 替换" not in msg


def test_check_redis_affinity_exits_when_disabled(redis_affinity_module):
    config = redis_affinity_module.RedisAffinityCheckConfig(enabled=False)

    with patch.object(redis_affinity_module.RedisAffinityCheckConfig, "from_settings", return_value=config):
        with patch.object(redis_affinity_module, "RedisAffinityChecker") as checker_cls:
            redis_affinity_module.check_redis_affinity()

    checker_cls.assert_not_called()


def test_get_candidate_clusters_filters_by_bk_cloud_ids(redis_affinity_module):
    config = redis_affinity_module.RedisAffinityCheckConfig(
        cluster_types=["RedisInstance"],
        bk_cloud_ids=[0],
    )
    query = MagicMock()
    query.exclude.return_value = query
    query.filter.return_value = query
    query.values_list.return_value = [1, 2]

    with patch.object(redis_affinity_module.Cluster.objects, "filter", return_value=query) as cluster_filter:
        redis_affinity_module._get_candidate_cluster_ids(config)

    cluster_filter.assert_called_once_with(cluster_type__in=["RedisInstance"])
    query.filter.assert_called_once_with(bk_cloud_id__in=[0])
    query.values_list.assert_called_once_with("id", flat=True)


def test_get_candidate_clusters_checks_all_clouds_when_bk_cloud_ids_empty(redis_affinity_module):
    config = redis_affinity_module.RedisAffinityCheckConfig(cluster_types=["RedisInstance"])
    query = MagicMock()
    query.exclude.return_value = query
    query.values_list.return_value = []

    with patch.object(redis_affinity_module.Cluster.objects, "filter", return_value=query):
        redis_affinity_module._get_candidate_cluster_ids(config)

    query.filter.assert_not_called()


def test_check_all_clusters_ingests_portrait_and_survives_ingest_failure(redis_affinity_module):
    config = redis_affinity_module.RedisAffinityCheckConfig(enabled=True, cluster_types=["RedisInstance"])
    cluster = SimpleNamespace(id=1, immute_domain="a.redis.db", bk_biz_id=1001)
    warning_row = {
        "cluster": cluster,
        "state": redis_affinity_module.ReportStateType.WARNING,
        "msg": "affinity warning",
        "subtype": redis_affinity_module.MetaCheckSubType.AffinityViolation,
    }

    with patch.object(redis_affinity_module, "RedisReportWriter"):
        checker = redis_affinity_module.RedisAffinityChecker(config)

    with patch.object(redis_affinity_module.BKSubzone, "get_subzone_map", return_value={}), patch.object(
        redis_affinity_module, "delete_old_meta_check_reports"
    ), patch.object(redis_affinity_module, "_get_candidate_cluster_ids", return_value=[1]), patch.object(
        redis_affinity_module, "_fetch_affinity_ignore_cluster_ids", return_value=set()
    ), patch.object(
        redis_affinity_module, "_load_affinity_clusters_page", return_value=[cluster]
    ), patch.object(
        checker, "_should_ignore_cluster", return_value=False
    ), patch.object(
        checker, "_check_cluster_affinity", return_value=[warning_row]
    ), patch.object(
        redis_affinity_module, "safe_write_meta_reports"
    ) as write_mock, patch.object(
        redis_affinity_module, "ingest_abnormal_cluster_rows"
    ) as ingest:
        checker.check_all_clusters()

    write_mock.assert_called_once()
    ingest.assert_called_once()
    assert ingest.call_args.kwargs["prefix"] == "[亲和性]"
    assert ingest.call_args.kwargs["dimension"] == redis_affinity_module.RedisPortraitDimensionCode.TOPOLOGY_SCALE

    with patch.object(redis_affinity_module.BKSubzone, "get_subzone_map", return_value={}), patch.object(
        redis_affinity_module, "delete_old_meta_check_reports"
    ), patch.object(redis_affinity_module, "_get_candidate_cluster_ids", return_value=[1]), patch.object(
        redis_affinity_module, "_fetch_affinity_ignore_cluster_ids", return_value=set()
    ), patch.object(
        redis_affinity_module, "_load_affinity_clusters_page", return_value=[cluster]
    ), patch.object(
        checker, "_should_ignore_cluster", return_value=False
    ), patch.object(
        checker, "_check_cluster_affinity", return_value=[warning_row]
    ), patch.object(
        redis_affinity_module, "safe_write_meta_reports"
    ), patch(
        "backend.db_report.portrait.redis_ingest.ingest_summary",
        side_effect=RuntimeError("portrait boom"),
    ):
        checker.check_all_clusters()
