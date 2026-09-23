# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import SWITCHED_SHARD_VALUE
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.shards import ShardRef, round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner


@pytest.fixture(autouse=True)
def backup_files_still_present():
    """Existing plan tests assume the chosen files are still in the backup system."""

    def _query(params):
        return [{"task_id": task_id, "status": 4, "expired": "0"} for task_id in params["task_ids"]]

    with patch(
        "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids",
        side_effect=_query,
    ):
        yield


def _planner(cluster_type=ClusterType.TendisTwemproxyRedisInstance.value, **info):
    cluster = MagicMock()
    cluster.id = 1
    cluster.immute_domain = "cache.example.db"
    cluster.cluster_type = cluster_type
    cluster.bk_cloud_id = 0
    cluster.bk_biz_id = 3
    cluster.major_version = "Redis-6"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    return RollbackPlanner(cluster, info or {"backup_identify": "SCHEDULED-1"})


def _record(shard_value, file_name, source_ip="1.1.1.9", server_port=30000, hour="01", identify="SCHEDULED-1"):
    return {
        "shard_value": shard_value,
        "source_ip": source_ip,
        "server_port": server_port,
        "file_name": file_name,
        "task_id": "task-{}".format(file_name),
        "size": 1,
        "backup_identify": identify,
        "backup_begin_time": "2026-01-01T{}:00:00+00:00".format(hour),
        "backup_end_time": "2026-01-01T{}:01:00+00:00".format(hour),
        "round_key": round_key_from_filename(file_name),
    }


def _two_rounds_same_identify():
    return [
        _record("0-104999", "old.aof.zst", hour="01"),
        _record("0-104999", "new.aof.zst", hour="02"),
    ]


def test_non_cache_rejected():
    planner = _planner(ClusterType.TwemproxyTendisSSDInstance.value)
    try:
        planner.build(pack=False)
        assert False, "expected non-cache error"
    except RollbackPlanError as exc:
        assert "REDIS_DATA_STRUCTURE" in str(exc.message)


def _planner_with(records, shards=None, cluster_type=ClusterType.TendisTwemproxyRedisInstance.value):
    info = {"backup_identify": "SCHEDULED-1"}
    if shards is not None:
        info["shards"] = shards
    planner = _planner(cluster_type, **info)
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=records)
    return planner


def test_partial_coverage_only_warns_and_precheck_agrees():
    """Coverage gaps exist only when the batch itself does not cover all slots; both endpoints must agree."""
    planner = _planner_with([_record("0-104999", "a.aof.zst")])

    result = planner.precheck()
    plan = planner.build(pack=False)

    assert result["exist"] is True
    assert any("未覆盖全部 slot" in w for w in result["warnings"])
    assert any("未覆盖全部 slot" in w for w in plan.warnings)


def test_partial_selection_coverage_verdict_is_identical_in_precheck_and_build():
    """Partial selection fills unselected slots with placeholders; precheck and build must both pass."""
    records = [_record("0-209999", "a.aof.zst"), _record("210000-419999", "b.aof.zst")]
    planner = _planner_with(records, shards=[{"shard_value": "0-209999"}])

    result = planner.precheck()
    plan = planner.build(pack=False)

    assert result["exist"] is True
    assert not any("未覆盖全部 slot" in w for w in result["warnings"])
    assert not any("未覆盖全部 slot" in w for w in plan.warnings)


def test_overlapping_shards_rejected_by_both_entry_points():
    planner = _planner_with([_record("0-104999", "a.aof.zst"), _record("50000-209999", "b.aof.zst")])

    result = planner.precheck()
    assert result["exist"] is False
    assert any("重叠" in err for err in result["errors"])

    try:
        planner.build(pack=False)
        assert False, "expected overlap error"
    except RollbackPlanError as exc:
        assert "重叠" in str(exc.message)


def test_unroutable_shard_rejected_for_twemproxy():
    planner = _planner_with([_record(SWITCHED_SHARD_VALUE, "a.aof.zst")])
    try:
        planner.build(pack=False)
        assert False, "expected unroutable shard error"
    except RollbackPlanError as exc:
        assert "Proxy 路由" in str(exc.message)


def test_unroutable_shard_allowed_for_single_instance():
    """Single-instance has no twemproxy routes to generate; switched-0 downgrades without rejecting."""
    planner = _planner_with(
        [_record(SWITCHED_SHARD_VALUE, "a.aof.zst")], cluster_type=ClusterType.TendisRedisInstance.value
    )

    plan = planner.build(pack=False)

    assert [item.shard.shard_value for item in plan.items] == [SWITCHED_SHARD_VALUE]
    assert plan.shard_keyed is False


def test_record_without_shard_value_fails_the_shard():
    planner = _planner_with([_record("", "a.aof.zst")])
    try:
        planner.build(pack=False)
        assert False, "expected missing shard_value error"
    except RollbackPlanError as exc:
        assert "shard_value" in str(exc.message)


def test_host_count_rule_lives_only_in_the_planner():
    """Host count constraints are evaluated once by planner rather than recount by serializer."""
    planner = _planner_with([_record("0-104999", "a.aof.zst")])
    planner.info["resource_spec"] = {"redis": {"count": 3}}

    result = planner.precheck()
    assert any("待构造分片数" in err for err in result["errors"])

    try:
        planner.build(pack=False)
        assert False, "expected host count error"
    except RollbackPlanError as exc:
        assert "待构造分片数" in str(exc.message)


def test_build_reports_every_problem_at_once():
    """build combines all validation errors instead of stopping at the first failure."""
    planner = _planner_with(
        [
            _record("0-104999", "a.aof.zst.split.000"),
            _record("0-104999", "a.aof.zst.split.002"),
            _record("105000-209999", "b.aof.zst", identify="OTHER-1"),
            _record("105000-209999", "b.aof.zst", identify="SCHEDULED-1"),
        ]
    )
    try:
        planner.build(pack=False)
        assert False, "expected aggregated error"
    except RollbackPlanError as exc:
        assert "分卷不齐全" in str(exc.message)
        assert "跨 identify" in str(exc.message)


def test_historical_shard_absent_from_topology_still_builds():
    """After resharding, historical shards outside current topology are still restored based on batch shards."""
    planner = _planner()
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=[_record("0-104999", "a.aof.zst")])

    plan = planner.build(pack=False)

    assert [item.shard.shard_value for item in plan.items] == ["0-104999"]
    assert plan.items[0].shard.current_master is None
    assert plan.topology_changed is True
    assert any("不在当前拓扑" in w for w in plan.warnings)


def _partial_selection_planner():
    planner = _planner(shards=[{"shard_value": "0-104999"}], backup_identify="SCHEDULED-1")
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-104999", "a.aof.zst"), _record("105000-209999", "b.aof.zst")]
    )
    return planner


def test_partial_shards_do_not_block_build():
    plan = _partial_selection_planner().build(pack=False)

    restored = [item.shard.shard_value for item in plan.items if not item.is_placeholder]
    assert restored == ["0-104999"]
    assert plan.scope == "instances"


def test_unselected_shard_gets_empty_instance():
    """Partial rollback keeps temp cluster accessible by launching empty placeholder instances."""
    plan = _partial_selection_planner().build(pack=False)

    placeholders = [item for item in plan.items if item.is_placeholder]
    assert [item.shard.shard_value for item in placeholders] == ["105000-209999"]
    assert placeholders[0].full_files == []
    assert placeholders[0].task_ids == []
    assert placeholders[0].download_bytes == 0
    assert any("空实例" in w for w in plan.warnings)


def test_placeholders_keep_proxy_routing_complete():
    """Placeholders fill slot coverage so there is no gap warning and all items have routable shards."""
    planner = _planner(shards=[{"shard_value": "0-209999"}], backup_identify="SCHEDULED-1")
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-209999", "a.aof.zst"), _record("210000-419999", "b.aof.zst")]
    )

    plan = planner.build(pack=False)

    assert sorted(item.shard.shard_value for item in plan.items) == ["0-209999", "210000-419999"]
    assert all(item.shard.shard_value for item in plan.items)
    assert not any("未覆盖全部 slot" in w for w in plan.warnings)


def test_placeholders_get_ports_and_real_shards_packed_first():
    planner = _planner(shards=[{"shard_value": "0-209999"}], backup_identify="SCHEDULED-1")
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-209999", "a.aof.zst"), _record("210000-419999", "b.aof.zst")]
    )

    plan = planner.build(dest_ips=["2.2.2.2"], pack=True)

    assert [item.dest_port for item in plan.items] == [30000, 30001]
    assert plan.items[0].is_placeholder is False
    assert plan.items[1].is_placeholder is True
    # Placeholders require a port but generate no download bytes.
    assert plan.dest_hosts[0].ports == [30000, 30001]
    assert plan.dest_hosts[0].download_bytes == 1


def _sized_records(sizes):
    records = []
    for index, size in enumerate(sizes):
        record = _record(
            "{}-{}".format(index * 1000, index * 1000 + 999), "f{}.aof.zst".format(index), server_port=30000 + index
        )
        record["size"] = size
        records.append(record)
    return records


def test_every_host_gets_real_work_when_placeholders_outnumber_hosts():
    records = _sized_records([1] * 8)
    selected = [{"shard_value": r["shard_value"]} for r in records[:4]]
    plan = _planner_with(records, shards=selected).build(dest_ips=["2.2.2.2", "3.3.3.3"], pack=True)

    for ip in ("2.2.2.2", "3.3.3.3"):
        host_items = [item for item in plan.items if item.dest_ip == ip]
        assert sum(1 for item in host_items if not item.is_placeholder) == 2
        assert len(host_items) == 4
        assert [item.dest_port for item in host_items] == [30000, 30001, 30002, 30003]
        assert host_items[0].is_placeholder is False


def test_packing_balances_download_bytes():
    plan = _planner_with(_sized_records([100, 60, 50, 40, 30, 20])).build(dest_ips=["2.2.2.2", "3.3.3.3"], pack=True)

    loads = sorted(host.download_bytes for host in plan.dest_hosts)
    assert loads == [140, 160]
    assert sorted(host.unpacked_bytes for host in plan.dest_hosts) == [140 * 3, 160 * 3]
    assert sum(len(host.ports) for host in plan.dest_hosts) == 6


def test_pack_dest_hosts_caps_by_restored_shards_not_placeholders():
    planner = _planner(shards=[{"shard_value": "0-209999"}], backup_identify="SCHEDULED-1")
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-209999", "a.aof.zst"), _record("210000-419999", "b.aof.zst")]
    )

    try:
        planner.build(dest_ips=["2.2.2.2", "3.3.3.3"], pack=True)
        assert False, "expected host count error"
    except RollbackPlanError as exc:
        assert "待构造分片数" in str(exc.message)


def test_source_not_current_is_annotation_only():
    refs = [ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True)]
    planner = _planner_with([_record("0-104999", "old.aof.zst", source_ip="3.3.3.3")])
    planner.resolver.from_db_meta = MagicMock(return_value=refs)

    plan = planner.build(pack=False)

    assert plan.items[0].source_is_current is False
    assert plan.items[0].source_ip == "3.3.3.3"
    assert plan.topology_changed is True


def test_identify_only_picks_latest_round():
    plan = _planner_with(_two_rounds_same_identify()).build(pack=False)
    assert [f.file_name for f in plan.items[0].full_files] == ["new.aof.zst"]


def test_shard_selection_can_pick_older_round():
    planner = _planner_with(
        _two_rounds_same_identify(), shards=[{"shard_value": "0-104999", "round_key": "old.aof.zst"}]
    )
    plan = planner.build(pack=False)
    assert [f.file_name for f in plan.items[0].full_files] == ["old.aof.zst"]


def test_shard_selection_without_round_key_takes_latest():
    planner = _planner_with(_two_rounds_same_identify(), shards=[{"shard_value": "0-104999"}])
    plan = planner.build(pack=False)
    assert [f.file_name for f in plan.items[0].full_files] == ["new.aof.zst"]


def test_shard_selection_rejects_shard_missing_from_batch():
    planner = _planner_with(_two_rounds_same_identify(), shards=[{"shard_value": "999-1000"}])
    try:
        planner.build(pack=False)
        assert False, "expected missing shard error"
    except RollbackPlanError as exc:
        assert "没有成功全备" in str(exc.message)


def test_shard_selection_rejects_unknown_round_key():
    planner = _planner_with(
        _two_rounds_same_identify(), shards=[{"shard_value": "0-104999", "round_key": "nope.aof.zst"}]
    )
    try:
        planner.build(pack=False)
        assert False, "expected unknown round error"
    except RollbackPlanError as exc:
        assert "找不到轮次" in str(exc.message)


def test_shard_selection_rejects_duplicates():
    planner = _planner_with(
        _two_rounds_same_identify(),
        shards=[{"shard_value": "0-104999"}, {"shard_value": "0-104999", "round_key": "old.aof.zst"}],
    )
    try:
        planner.build(pack=False)
        assert False, "expected duplicate shard error"
    except RollbackPlanError as exc:
        assert "重复勾选" in str(exc.message)


def test_by_task_id_cross_identify_fails():
    planner = _planner()
    planner.info = {"backup_task_ids": ["t1", "t2"]}
    planner.locator.locate_full_by_task_ids = MagicMock(
        return_value=[
            {"task_id": "t1", "backup_identify": "A", "shard_value": "0-1"},
            {"task_id": "t2", "backup_identify": "B", "shard_value": "2-3"},
        ]
    )
    try:
        planner._select_records("by_task_id")
        assert False, "expected cross identify error"
    except RollbackPlanError as exc:
        assert "跨 identify" in str(exc.message)


def test_planner_requires_select_fields():
    planner = _planner()
    planner.info = {}
    try:
        planner.build(pack=False)
        assert False, "expected missing select fields"
    except RollbackPlanError as exc:
        assert "backup_identify" in str(exc.message)


def test_precheck_reports_every_shard_not_just_the_first():
    planner = _planner(
        backup_identify="SCHEDULED-1",
        shards=[{"shard_value": "0-104999"}, {"shard_value": "105000-209999"}],
    )
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[
            # Missing split.001 marks this round incomplete.
            _record("0-104999", "a.aof.zst.split.000"),
            _record("0-104999", "a.aof.zst.split.002"),
            _record("105000-209999", "b.aof.zst"),
        ]
    )

    result = planner.precheck()

    assert [s["shard_value"] for s in result["shards"]] == ["0-104999", "105000-209999"]
    assert result["shards"][0]["ok"] is False
    assert "分卷不齐全" in result["shards"][0]["errors"][0]
    assert result["shards"][1]["ok"] is True
    assert result["exist"] is False


def test_precheck_passes_and_flags_topology_drift():
    planner = _planner(backup_identify="SCHEDULED-1")
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(return_value=[_record("0-104999", "a.aof.zst")])

    result = planner.precheck()

    assert result["exist"] is True
    assert result["shards"][0]["round_key"] == "a.aof.zst"
    assert result["shards"][0]["in_current_topology"] is False
    assert any("不在当前拓扑" in w for w in result["warnings"])


def test_precheck_reports_overlap():
    planner = _planner(
        backup_identify="SCHEDULED-1",
        shards=[{"shard_value": "0-104999"}, {"shard_value": "50000-209999"}],
    )
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record("0-104999", "a.aof.zst"), _record("50000-209999", "b.aof.zst")]
    )

    result = planner.precheck()

    assert result["exist"] is False
    assert any("重叠" in err for err in result["errors"])


def test_precheck_returns_business_error_without_raising():
    planner = _planner(backup_identify="MISSING")
    planner.locator.locate_full_by_identify = MagicMock(return_value=[])

    result = planner.precheck()

    assert result["exist"] is False
    assert result["shards"] == []
    assert any("backup_identify" in err for err in result["errors"])


def test_precheck_swallows_unexpected_error_and_logs():
    secret = "SECRET_PATH_/data/mysql/xxx.sql"
    planner = _planner(backup_identify="SCHEDULED-1")
    planner.locator.locate_full_by_identify = MagicMock(side_effect=RuntimeError(secret))

    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.logger") as log:
        result = planner.precheck()

    assert result["exist"] is False
    assert result["shards"] == []
    assert len(result["errors"]) == 1
    assert secret not in result["errors"][0]
    assert "回档预检失败" in result["errors"][0]
    log.exception.assert_called_once()
