# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.backup_presence import BACKUP_QUERY_BATCH_SIZE, confirm_backup_tasks
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.shards import round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner

_PATCH = "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids"


def _ok(task_id, status=4, **extra):
    row = {"task_id": task_id, "status": status}
    row.update(extra)
    return row


def test_missing_task_is_a_shard_error():
    with patch(_PATCH, return_value=[_ok("t1")]):
        problems = confirm_backup_tasks({"0-1": ["t1", "t2"]})
    assert "t2" in problems["0-1"][0]
    assert "0-1" in problems["0-1"][0]
    assert "t1" not in problems


def test_status_other_than_success_fails():
    with patch(_PATCH, return_value=[_ok("t1", status=1)]):
        problems = confirm_backup_tasks({"0-1": ["t1"]})
    assert "上传状态" in problems["0-1"][0]


def test_expired_flag_fails_even_when_status_is_success():
    with patch(_PATCH, return_value=[_ok("t1", expired="1")]):
        problems = confirm_backup_tasks({"0-1": ["t1"]})
    assert "已过期" in problems["0-1"][0]


def test_api_failure_does_not_pass():
    with patch(_PATCH, side_effect=RuntimeError("down")):
        with pytest.raises(RollbackPlanError) as exc:
            confirm_backup_tasks({"0-1": ["t1"]})
    assert "无法向备份系统确认文件仍在" in str(exc.value.message)


def test_placeholder_shard_is_not_queried():
    query = MagicMock(return_value=[_ok("t1")])
    with patch(_PATCH, query):
        problems = confirm_backup_tasks({"0-1": ["t1"], "2-3": []})
    assert problems == {}
    assert query.call_args.args[0]["task_ids"] == ["t1"]


def test_empty_binlog_queries_full_files_only_and_listed_binlog_is_included():
    query = MagicMock(side_effect=lambda params: [_ok(task_id) for task_id in params["task_ids"]])
    with patch(_PATCH, query):
        assert confirm_backup_tasks({"0-1": ["full-1"]}) == {}
        assert confirm_backup_tasks({"0-1": ["full-1", "binlog-9"]}) == {}
    assert query.call_args_list[0].args[0]["task_ids"] == ["full-1"]
    assert query.call_args_list[1].args[0]["task_ids"] == ["full-1", "binlog-9"]


def test_query_is_batched_at_100():
    ids = ["t{}".format(i) for i in range(BACKUP_QUERY_BATCH_SIZE + 1)]
    query = MagicMock(side_effect=lambda params: [_ok(task_id) for task_id in params["task_ids"]])
    with patch(_PATCH, query):
        assert confirm_backup_tasks({"0-1": ids}) == {}
    assert [len(call.args[0]["task_ids"]) for call in query.call_args_list] == [100, 1]


def _planner():
    cluster = MagicMock()
    cluster.id = 1
    cluster.immute_domain = "cache.example.db"
    cluster.cluster_type = ClusterType.TendisTwemproxyRedisInstance.value
    cluster.bk_cloud_id = 0
    cluster.bk_biz_id = 3
    cluster.major_version = "Redis-6"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    return RollbackPlanner(cluster, {"backup_identify": "SCHEDULED-1"})


def _record(shard_value, file_name):
    return {
        "shard_value": shard_value,
        "source_ip": "1.1.1.9",
        "server_port": 30000,
        "file_name": file_name,
        "task_id": "task-{}".format(file_name),
        "size": 1,
        "backup_identify": "SCHEDULED-1",
        "backup_begin_time": "2026-01-01T01:00:00+00:00",
        "backup_end_time": "2026-01-01T01:01:00+00:00",
        "round_key": round_key_from_filename(file_name),
    }


def test_precheck_marks_missing_file_and_blocks_the_plan():
    planner = _planner()
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=[_record("0-104999", "a.aof.zst")])
    with patch(_PATCH, return_value=[]):
        result = planner.precheck()
    assert result["exist"] is False
    assert result["shards"][0]["ok"] is False
    assert "task-a.aof.zst" in result["shards"][0]["errors"][0]


def test_precheck_api_failure_fails_the_whole_plan():
    planner = _planner()
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=[_record("0-104999", "a.aof.zst")])
    with patch(_PATCH, side_effect=RuntimeError("down")):
        result = planner.precheck()
    assert result["exist"] is False
    assert any("无法向备份系统确认文件仍在" in err for err in result["errors"])


def test_build_skips_placeholder_task_ids():
    planner = _planner()
    planner.info = {"backup_identify": "SCHEDULED-1", "shards": [{"shard_value": "0-104999"}]}
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-104999", "a.aof.zst"), _record("105000-209999", "b.aof.zst")]
    )
    query = MagicMock(return_value=[_ok("task-a.aof.zst")])
    with patch(_PATCH, query):
        plan = planner.build(pack=False)
    assert any(item.is_placeholder for item in plan.items)
    assert query.call_args.args[0]["task_ids"] == ["task-a.aof.zst"]


def test_build_also_confirms_listed_binlog_task_ids():
    """When the plan includes binlog task_ids, query both full and binlog tasks."""
    planner = _planner()
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[dict(_record("0-104999", "a.aof.zst"), binlog_task_ids=["binlog-9"])]
    )
    query = MagicMock(side_effect=lambda params: [_ok(task_id) for task_id in params["task_ids"]])
    with patch(_PATCH, query):
        planner.build(pack=False)
    assert query.call_args.args[0]["task_ids"] == ["task-a.aof.zst", "binlog-9"]
