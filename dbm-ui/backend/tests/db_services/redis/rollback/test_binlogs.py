# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.binlogs import (
    binlog_fingerprint,
    binlog_index,
    index_segments,
    select_binlog_chain,
)
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.locator import BackupLocator, binlog_record
from backend.db_services.redis.rollback.shards import round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import RollbackPlan
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner

T0 = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
RECOVER_AT = T0 + timedelta(minutes=60)


def _binlog(index, minutes, ip="1.1.1.1", port=30000):
    begin = T0 + timedelta(minutes=minutes)
    name = "binlog-{}-{}-{:07d}-{}.log.zst".format(ip, port, index, begin.strftime("%Y%m%d%H%M%S"))
    return binlog_record(name, "binlog-task-{}".format(index), 10, ip, port, begin)


def _chain(*pairs):
    return [_binlog(index, minutes) for index, minutes in pairs]


FULL_CHAIN = ((1, -40), (2, -20), (3, 10), (4, 40), (5, 70), (6, 100))


def _indexes(chain):
    return [b["index"] for b in chain]


def test_binlog_index_parses_current_and_legacy_names():
    assert binlog_index("binlog-1.1.1.1-30000-0000386-20230420021655.log.zst") == 386
    assert binlog_index("/data/binlog-30000-0009936-20231228062236.log.lzo") == 9936
    assert binlog_index("binlog-1.1.1.1-30000-7-0003612-20230326232536.log.zst") is None
    assert binlog_index("3-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010203-9.tar") is None


def test_chain_runs_from_last_file_before_full_to_first_after_target():
    binlogs = _chain(*FULL_CHAIN)
    chain, gaps = select_binlog_chain(binlogs + binlogs[:2], T0, RECOVER_AT)
    assert _indexes(chain) == [2, 3, 4, 5]
    assert gaps is None


def test_missing_index_fails():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((1, -40), (2, -20), (3, 10), (5, 70)), T0, RECOVER_AT)
    assert "[4]" in exc.value.message
    assert "allow_binlog_nonconsecutive" in exc.value.message


def test_allowed_gap_returns_chain_and_gaps():
    chain, gaps = select_binlog_chain(_chain((1, -40), (2, -20), (3, 10), (5, 70)), T0, RECOVER_AT, True)
    assert _indexes(chain) == [2, 3, 5]
    assert gaps == {"missing_count": 1, "missing": [4]}


def test_allowed_gap_lists_only_the_first_ten_missing():
    _, gaps = select_binlog_chain(_chain((1, -40), (2, -20), (3, 10), (30, 70)), T0, RECOVER_AT, True)
    assert gaps == {"missing_count": 26, "missing": list(range(4, 14))}


def test_allowed_gap_still_rejects_missing_tail_and_duplicates():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((1, -40), (2, -20), (4, 10)), T0, RECOVER_AT, True)
    assert "断裂" in exc.value.message
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain(*FULL_CHAIN) + [_binlog(3, 20)], T0, RECOVER_AT, True)
    assert "重复" in exc.value.message
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((3, 10), (5, 70)), T0, RECOVER_AT, True)
    assert "全备开始前" in exc.value.message


def test_allowed_gap_still_rejects_index_reset_by_restart():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((7, -20), (8, 10), (1, 40), (2, 70)), T0, RECOVER_AT, True)
    assert "回退" in exc.value.message


def test_duplicate_index_fails():
    binlogs = _chain(*FULL_CHAIN) + [_binlog(3, 20)]
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(binlogs, T0, RECOVER_AT)
    assert "重复" in exc.value.message and "[3]" in exc.value.message


def test_fewer_than_two_files_fails():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((1, 0)), T0, T0)
    assert "少于 2" in exc.value.message


def test_replaced_instance_has_no_tail_and_breaks_the_chain():
    # The source instance stopped writing binlogs before the target time.
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((1, -40), (2, -20), (3, 10)), T0, RECOVER_AT)
    assert "断裂" in exc.value.message


def test_restarted_instance_resets_index_and_leaves_a_gap():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((7, -20), (8, 10), (1, 40), (2, 70)), T0, RECOVER_AT)
    assert "不连续" in exc.value.message


def test_no_binlog_before_full_fails():
    with pytest.raises(RollbackPlanError) as exc:
        select_binlog_chain(_chain((3, 10), (4, 70)), T0, RECOVER_AT)
    assert "全备开始前" in exc.value.message


def test_index_segments_reads_like_runs():
    assert index_segments([1000, 1001, 1003, 1004]) == "[1000-1001],[1003-1004]"
    assert index_segments([7, 5, 6, 9]) == "[5-7],[9]"
    assert index_segments([]) == ""
    assert index_segments(range(0, 30, 2), limit=3) == "[0],[2],[4],...(+12)"


def test_fingerprint_matches_the_actuator():
    # dbactuator rollback.BinlogFingerprint([]string{"a", "b"})
    assert binlog_fingerprint(["/x/a", "b"]) == "7e18f737311b2dc3b2f269dd78396b0351f14fb66efa879f768cb23181883c78"


def _locator():
    cluster = MagicMock()
    cluster.immute_domain = "ssd.example.db"
    return BackupLocator(cluster)


def test_locate_binlogs_reads_table_for_the_source_instance_only():
    rows = [
        SimpleNamespace(
            backup_file="/backup/binlog-1.1.1.1-30000-0000002-20260101004000.log.zst",
            backup_taskid="t2",
            backup_file_size=5,
            backup_host="1.1.1.1",
            backup_port=30000,
            backup_begin_time=T0 - timedelta(minutes=20),
        ),
        SimpleNamespace(
            backup_file="not-a-binlog.log",
            backup_taskid="t9",
            backup_file_size=5,
            backup_host="1.1.1.1",
            backup_port=30000,
            backup_begin_time=T0,
        ),
    ]
    locator = _locator()
    locator._esquery = MagicMock(return_value=[])
    with patch("backend.db_services.redis.rollback.locator.RedisBinlogResult") as model:
        model.objects.using.return_value.filter.return_value = rows
        records = locator.locate_binlogs("1.1.1.1", 30000, T0, RECOVER_AT)

    query = model.objects.using.return_value.filter.call_args.kwargs
    assert (query["backup_host"], query["backup_port"]) == ("1.1.1.1", 30000)
    assert query["backup_begin_time__gte"] < T0 and query["backup_begin_time__lte"] > RECOVER_AT
    assert [(r["task_id"], r["file_name"], r["index"]) for r in records] == [
        ("t2", "binlog-1.1.1.1-30000-0000002-20260101004000.log.zst", 2)
    ]


def test_locate_binlogs_reads_bklog_and_keeps_the_window():
    locator = _locator()
    logs = [
        {
            "backup_file": "binlog-1.1.1.1-30000-0000002-20260101004000.log.zst",
            "backup_taskid": "t2",
            "backup_file_size": 5,
            "server_ip": "1.1.1.1",
            "server_port": 30000,
            "start_time": "2026-01-01T08:40:00+08:00",
        },
        {
            "backup_file": "binlog-1.1.1.1-30000-0000001-20251231000000.log.zst",
            "backup_taskid": "t1",
            "backup_file_size": 5,
            "server_ip": "1.1.1.1",
            "server_port": 30000,
            "start_time": "2025-12-31T08:00:00+08:00",
        },
    ]
    locator._esquery = MagicMock(return_value=logs)
    with patch("backend.db_services.redis.rollback.locator.RedisBinlogResult") as model:
        model.objects.using.return_value.filter.return_value = []
        records = locator.locate_binlogs("1.1.1.1", 30000, T0, RECOVER_AT)

    assert locator._esquery.call_args.kwargs["collector"] == "redis_binlog_backup_result"
    assert "server_ip: 1.1.1.1 AND server_port: 30000" in locator._esquery.call_args.args[2]
    assert [r["task_id"] for r in records] == ["t2"]


@pytest.fixture
def backup_files_still_present():
    def _query(params):
        return [{"task_id": task_id, "status": 4, "expired": "0"} for task_id in params["task_ids"]]

    with patch(
        "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids", side_effect=_query
    ) as query:
        yield query


def _ssd_planner(binlogs, cluster_type=ClusterType.TwemproxyTendisSSDInstance.value, **info):
    cluster = MagicMock()
    cluster.id = 1
    cluster.immute_domain = "ssd.example.db"
    cluster.cluster_type = cluster_type
    cluster.bk_cloud_id = 0
    cluster.bk_biz_id = 3
    cluster.major_version = "TendisSSD-1.3"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    planner = RollbackPlanner(cluster, {"backup_identify": "SCHEDULED-1", **info})
    file_name = "3-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-010000-9.tar"
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[
            {
                "shard_value": "0-419999",
                "source_ip": "1.1.1.1",
                "server_port": 30000,
                "file_name": file_name,
                "task_id": "full-task",
                "size": 100,
                "backup_identify": "SCHEDULED-1",
                "backup_begin_time": T0.isoformat(),
                "backup_end_time": RECOVER_AT.isoformat(),
                "round_key": round_key_from_filename(file_name),
            }
        ]
    )
    planner.locator.locate_binlogs = MagicMock(return_value=binlogs)
    return planner


def test_ssd_plan_carries_the_chain_and_confirms_its_tasks(backup_files_still_present):
    plan = _ssd_planner(_chain(*FULL_CHAIN)).build(pack=False)

    item = plan.items[0]
    assert plan.tendis_type == ClusterType.TendisSSDInstance.value
    assert [b.index for b in item.binlog_files] == [2, 3, 4, 5]
    assert backup_files_still_present.call_args.args[0]["task_ids"] == ["full-task"] + [
        "binlog-task-{}".format(i) for i in (2, 3, 4, 5)
    ]
    detail = plan.to_rollback_detail()["shards"][0]
    assert detail["task_ids"] == ["full-task"]
    assert detail["binlog"] == {
        "count": 4,
        "first": item.binlog_files[0].file_name,
        "last": item.binlog_files[-1].file_name,
        "fingerprint": binlog_fingerprint([b.file_name for b in item.binlog_files]),
        "segments": "[2-5]",
    }


def test_ssd_broken_chain_blocks_precheck_and_build(backup_files_still_present):
    planner = _ssd_planner(_chain((1, -40), (2, -20), (3, 10)))
    result = planner.precheck()
    assert result["exist"] is False
    assert "0-419999" in result["shards"][0]["errors"][0] and "断裂" in result["shards"][0]["errors"][0]
    with pytest.raises(RollbackPlanError):
        planner.build(pack=False)


GAPPED_CHAIN = ((1, -40), (2, -20), (3, 10), (5, 70))


def test_gap_blocks_precheck_unless_allowed(backup_files_still_present):
    result = _ssd_planner(_chain(*GAPPED_CHAIN)).precheck()
    assert result["exist"] is False
    assert result["binlog_nonconsecutive"] is False
    assert "allow_binlog_nonconsecutive" in result["shards"][0]["errors"][0]


def test_allowed_gap_passes_precheck_with_warning(backup_files_still_present):
    result = _ssd_planner(_chain(*GAPPED_CHAIN), allow_binlog_nonconsecutive=True).precheck()
    assert result["exist"] is True
    assert result["binlog_nonconsecutive"] is True
    assert result["shards"][0]["binlog_gaps"] == {"missing_count": 1, "missing": [4]}
    assert any("0-419999" in warning and "[4]" in warning for warning in result["warnings"])


def test_allowed_gap_is_carried_by_the_plan_and_the_task_record(backup_files_still_present):
    plan = _ssd_planner(_chain(*GAPPED_CHAIN), allow_binlog_nonconsecutive=True).build(pack=False)
    assert plan.allow_binlog_nonconsecutive is True
    assert any("[4]" in warning for warning in plan.warnings)
    binlog = plan.to_rollback_detail()["shards"][0]["binlog"]
    assert binlog["gaps"] == {"missing_count": 1, "missing": [4]}
    assert binlog["segments"] == "[2-3],[5]"
    assert plan.items[0].actuator_instance()["binlog_segments"] == "[2-3],[5]"

    restored = RollbackPlan.from_dict(plan.to_dict())
    assert restored.allow_binlog_nonconsecutive is True
    assert restored.items[0].binlog_gaps == {"missing_count": 1, "missing": [4]}
    assert restored.to_rollback_detail() == plan.to_rollback_detail()


def test_contiguous_chain_records_no_gaps_key(backup_files_still_present):
    plan = _ssd_planner(_chain(*FULL_CHAIN), allow_binlog_nonconsecutive=True).build(pack=False)
    assert "gaps" not in plan.to_rollback_detail()["shards"][0]["binlog"]


def test_cache_cluster_skips_binlog_lookup(backup_files_still_present):
    planner = _ssd_planner([], cluster_type=ClusterType.TendisTwemproxyRedisInstance.value)
    plan = planner.build(pack=False)
    planner.locator.locate_binlogs.assert_not_called()
    assert plan.items[0].binlog_files == []
    assert "binlog" not in plan.to_rollback_detail()["shards"][0]


# --- by_identify with an explicit recovery_time_point -----------------------------


def test_ssd_identify_replays_binlogs_up_to_a_later_time(backup_files_still_present):
    target = RECOVER_AT + timedelta(minutes=30)
    planner = _ssd_planner(_chain(*FULL_CHAIN), recovery_time_point=target.isoformat())
    plan = planner.build(pack=False)

    assert plan.recover_at == target
    assert planner.locator.locate_binlogs.call_args.args[3] == target
    assert [b.index for b in plan.items[0].binlog_files] == [2, 3, 4, 5, 6]


def test_ssd_time_before_full_end_fails_without_binlog_lookup(backup_files_still_present):
    target = RECOVER_AT - timedelta(minutes=10)
    planner = _ssd_planner(_chain(*FULL_CHAIN), recovery_time_point=target.isoformat())
    result = planner.precheck()

    assert result["exist"] is False
    error = result["shards"][0]["errors"][0]
    assert "0-419999" in error and "早于" in error and "少于 2" not in error
    planner.locator.locate_binlogs.assert_not_called()
    with pytest.raises(RollbackPlanError):
        planner.build(pack=False)


def test_ssd_full_without_end_time_is_bounded_by_its_begin_time(backup_files_still_present):
    planner = _ssd_planner(_chain(*FULL_CHAIN), recovery_time_point=(T0 + timedelta(minutes=5)).isoformat())
    planner.locator.locate_full_by_identify.return_value[0]["backup_end_time"] = ""
    assert planner.precheck()["exist"] is True

    planner = _ssd_planner(_chain(*FULL_CHAIN), recovery_time_point=(T0 - timedelta(minutes=5)).isoformat())
    planner.locator.locate_full_by_identify.return_value[0]["backup_end_time"] = ""
    assert "早于" in planner.precheck()["shards"][0]["errors"][0]


def test_cache_identify_ignores_recovery_time_point(backup_files_still_present):
    planner = _ssd_planner(
        [],
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        recovery_time_point=(RECOVER_AT + timedelta(hours=1)).isoformat(),
    )
    plan = planner.build(pack=False)

    assert plan.recover_at == RECOVER_AT
    assert any("recovery_time_point" in warning for warning in plan.warnings)
    planner.locator.locate_binlogs.assert_not_called()


def test_invalid_recovery_time_point_is_a_plan_error():
    planner = _ssd_planner(_chain(*FULL_CHAIN), recovery_time_point="not-a-time")
    result = planner.precheck()

    assert result["exist"] is False
    assert any("recovery_time_point" in error for error in result["errors"])
    planner.locator.locate_full_by_identify.assert_not_called()
    planner.locator.locate_binlogs.assert_not_called()


# --- binlog lookups run a few shards at a time, results stay in shard order -------


def _ssd_multi_planner(shard_count, locate_binlogs, **info):
    planner = _ssd_planner([], **info)
    records = []
    for i in range(shard_count):
        port = 30000 + i
        file_name = "3-TENDISSSD-FULL-slave-1.1.1.1-{}-20260101-010000-9.tar".format(port)
        records.append(
            {
                "shard_value": "{}-{}".format(i * 1000, i * 1000 + 999),
                "source_ip": "1.1.1.1",
                "server_port": port,
                "file_name": file_name,
                "task_id": "full-task-{}".format(i),
                "size": 100,
                "backup_identify": "SCHEDULED-1",
                "backup_begin_time": T0.isoformat(),
                "backup_end_time": RECOVER_AT.isoformat(),
                "round_key": round_key_from_filename(file_name),
            }
        )
    planner.locator.locate_full_by_identify = MagicMock(return_value=records)
    planner.locator.locate_binlogs = locate_binlogs
    return planner


def test_binlog_lookups_are_bounded_and_results_keep_shard_order(backup_files_still_present):
    import threading
    import time

    from backend.db_services.redis.rollback.constants import BINLOG_LOCATE_CONCURRENCY

    lock, running, peak = threading.Lock(), [0], [0]

    def locate(source_ip, source_port, full_start, recover_at):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        # later ports answer first, so completion order is the reverse of shard order
        time.sleep(0.002 * (30012 - source_port))
        with lock:
            running[0] -= 1
        chain = GAPPED_CHAIN if source_port % 2 else FULL_CHAIN
        return [_binlog(index, minutes, port=source_port) for index, minutes in chain]

    planner = _ssd_multi_planner(12, locate, allow_binlog_nonconsecutive=True)
    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.connections") as conns:
        result = planner.precheck()

    assert 1 < peak[0] <= BINLOG_LOCATE_CONCURRENCY
    assert conns.close_all.call_count == 12
    shards = result["shards"]
    assert len(shards) == 12
    # warnings follow the shard list, not the order the lookups finished in
    # each shard got the chain of its own source instance: odd ports were given the gapped one
    assert [bool(s["binlog_gaps"]) for s in shards] == [bool(s["source_port"] % 2) for s in shards]
    gapped = [s["shard_value"] for s in shards if s["binlog_gaps"]]
    gap_warnings = [w for w in result["warnings"] if "allow_binlog_nonconsecutive" in w]
    assert [w.split(" ")[1] for w in gap_warnings] == gapped


def test_binlog_chain_errors_keep_shard_order(backup_files_still_present):
    def locate(source_ip, source_port, full_start, recover_at):
        return [_binlog(index, minutes, port=source_port) for index, minutes in GAPPED_CHAIN]

    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.connections"):
        result = _ssd_multi_planner(6, locate).precheck()
    assert result["exist"] is False
    assert [s["errors"][0].split(" ")[1] for s in result["shards"]] == [s["shard_value"] for s in result["shards"]]


def test_binlog_lookup_failure_still_closes_the_worker_connection(backup_files_still_present):
    locate = MagicMock(side_effect=RuntimeError("report_db down"))
    planner = _ssd_multi_planner(4, locate)
    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.connections") as conns:
        result = planner.precheck()
    assert result["exist"] is False
    # lookups not yet started are cancelled; every one that ran closed its connections
    assert locate.call_count >= 1
    assert conns.close_all.call_count == locate.call_count
