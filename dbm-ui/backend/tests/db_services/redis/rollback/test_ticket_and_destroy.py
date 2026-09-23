# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from rest_framework.exceptions import ValidationError

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import (
    SELECT_MODE_BY_IDENTIFY,
    SELECT_MODE_BY_TASK_ID,
    SELECT_MODE_BY_TIME,
    infer_select_mode,
)
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.flow.engine.bamboo.scene.redis.redis_rollback.destroy import RedisRollbackDestroyFlow
from backend.ticket.builders.redis.redis_rollback import RedisRollbackDetailSerializer


def _ticket_info(**extra):
    attr = {
        "cluster_id": 1,
        "resource_spec": {"redis": {"count": 1, "id": 1}},
        "backup_identify": "SCHEDULED-2026010101",
    }
    attr.update(extra)
    return attr


def test_ticket_rejects_non_cache_cluster():
    serializer = RedisRollbackDetailSerializer.InfoSerializer()
    cluster = MagicMock()
    cluster.cluster_type = ClusterType.TwemproxyTendisSSDInstance.value
    cluster.immute_domain = "ssd.example.db"
    with patch("backend.ticket.builders.redis.redis_rollback.Cluster") as cluster_model:
        cluster_model.objects.get.return_value = cluster
        try:
            serializer.validate(_ticket_info())
            assert False, "expected ValidationError"
        except ValidationError as exc:
            assert "REDIS_DATA_STRUCTURE" in str(exc)


def test_destroy_refuses_v1_record():
    task = MagicMock()
    task.id = 9
    task.rollback_version = "datastructure"
    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.destroy.TbTendisRollbackTasks") as model:
        model.objects.get.return_value = task
        try:
            RedisRollbackDestroyFlow.load_task({"task_id": 9})
            assert False, "expected RollbackPlanError"
        except RollbackPlanError as exc:
            assert "REDIS_DATA_STRUCTURE_TASK_DELETE" in str(exc.message)


def test_destroy_payload_omits_passwords_and_supports_multi_proxy():
    task = MagicMock()
    task.id = 3
    task.related_rollback_bill_id = 100
    task.bk_biz_id = 1
    task.bk_cloud_id = 0
    task.prod_cluster = "cache.example.db"
    task.prod_cluster_id = 8
    task.temp_cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    task.temp_instance_range = ["2.2.2.2:30000", "2.2.2.2:30001"]
    task.temp_cluster_proxy = "2.2.2.2:50000 3.3.3.3:50000"
    task.rollback_version = "rollback"
    task.temp_proxy_password = "secret"
    task.temp_redis_password = "secret2"
    payload = RedisRollbackDestroyFlow.task_payload(task)
    assert "temp_proxy_password" not in payload
    assert "temp_redis_password" not in payload
    assert payload["temp_cluster_proxies"] == ["2.2.2.2:50000", "3.3.3.3:50000"]


def test_infer_select_mode_priority():
    assert infer_select_mode({"backup_identify": "SCHEDULED-1"}) == SELECT_MODE_BY_IDENTIFY
    assert infer_select_mode({"backup_identify": "SCHEDULED-1", "recovery_time_point": "t"}) == SELECT_MODE_BY_IDENTIFY
    assert infer_select_mode({"recovery_time_point": "t"}) == SELECT_MODE_BY_TIME
    assert infer_select_mode({"backup_task_ids": ["t1"]}) == SELECT_MODE_BY_TASK_ID
    try:
        infer_select_mode({})
        assert False, "expected RollbackPlanError"
    except RollbackPlanError as exc:
        assert "backup_identify" in str(exc.message)


def _cache_serializer():
    cluster = MagicMock()
    cluster.cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    cluster.immute_domain = "cache.example.db"
    return RedisRollbackDetailSerializer.InfoSerializer(), cluster


def test_ticket_allows_identify_only():
    """Specifying only identify picks the latest round for all shards."""
    serializer, cluster = _cache_serializer()
    with patch("backend.ticket.builders.redis.redis_rollback.Cluster") as cluster_model, patch(
        "backend.ticket.builders.redis.redis_rollback.RollbackPlanner"
    ) as planner_cls:
        cluster_model.objects.get.return_value = cluster
        planner_cls.return_value.build.return_value = MagicMock()
        assert serializer.validate(_ticket_info())


def test_ticket_allows_identify_plus_shards():
    serializer, cluster = _cache_serializer()
    with patch("backend.ticket.builders.redis.redis_rollback.Cluster") as cluster_model, patch(
        "backend.ticket.builders.redis.redis_rollback.RollbackPlanner"
    ) as planner_cls:
        cluster_model.objects.get.return_value = cluster
        planner_cls.return_value.build.return_value = MagicMock()
        attr = _ticket_info(
            shards=[
                {"shard_value": "0-104999", "round_key": "a.aof.zst"},
                {"shard_value": "105000-209999", "round_key": ""},
            ]
        )
        assert serializer.validate(attr)


def test_ticket_surfaces_planner_error():
    """Host count constraints are evaluated by planner; ticket serializer forwards failures.

    Previously serializer checked len(shards), which no-ops on whole-cluster rollback where shards is empty.
    """
    serializer, cluster = _cache_serializer()
    with patch("backend.ticket.builders.redis.redis_rollback.Cluster") as cluster_model, patch(
        "backend.ticket.builders.redis.redis_rollback.RollbackPlanner"
    ) as planner_cls:
        cluster_model.objects.get.return_value = cluster
        planner_cls.return_value.build.side_effect = RollbackPlanError(context={"message": "主机数量(3)不能大于待构造分片数(1)"})
        attr = _ticket_info(resource_spec={"redis": {"count": 3, "id": 1}}, shards=[{"shard_value": "0-104999"}])
        try:
            serializer.validate(attr)
            assert False, "expected ValidationError"
        except ValidationError as exc:
            assert "待构造分片数" in str(exc)


def test_ticket_requires_backup_identify():
    serializer = RedisRollbackDetailSerializer.InfoSerializer(
        data={"cluster_id": 1, "resource_spec": {"redis": {"count": 1}}}
    )
    assert serializer.is_valid() is False
    assert "backup_identify" in serializer.errors
