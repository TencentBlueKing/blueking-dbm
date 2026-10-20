# -*- coding: utf-8 -*-
import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.binlogs import binlog_fingerprint, plus_binlog_position, select_kvstore_chains
from backend.db_services.redis.rollback.constants import ROLLBACK_CLUSTER_TYPES
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.locator import binlog_record
from backend.db_services.redis.rollback.shards import ShardRef, round_key_from_filename, slot_ranges
from backend.flow.engine.bamboo.scene.redis.redis_rollback import flow as rollback_flow
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    BinlogRef,
    FullBackupRef,
    RollbackItem,
    RollbackPlan,
    host_disk_needs,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner
from backend.flow.utils.redis.redis_act_playload import RedisActPayload

PLUS = ClusterType.TendisPredixyTendisplusCluster.value
REDIS_CLUSTER = ClusterType.TendisPredixyRedisCluster.value
T0 = datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
RECOVER_AT = T0 + timedelta(minutes=60)
SLOT_SHARDS = ["0-5460", "5461-10922", "10923-16383"]
CHAIN = ((1, -40), (2, -20), (3, 10), (4, 40), (5, 70))
GB = 1024**3


def _plus_binlog(kvstore, index, minutes, port=30000):
    begin = T0 + timedelta(minutes=minutes)
    name = "binlog-1.1.1.1-{}-{}-{:07d}-{}.log.zst".format(port, kvstore, index, begin.strftime("%Y%m%d%H%M%S"))
    return binlog_record(name, "binlog-{}-{}-{}".format(port, kvstore, index), 10, "1.1.1.1", port, begin, plus=True)


def _chains(port=30000, kvstores=2, chain=CHAIN, override=None):
    """Every kvstore gets ``chain`` unless ``override`` gives it another one."""
    override = override or {}
    return [
        _plus_binlog(kvstore, index, minutes, port)
        for kvstore in range(kvstores)
        for index, minutes in override.get(kvstore, chain)
    ]


def _full(shard_value, port):
    file_name = "3-TENDISPLUS-FULL-slave-1.1.1.1-{}-20260101-010000.tar".format(port)
    return {
        "shard_value": shard_value,
        "source_ip": "1.1.1.1",
        "server_port": port,
        "file_name": file_name,
        "task_id": "full-{}".format(port),
        "size": GB,
        "backup_identify": "SCHEDULED-1",
        "backup_begin_time": T0.isoformat(),
        "backup_end_time": RECOVER_AT.isoformat(),
        "round_key": round_key_from_filename(file_name),
    }


def _planner(cluster_type=PLUS, shards=SLOT_SHARDS, binlogs=None, **info):
    cluster = MagicMock(id=1, immute_domain="plus.example.db", cluster_type=cluster_type, bk_cloud_id=0, bk_biz_id=3)
    cluster.major_version = "Tendisplus-2.8"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    planner = RollbackPlanner(cluster, {"backup_identify": "SCHEDULED-1", **info})
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_full(shard, 30000 + i) for i, shard in enumerate(shards)]
    )
    binlogs = binlogs or (lambda port: _chains(port))
    planner.locator.locate_binlogs = MagicMock(side_effect=lambda ip, port, start, end: binlogs(port))
    return planner


@pytest.fixture(autouse=True)
def backup_files_still_present():
    def _query(params):
        return [{"task_id": task_id, "status": 4, "expired": "0"} for task_id in params["task_ids"]]

    with patch(
        "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids", side_effect=_query
    ) as query:
        yield query


@pytest.fixture(autouse=True)
def kvstorecount():
    with patch(
        "backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.DBConfigApi.query_conf_item",
        return_value={"content": {"kvstorecount": "2"}},
    ) as query:
        yield query


# --- names, slots ----------------------------------------------------------------------


def test_plus_binlog_names_carry_kvstore_and_index():
    assert plus_binlog_position("binlog-1.1.1.1-30000-7-0003612-20230326232536.log.zst") == (7, 3612)
    assert plus_binlog_position("/x/binlog-30000-7-0003612-20230326232536.log.zst") == (7, 3612)
    assert plus_binlog_position("binlog-1.1.1.1-30000-0000386-20230420021655.log.zst") is None

    name = "binlog-1.1.1.1-30000-7-0003612-20230326232536.log.zst"
    plus = binlog_record(name, "t", 1, "1.1.1.1", 30000, T0, plus=True)
    assert (plus["kvstore"], plus["index"]) == (7, 3612)
    assert binlog_record(name, "t", 1, "1.1.1.1", 30000, T0)["index"] is None


def test_slot_ranges_merge_and_drop_migration_markers():
    assert slot_ranges("10651-10923 1365-1637 1638") == "1365-1638,10651-10923"
    assert slot_ranges("0-100 [101->-abcdef]") == "0-100"
    assert slot_ranges("7") == "7"
    assert slot_ranges("switched-0") == ""


# --- 3.5 / 3.14 Gate C per kvstore -----------------------------------------------------


def test_every_kvstore_gets_its_chain():
    chain, gaps, errors = select_kvstore_chains(_chains(), 2, T0, RECOVER_AT)
    assert errors == [] and gaps is None
    assert [(b["kvstore"], b["index"]) for b in chain] == [
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
    ]


def test_kvstore_without_binlogs_names_the_kvstore_and_side():
    _, _, errors = select_kvstore_chains(_chains(kvstores=1), 2, T0, RECOVER_AT)
    assert len(errors) == 1
    assert errors[0].startswith("kvstore 1:") and "左边界" in errors[0]


def test_source_with_more_kvstores_than_the_temp_instance_is_rejected():
    _, _, errors = select_kvstore_chains(_chains(kvstores=3), 2, T0, RECOVER_AT)
    assert errors == ["源实例有 kvstore [2]，多于临时实例的 2 个 kvstore"]


def test_allowed_gaps_are_recorded_per_kvstore():
    gapped = {1: ((1, -40), (2, -20), (3, 10), (5, 70))}
    _, _, errors = select_kvstore_chains(_chains(override=gapped), 2, T0, RECOVER_AT)
    assert "kvstore 1" in errors[0] and "allow_binlog_nonconsecutive" in errors[0]

    chain, gaps, errors = select_kvstore_chains(_chains(override=gapped), 2, T0, RECOVER_AT, True)
    assert errors == []
    assert gaps == {"missing_count": 1, "kvstores": {"1": {"missing_count": 1, "missing": [4]}}}


def test_missing_right_boundary_names_instance_kvstore_side_and_chain_ends():
    no_tail = {1: ((1, -40), (2, -20), (3, 10))}
    planner = _planner(binlogs=lambda port: _chains(port, override=no_tail if port == 30001 else None))
    result = planner.precheck()

    assert result["exist"] is False
    errors = {shard["shard_value"]: shard["errors"] for shard in result["shards"]}
    assert errors["0-5460"] == [] and errors["10923-16383"] == []
    assert len(errors["5461-10922"]) == 1
    error = errors["5461-10922"][0]
    assert "5461-10922" in error and "1.1.1.1:30001" in error and "kvstore 1" in error and "右边界" in error
    assert "binlog-1.1.1.1-30001-1-0000001-" in error and "binlog-1.1.1.1-30001-1-0000003-" in error
    with pytest.raises(RollbackPlanError):
        planner.build(pack=False)


def test_kvstore_count_comes_from_the_cluster_config(kvstorecount):
    kvstorecount.return_value = {"content": {"kvstorecount": "3"}}
    result = _planner().precheck()
    assert result["exist"] is False
    assert all("kvstore 2" in shard["errors"][0] for shard in result["shards"])
    params = kvstorecount.call_args.kwargs["params"]
    assert (params["level_value"], params["conf_file"], params["namespace"]) == (
        "plus.example.db",
        "Tendisplus-2.8",
        PLUS,
    )


def test_unknown_kvstore_count_fails_without_binlog_lookup(kvstorecount):
    kvstorecount.side_effect = RuntimeError("dbconfig down")
    planner = _planner()
    result = planner.precheck()
    assert result["exist"] is False
    assert any("kvstorecount" in error for error in result["errors"])
    planner.locator.locate_binlogs.assert_not_called()


# --- 3.4 / 3.7 the plan for cluster protocol --------------------------------------------


def test_plus_plan_sends_slots_and_a_digest_per_kvstore(backup_files_still_present):
    plan = _planner().build(pack=False)
    assert plan.tendis_type == ClusterType.TendisplusInstance.value
    assert plan.is_plus and plan.is_cluster_protocol

    item = plan.items[0]
    instance = item.actuator_instance(plus=True, cluster_protocol=True)
    assert instance["slots"] == "0-5460"
    assert instance["binlog_count"] == 0 and instance["binlog_fingerprint"] == ""
    names = {kv: [b.file_name for b in chain] for kv, chain in item.kvstore_binlogs.items()}
    assert instance["kvstore_binlogs"] == [
        {
            "kvstore": kv,
            "binlog_range": {"first_index": 2, "last_index": 5},
            "binlog_count": 4,
            "binlog_fingerprint": binlog_fingerprint(names[kv]),
            "binlog_segments": "[2-5]",
        }
        for kv in (0, 1)
    ]
    task_ids = backup_files_still_present.call_args.args[0]["task_ids"]
    assert "full-30000" in task_ids and "binlog-30000-1-5" in task_ids

    detail = plan.to_rollback_detail()["shards"][0]["binlog"]
    assert detail["count"] == 8 and set(detail["kvstores"]) == {"0", "1"}
    assert detail["kvstores"]["1"]["segments"] == "[2-5]"

    restored = RollbackPlan.from_dict(plan.to_dict())
    assert [b.kvstore for b in restored.items[0].binlog_files] == [b.kvstore for b in item.binlog_files]


def test_partial_cluster_selection_fills_the_other_slots_with_placeholders(backup_files_still_present):
    planner = _planner(shard_values=[SLOT_SHARDS[0]])
    result = planner.precheck()
    assert result["exist"] is True
    assert any("slot" in w and "Proxy" not in w for w in result["warnings"] if "未勾选" in w)
    plan = planner.build(pack=False)

    placeholders = [item for item in plan.items if item.is_placeholder]
    assert [item.shard.shard_value for item in placeholders] == SLOT_SHARDS[1:]
    assert all(not item.full_files and not item.binlog_files for item in placeholders)
    # only the selected shard is downloaded, confirmed and chained
    for call in backup_files_still_present.call_args_list:
        assert all("30001" not in t and "30002" not in t for t in call.args[0]["task_ids"])
    assert {call.args[1] for call in planner.locator.locate_binlogs.call_args_list} == {30000}
    assert [node["slots"] for node in plan.cluster_nodes()] == SLOT_SHARDS


def test_batch_layout_missing_slots_cannot_form_a_cluster():
    planner = _planner(cluster_type=REDIS_CLUSTER, shards=SLOT_SHARDS[:2])
    result = planner.precheck()
    assert result["exist"] is False
    assert any("10923-16383" in error and "16384" in error for error in result["errors"])
    with pytest.raises(RollbackPlanError):
        planner.build(pack=False)


def test_cluster_shard_value_must_parse_to_slots():
    result = _planner(cluster_type=REDIS_CLUSTER, shards=["switched-0"]).precheck()
    assert result["exist"] is False
    assert "slot" in result["shards"][0]["errors"][0]


def test_redis_cluster_restores_without_binlogs_and_checks_memory():
    assert {PLUS, REDIS_CLUSTER} <= set(ROLLBACK_CLUSTER_TYPES)
    planner = _planner(cluster_type=REDIS_CLUSTER, resource_spec={"redis": {"id": 9, "count": 1}})
    planner._spec = MagicMock(return_value=SimpleNamespace(mem={"min": 5}, cpu={"min": 16}))
    result = planner.precheck()

    planner.locator.locate_binlogs.assert_not_called()
    assert result["exist"] is False
    assert any("内存" in error for error in result["errors"])
    planner._spec.return_value = SimpleNamespace(mem={"min": 64}, cpu={"min": 16})
    plan = planner.build(pack=False)
    assert plan.tendis_type == ClusterType.RedisInstance.value
    assert not plan.is_plus and plan.is_cluster_protocol


# --- 3.10 formation node ---------------------------------------------------------------


def _item(shard, dest_ip, dest_port, placeholder=False, binlogs=()):
    full = FullBackupRef("f", "a.tar", 10, "1.1.1.1", 30000, shard, "SCHEDULED-1", "", "", "a.tar")
    return RollbackItem(
        shard=ShardRef(shard),
        source_ip="1.1.1.1",
        source_port=30000,
        source_is_current=True,
        dest_ip=dest_ip,
        dest_port=dest_port,
        full_files=[] if placeholder else [full],
        binlog_files=[
            BinlogRef("b", name, 5, "1.1.1.1", 30000, index=index, kvstore=kvstore) for kvstore, index, name in binlogs
        ],
        is_placeholder=placeholder,
    )


def _plan(cluster_type=PLUS):
    return RollbackPlan(
        cluster_id=1,
        immute_domain="plus.example.db",
        cluster_type=cluster_type,
        tendis_type=ClusterType.TendisplusInstance.value,
        bk_cloud_id=0,
        bk_biz_id=3,
        db_version="Tendisplus-2.8",
        proxy_port=50000,
        items=[
            _item("0-8191", "2.2.2.2", 30000),
            _item("8192-16383", "3.3.3.3", 30000, placeholder=True),
        ],
    )


def test_form_cluster_payload_lists_every_instance_with_its_slots():
    builder = RedisActPayload.__new__(RedisActPayload)
    with patch.object(RollbackPlan, "load", return_value=_plan()):
        payload = builder.redis_rollback_form_cluster_payload(params={"plan_id": 7, "dest_ip": "2.2.2.2"})
    assert payload["action"] == "redis_rollback_form_cluster"
    assert payload["payload"] == {
        "dest_ip": "2.2.2.2",
        "nodes": [
            {"ip": "2.2.2.2", "port": 30000, "slots": "0-8191"},
            {"ip": "3.3.3.3", "port": 30000, "slots": "8192-16383"},
        ],
    }
    assert "password" not in str(payload)


def test_cluster_is_formed_once_after_restore_and_before_the_proxy():
    source = inspect.getsource(rollback_flow.RedisRollbackFlow.build_cluster_rollback)
    assert "if plan.is_cluster_protocol:" in source
    assert source.index("redis_rollback_payload") < source.index("_add_form_cluster_act")
    assert source.index("_add_form_cluster_act") < source.index("_deploy_proxy")
    form = inspect.getsource(rollback_flow.RedisRollbackFlow._add_form_cluster_act)
    assert "redis_rollback_form_cluster_payload" in form


# --- disk peaks for Tendisplus ---------------------------------------------------------


def test_plus_disks_hold_one_decompressed_binlog_per_replaying_kvstore():
    binlogs = [(kv, index, "binlog-{}-{}.log.zst".format(kv, index)) for kv in (0, 1) for index in (1, 2)]
    items = [_item("0-8191", "2.2.2.2", 30000, binlogs=binlogs), _item("8192-16383", "2.2.2.2", 30001, True)]
    # a.tar 10 plus four 5-byte binlogs downloaded; each decompresses to 15
    assert host_disk_needs(items, False, cpu=4, max_concurrency=0, is_plus=True) == (30 + 2 * 15, 10 + 4 * 15)
    assert host_disk_needs(items, False, cpu=2, max_concurrency=0, is_plus=True) == (30 + 15, 10 + 4 * 15)
    assert host_disk_needs(items, False, cpu=4, max_concurrency=1, is_plus=True) == (30 + 15, 10 + 4 * 15)
