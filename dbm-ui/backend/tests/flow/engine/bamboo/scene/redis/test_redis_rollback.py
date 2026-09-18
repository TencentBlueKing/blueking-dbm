# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.constants import SWITCHED_SHARD_VALUE
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.shards import ShardRef, round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner


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


def test_shard_layout_allows_partial_coverage_with_warning():
    """设计稿：Twemproxy / Cache 允许只勾该批次里的部分分片。"""
    planner = _planner()
    warnings = planner._check_shard_layout(["0-104999"])
    assert warnings
    assert "未覆盖全部 slot" in warnings[0]


def test_shard_layout_rejects_overlapping_shards():
    planner = _planner()
    try:
        planner._check_shard_layout(["0-104999", "50000-209999"])
        assert False, "expected overlap error"
    except RollbackPlanError as exc:
        assert "重叠" in str(exc.message)


def test_shard_layout_rejects_unroutable_shard_for_twemproxy():
    planner = _planner()
    try:
        planner._check_shard_layout([SWITCHED_SHARD_VALUE])
        assert False, "expected unroutable shard error"
    except RollbackPlanError as exc:
        assert "Proxy 路由" in str(exc.message)


def test_shard_layout_skips_routing_check_for_single_instance():
    planner = _planner(ClusterType.TendisRedisInstance.value)
    assert planner._check_shard_layout([SWITCHED_SHARD_VALUE]) == []


def test_resolve_backup_shards_rejects_records_without_shard_value():
    planner = _planner()
    try:
        planner._resolve_backup_shards([_record("", "a.aof.zst")])
        assert False, "expected missing shard_value error"
    except RollbackPlanError as exc:
        assert "shard_value" in str(exc.message)


def test_historical_shard_absent_from_topology_still_builds():
    """扩缩容后历史分片已不在当前拓扑，仍按该批次当时的 shard 构造（临时 Proxy 路由依赖它）。"""
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
    """部分回档也要保证产物可访问：未勾选的分片起空进程，proxy 后端才有所指。"""
    plan = _partial_selection_planner().build(pack=False)

    placeholders = [item for item in plan.items if item.is_placeholder]
    assert [item.shard.shard_value for item in placeholders] == ["105000-209999"]
    assert placeholders[0].full_files == []
    assert placeholders[0].task_ids == []
    assert placeholders[0].download_bytes == 0
    assert any("空实例" in w for w in plan.warnings)


def test_placeholders_keep_proxy_routing_complete():
    """加上空实例后 slot 铺满，不再有未覆盖告警；每个 item 都有可路由的 shard。"""
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
    # 空实例不产生下载量，但要占一个端口
    assert plan.dest_hosts[0].ports == [30000, 30001]
    assert plan.dest_hosts[0].download_bytes == 1


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
    planner = _planner()
    refs = [ShardRef("0-104999", current_master="1.1.1.1:30000", current_slave="1.1.1.9:30000", resolvable=True)]
    planner.resolver.from_db_meta = MagicMock(return_value=refs)
    items = planner._build_rollback_items(refs, [_record("0-104999", "old.aof.zst", source_ip="3.3.3.3")])
    assert items[0].source_is_current is False
    assert items[0].source_ip == "3.3.3.3"


def test_identify_only_picks_latest_round():
    planner = _planner(backup_identify="SCHEDULED-1")
    selected = planner._apply_shard_selection(_two_rounds_same_identify())
    assert [r["file_name"] for r in selected] == ["new.aof.zst"]


def test_shard_selection_can_pick_older_round():
    planner = _planner(backup_identify="SCHEDULED-1", shards=[{"shard_value": "0-104999", "round_key": "old.aof.zst"}])
    selected = planner._apply_shard_selection(_two_rounds_same_identify())
    assert [r["file_name"] for r in selected] == ["old.aof.zst"]


def test_shard_selection_without_round_key_takes_latest():
    planner = _planner(backup_identify="SCHEDULED-1", shards=[{"shard_value": "0-104999"}])
    selected = planner._apply_shard_selection(_two_rounds_same_identify())
    assert [r["file_name"] for r in selected] == ["new.aof.zst"]


def test_shard_selection_rejects_shard_missing_from_batch():
    planner = _planner(backup_identify="SCHEDULED-1", shards=[{"shard_value": "999-1000"}])
    try:
        planner._apply_shard_selection(_two_rounds_same_identify())
        assert False, "expected missing shard error"
    except RollbackPlanError as exc:
        assert "没有成功全备" in str(exc.message)


def test_shard_selection_rejects_unknown_round_key():
    planner = _planner(
        backup_identify="SCHEDULED-1", shards=[{"shard_value": "0-104999", "round_key": "nope.aof.zst"}]
    )
    try:
        planner._apply_shard_selection(_two_rounds_same_identify())
        assert False, "expected unknown round error"
    except RollbackPlanError as exc:
        assert "找不到轮次" in str(exc.message)


def test_shard_selection_rejects_duplicates():
    planner = _planner(
        backup_identify="SCHEDULED-1",
        shards=[{"shard_value": "0-104999"}, {"shard_value": "0-104999", "round_key": "old.aof.zst"}],
    )
    try:
        planner._apply_shard_selection(_two_rounds_same_identify())
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
            # 缺 split.001，这一轮不齐
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
