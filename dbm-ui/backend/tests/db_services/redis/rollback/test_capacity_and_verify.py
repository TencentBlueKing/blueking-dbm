# -*- coding: utf-8 -*-
import ast
import base64
import hashlib
import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.credentials import rollback_temp_password, with_temp_passwords
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.shards import ShardRef, round_key_from_filename
from backend.flow.engine.bamboo.scene.redis.redis_rollback import flow as rollback_flow
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    BinlogRef,
    FullBackupRef,
    RollbackItem,
    RollbackPlan,
    host_disk_needs,
    load_memory,
    rollback_manifest,
    stage_slots,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner, balance_hosts
from backend.flow.plugins.components.collections.redis.redis_rollback import RedisRollbackDiskPrecheckService
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

GB = 1024**3
SHARDS = ["0-104999", "105000-209999", "210000-314999", "315000-419999"]


@pytest.fixture(autouse=True)
def backup_files_still_present():
    def _query(params):
        return [{"task_id": task_id, "status": 4, "expired": "0"} for task_id in params["task_ids"]]

    with patch(
        "backend.db_services.redis.rollback.backup_presence.RedisBackupApi.query_for_task_ids", side_effect=_query
    ):
        yield


def _record(shard_value, file_name, size=GB):
    return {
        "shard_value": shard_value,
        "source_ip": "1.1.1.9",
        "server_port": 30000,
        "file_name": file_name,
        "task_id": "task-{}".format(file_name),
        "size": size,
        "backup_identify": "SCHEDULED-1",
        "backup_begin_time": "2026-01-01T01:00:00+00:00",
        "backup_end_time": "2026-01-01T01:01:00+00:00",
        "round_key": round_key_from_filename(file_name),
    }


def _planner(host_count, spec, shard_values=None, cluster_type=ClusterType.TendisTwemproxyRedisInstance.value):
    cluster = MagicMock(id=1, immute_domain="cache.example.db", cluster_type=cluster_type, bk_cloud_id=0, bk_biz_id=3)
    cluster.major_version = "Redis-6"
    cluster.proxyinstance_set.first.return_value = MagicMock(port=50000)
    info = {"backup_identify": "SCHEDULED-1", "resource_spec": {"redis": {"id": 9, "count": host_count}}}
    if shard_values:
        info["shard_values"] = shard_values
    planner = RollbackPlanner(cluster, info)
    planner.resolver.from_db_meta = MagicMock(return_value=[])
    planner.locator.locate_full_by_identify = MagicMock(
        return_value=[_record(shard, "{}.rdb".format(i)) for i, shard in enumerate(SHARDS)]
    )
    planner._spec = MagicMock(return_value=spec)
    return planner


def _spec(mem_gb=64, cpu=16):
    return SimpleNamespace(mem={"min": mem_gb, "max": mem_gb}, cpu={"min": cpu, "max": cpu})


# --- 9.2 memory at ticket time ---------------------------------------------------------


def test_load_memory_uses_file_type_and_compression():
    assert load_memory([("a.rdb", GB)]) == 2 * GB
    # compressed files are taken at UNPACK_RATIO
    assert load_memory([("a.aof.zst", GB)]) == 6 * GB


def test_busiest_host_short_of_memory_rejects_with_minimum_hosts():
    # four 1G RDBs need 2G each; one 5G host admits 4.5G, so two of them
    planner = _planner(host_count=1, spec=_spec(mem_gb=5))
    with pytest.raises(RollbackPlanError) as exc:
        planner.build(pack=False)
    assert "至少需要 2 台" in exc.value.message

    assert planner.precheck()["exist"] is False


def test_memory_enough_once_spread_over_hosts():
    planner = _planner(host_count=2, spec=_spec(mem_gb=5))
    assert planner.precheck()["exist"] is True


def test_spec_memory_keeps_the_actuator_reserve():
    # two 2G shards per 4G host fill it, but the actuator only admits 3.6G
    planner = _planner(host_count=2, spec=_spec(mem_gb=4))
    assert planner.precheck()["exist"] is False


def test_heap_packing_matches_the_linear_scan():
    def linear(real, placeholders, host_count, size):
        buckets, loads = [[] for _ in range(host_count)], [0] * host_count
        for item in real:
            index = min(range(host_count), key=lambda i: (loads[i], len(buckets[i]), i))
            buckets[index].append(item)
            loads[index] += size(item)
        for item in placeholders:
            index = min(range(host_count), key=lambda i: (len(buckets[i]), i))
            buckets[index].append(item)
        return buckets

    sizes = sorted([(i * 7919) % 97 for i in range(300)], reverse=True)
    real = list(range(len(sizes)))
    placeholders = list(range(1000, 1050))
    for host_count in (1, 2, 7, 64, 300):
        assert balance_hosts(real, placeholders, host_count, sizes.__getitem__) == linear(
            real, placeholders, host_count, sizes.__getitem__
        )


def test_fewest_hosts_searches_instead_of_scanning():
    calls = []

    def busiest(count):
        calls.append(count)
        return -(-2000 // count)

    assert RollbackPlanner._fewest_hosts(busiest, limit=10, host_count=1, total=2000, shards=2000) == 200
    assert len(calls) <= 12


def test_a_shard_larger_than_the_spec_asks_for_a_bigger_spec():
    planner = _planner(host_count=1, spec=_spec(mem_gb=1))
    with pytest.raises(RollbackPlanError) as exc:
        planner.build(pack=False)
    assert "换更大内存的规格" in exc.value.message


def test_ssd_does_not_check_memory():
    planner = _planner(host_count=1, spec=_spec(mem_gb=1), cluster_type=ClusterType.TwemproxyTendisSSDInstance.value)
    planner._check_binlog_chains = MagicMock()
    assert not any("内存" in message for message in planner.precheck()["errors"])


def test_packing_records_memory_for_cache_hosts_only():
    planner = _planner(host_count=2, spec=_spec())
    plan = planner.build(pack=False)
    RollbackPlanner.pack_dest_hosts(plan, ["2.2.2.2", "3.3.3.3"], 2)
    assert [host.memory_bytes for host in plan.dest_hosts] == [4 * GB, 4 * GB]

    plan.cluster_type = ClusterType.TwemproxyTendisSSDInstance.value
    RollbackPlanner.pack_dest_hosts(plan, ["2.2.2.2", "3.3.3.3"], 2)
    assert [host.memory_bytes for host in plan.dest_hosts] == [0, 0]


@pytest.mark.parametrize(
    "redis_spec,expected",
    [
        ({"spec_id": 7, "count": 1}, 7),
        ({"id": 9, "count": 1}, 9),
        ({"spec_id": 7, "id": 9}, 7),
        ({"count": 1}, None),
    ],
)
def test_spec_reads_spec_id_or_pool_expanded_id(redis_spec, expected):
    cluster = MagicMock(cluster_type=ClusterType.TendisTwemproxyRedisInstance.value)
    planner = RollbackPlanner(cluster, {"backup_identify": "SCHEDULED-1", "resource_spec": {"redis": redis_spec}})
    with patch("backend.flow.engine.bamboo.scene.redis.redis_rollback.planner.Spec") as spec_model:
        planner._spec()
    if expected is None:
        spec_model.objects.filter.assert_not_called()
    else:
        spec_model.objects.filter.assert_called_once_with(spec_id=expected)


# --- 9.3 memory on the real host -------------------------------------------------------


def _precheck_service():
    svc = RedisRollbackDiskPrecheckService.__new__(RedisRollbackDiskPrecheckService)
    svc.log_info = svc.log_error = lambda *a, **k: None
    return svc


def test_host_memory_short_stops_before_download():
    svc = _precheck_service()
    host = {"mem_total_kb": str(16 * 1024 * 1024), "mem_available_kb": str(10 * 1024 * 1024)}
    assert svc._check_memory("2.2.2.2", host, 11 * GB) is False
    # fits MemAvailable but not the window the actuator admits into
    assert svc._check_memory("2.2.2.2", host, int(9.5 * GB)) is False
    assert svc._check_memory("2.2.2.2", host, 9 * GB) is True
    # SSD hosts and old plans carry no memory need
    assert svc._check_memory("2.2.2.2", {}, 0) is True
    # a Cache host that did not report memory cannot be cleared
    assert svc._check_memory("2.2.2.2", {}, GB) is False


# --- 10.7 capacity hint ----------------------------------------------------------------


def test_precheck_hints_when_instances_get_less_than_two_cores():
    result = _planner(host_count=1, spec=_spec(cpu=4)).precheck()
    assert result["estimate"] == {
        "capacity": {"host_count": 1, "cpu_per_host": 4, "max_instances_per_host": 4, "cpu_per_instance": 1.0},
        "stages": [],
    }
    assert any("不足 2 核" in warning for warning in result["warnings"])

    result = _planner(host_count=1, spec=_spec(cpu=8)).precheck()
    assert not any("不足 2 核" in warning for warning in result["warnings"])


def test_precheck_without_spec_or_hosts_does_not_estimate():
    for planner in (_planner(host_count=1, spec=None), _planner(host_count=0, spec=_spec())):
        result = planner.precheck()
        assert result["estimate"] == {"capacity": None, "stages": []}
        assert not any("不足 2 核" in warning for warning in result["warnings"])


def test_placeholders_are_not_counted_as_instances():
    result = _planner(host_count=1, spec=_spec(cpu=4), shard_values=SHARDS[:2]).precheck()
    assert result["estimate"]["capacity"]["max_instances_per_host"] == 2
    assert not any("不足 2 核" in warning for warning in result["warnings"])


# --- 10.1 / 10.6 manifest and verification ---------------------------------------------


def _item(shard, dest_ip, full_name, binlogs=()):
    return RollbackItem(
        shard=ShardRef(shard),
        source_ip="1.1.1.1",
        source_port=30000,
        source_is_current=True,
        dest_ip=dest_ip,
        dest_port=30000,
        full_files=[
            FullBackupRef(
                task_id="f",
                file_name=full_name,
                size=10,
                source_ip="1.1.1.1",
                source_port=30000,
                shard_value=shard,
                backup_identify="SCHEDULED-1",
                backup_begin_time="",
                backup_end_time="",
                round_key=full_name,
            )
        ],
        binlog_files=[
            BinlogRef(task_id="b", file_name=name, size=5, source_ip="1.1.1.1", source_port=30000, index=i)
            for i, name in enumerate(binlogs)
        ],
    )


def _manifest_plan():
    return RollbackPlan(
        cluster_id=1,
        immute_domain="ssd.example.db",
        cluster_type=ClusterType.TwemproxyTendisSSDInstance.value,
        tendis_type=ClusterType.TendisSSDInstance.value,
        bk_cloud_id=0,
        bk_biz_id=3,
        db_version="TendisSSD-1.3",
        proxy_port=50000,
        items=[
            _item("0-209999", "2.2.2.2", "a.tar", binlogs=["binlog-1.log.zst", "binlog-2.log.zst"]),
            _item("210000-419999", "3.3.3.3", "b.tar"),
        ],
    )


def test_manifest_lists_this_hosts_files_compactly():
    manifest = rollback_manifest(_manifest_plan(), 7, "2.2.2.2")
    header, *lines = manifest.content.splitlines()
    assert manifest.file_name == "rollback_manifest_7"
    assert lines == ["a.tar 10 -", "binlog-1.log.zst 5 -", "binlog-2.log.zst 5 -"]
    assert manifest.count == 3
    assert manifest.fingerprint == hashlib.sha256("".join(line + "\n" for line in lines).encode()).hexdigest()
    assert header == "# redis rollback manifest plan=7 files=3 sha256={}".format(manifest.fingerprint)


def test_verify_payload_carries_no_file_list():
    builder = RedisActPayload.__new__(RedisActPayload)
    with patch.object(RollbackPlan, "load", return_value=_manifest_plan()):
        payload = builder.redis_rollback_verify_payload(
            ip="2.2.2.2", params={"plan_id": 7, "dest_ip": "2.2.2.2", "dest_dir": ""}
        )
    assert payload["action"] == "redis_rollback_verify"
    assert payload["payload"]["manifest_file"] == "rollback_manifest_7"
    assert "a.tar" not in str(payload) and "binlog-1" not in str(payload)


def test_downloads_are_verified_instead_of_confirmed_by_hand():
    source = inspect.getsource(rollback_flow.RedisRollbackFlow.build_cluster_rollback)
    assert "PauseComponent" not in source
    assert source.index("RedisRollbackDownloadComponent") < source.index("_add_verify_acts")
    assert source.index("_add_verify_acts") < source.index("redis_rollback_payload")

    verify = inspect.getsource(rollback_flow.RedisRollbackFlow._add_verify_acts)
    assert verify.index("RedisRollbackPushManifestComponent") < verify.index("redis_rollback_verify_payload")


# --- disk peaks per engine -------------------------------------------------------------


def _ssd_host_items():
    # a.tar 10 with two 5-byte .zst binlogs (15 unpacked each), b.tar 10 without binlogs
    items = _manifest_plan().items
    items[1].dest_ip = "2.2.2.2"
    placeholder = _item("420000-419999", "2.2.2.2", "c.tar")
    placeholder.full_files, placeholder.is_placeholder = [], True
    return items + [placeholder]


def test_stage_slots_follow_the_actuator_limits():
    assert stage_slots(cpu=16, max_concurrency=0, ports=20) == 8
    assert stage_slots(cpu=16, max_concurrency=3, ports=20) == 3
    assert stage_slots(cpu=16, max_concurrency=0, ports=2) == 2
    assert stage_slots(cpu=1, max_concurrency=0, ports=5) == 1
    # an unknown CPU count assumes every port at once
    assert stage_slots(cpu=0, max_concurrency=0, ports=5) == 5


def test_ssd_downloads_are_the_only_backup_disk_need():
    items = [
        _item("0-209999", "2.2.2.2", "a.tar", binlogs=["binlog-1.log.zst"]),
        _item("210000-419999", "2.2.2.2", "b.tar", binlogs=["binlog-2.log.zst"]),
    ]
    # Replay streams the downloaded binlogs, so no decompressed or parsed copy adds to them.
    backup, _ = host_disk_needs(items, is_ssd=True, cpu=2, max_concurrency=0)
    assert backup == 10 + 10 + 5 + 5


def test_cache_disks_hold_downloads_and_one_unpacked_copy():
    items = [_item("0-209999", "2.2.2.2", "a.rdb.zst"), _item("210000-419999", "2.2.2.2", "b.rdb")]
    assert host_disk_needs(items, is_ssd=False, cpu=16, max_concurrency=0) == (20, 30 + 10)


def test_ssd_counts_rebuild_and_replayed_writes():
    items = _ssd_host_items()
    # one port at a time: data = unpacked 20 + one port's backup beside its rocksdb 10 + replayed
    # writes 30; backup = downloads 30, binlogs are streamed and need no room of their own
    assert host_disk_needs(items, is_ssd=True, cpu=2, max_concurrency=0) == (30, 60)
    # both ports at once
    assert host_disk_needs(items, is_ssd=True, cpu=0, max_concurrency=0) == (30, 70)


def test_disk_precheck_sizes_from_the_plan_and_host_cpus():
    svc = _precheck_service()
    svc._check = MagicMock(return_value=True)
    plan = _manifest_plan()
    plan.items = _ssd_host_items()
    plan.dest_hosts = [SimpleNamespace(ip="2.2.2.2", memory_bytes=0)]
    df = "/dev/vdb 1000 100 900 10% {}"
    host = {
        "redis_backup_dir_data": df.format("/data"),
        "redis_data_dir_data": df.format("/data1"),
        "redis_backup_dir_dev": "1",
        "redis_data_dir_dev": "2",
        "cpu_count": "2",
    }
    data = MagicMock()
    data.get_one_of_inputs.side_effect = lambda key: {
        "kwargs": {"exec_ip": "2.2.2.2", "plan_id": 7},
        "trans_data": SimpleNamespace(disk_used={"2.2.2.2": host}),
    }[key]
    with patch.object(RollbackPlan, "load", return_value=plan):
        assert svc._execute(data, None) is True
    assert [c.args[3] for c in svc._check.call_args_list] == [30, 60]


# --- 9.9 plan_id in the record ---------------------------------------------------------


def test_record_points_to_its_own_plan():
    plan = _manifest_plan()
    assert plan.to_rollback_detail(7)["plan_id"] == 7
    assert plan.to_rollback_detail(8)["plan_id"] == 8
    assert "plan.to_rollback_detail(plan_id)" in inspect.getsource(
        rollback_flow.RedisRollbackFlow.build_cluster_rollback
    )


# --- 10.9 / 10.10 temp passwords -------------------------------------------------------


def test_temp_password_is_fixed_length_and_differs_per_plan_and_source():
    password = rollback_temp_password("source-secret", 7)
    assert password == rollback_temp_password("source-secret", 7)
    assert password.startswith("restored_") and "source-secret" not in password
    assert len(password) == len("restored_") + 32
    assert password != rollback_temp_password("source-secret", 8)
    assert password != rollback_temp_password("other-secret", 7)
    with pytest.raises(ValueError):
        rollback_temp_password("p", None)


def test_construction_record_stores_the_derived_passwords():
    def _write(rollback_version):
        cluster = {
            "domain_name": "cache.example.db",
            "bk_cloud_id": 0,
            "prod_cluster_type": "",
            "prod_cluster_id": 1,
            "specification": {},
            "prod_cluster": "cache.example.db",
            "prod_instance_range": [],
            "temp_cluster_type": "",
            "temp_instance_range": [],
            "temp_cluster_proxy": "",
            "prod_temp_instance_pairs": [],
            "host_count": 1,
            "recovery_time_point": "",
            "status": 1,
            "rollback_version": rollback_version,
            "plan_id": 7,
        }
        meta = RedisDBMeta({"created_by": "a", "uid": 1, "bk_biz_id": 3}, cluster)
        with patch(
            "backend.flow.utils.redis.redis_db_meta.PayloadHandler.redis_get_password_by_domain",
            return_value={"redis_password": "r", "redis_proxy_password": "p"},
        ), patch("backend.flow.utils.redis.redis_db_meta.TbTendisRollbackTasks") as model:
            meta.data_construction_tasks_operate()
        kwargs = model.call_args.kwargs
        decode = lambda value: base64.b64decode(ast.literal_eval(str(value))).decode()  # noqa: E731
        return decode(kwargs["temp_redis_password"]), decode(kwargs["temp_proxy_password"])

    assert _write("rollback") == (rollback_temp_password("r", 7), rollback_temp_password("p", 7))
    assert _write("datastructure") == ("r", "p")


def _proxy_builder(monkeypatch):
    from backend.flow.utils.redis import redis_act_playload

    monkeypatch.setattr(
        redis_act_playload.Package,
        "get_latest_package_v2_release",
        MagicMock(return_value=MagicMock(name="pkg", md5="m")),
    )
    builder = RedisActPayload.__new__(RedisActPayload)
    builder.cluster = {
        "bk_biz_id": 3,
        "domain_name": "cache.example.db",
        "proxy_port": 50000,
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
    }
    builder.proxy_version = "latest"
    builder._RedisActPayload__get_cluster_config = MagicMock(
        return_value={"redis_password": "r", "password": "p", "redis_proxy_admin_password": "a"}
    )
    return builder


def test_v2_proxy_gets_derived_passwords_and_v1_keeps_the_source(monkeypatch):
    builder = _proxy_builder(monkeypatch)
    # the shared builder is created before the proxy node sets servers, so they come from node params
    servers = ["2.2.2.2:30000 admin 0-419999 1"]
    v1 = builder.rollback_twemproxy_payload(ip="2.2.2.2", params={"servers": servers})["payload"]
    assert (v1["password"], v1["redis_password"], v1["servers"]) == ("p", "r", servers)

    derived = {source: rollback_temp_password(source, 7) for source in ("p", "r", "a")}
    v2 = builder.rollback_twemproxy_payload(ip="2.2.2.2", params={"servers": [], "temp_password_plan_id": 7})
    v2 = v2["payload"]
    assert (v2["password"], v2["redis_password"]) == (derived["p"], derived["r"])
    assert v2["conf_configs"]["password"] == derived["p"]

    predixy = builder.rollback_predixy_payload(ip="2.2.2.2", params={"servers": [], "temp_password_plan_id": 7})
    predixy = predixy["payload"]
    assert (predixy["predixypasswd"], predixy["predixyadminpasswd"], predixy["redispasswd"]) == (
        derived["p"],
        derived["a"],
        derived["r"],
    )


def test_v2_instances_get_the_derived_password():
    builder = RedisActPayload.__new__(RedisActPayload)
    builder.bk_biz_id = "3"
    builder.get_redis_install_4_scene = MagicMock(
        return_value={"payload": {"password": "r", "redis_conf_configs": {"requirepass": "r", "port": "1"}}}
    )
    with patch.object(RollbackPlan, "load", return_value=_manifest_plan()):
        payload = builder.redis_rollback_payload(
            ip="2.2.2.2",
            params={
                "plan_id": 7,
                "dest_ip": "2.2.2.2",
                "immute_domain": "cache.example.db",
                "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
                "db_version": "Redis-6",
            },
        )["payload"]
    derived = rollback_temp_password("r", 7)
    assert payload["install"]["password"] == derived
    assert payload["install"]["redis_conf_configs"] == {"requirepass": derived, "port": "1"}
    assert payload["max_concurrency"] == 0


def test_with_temp_passwords_leaves_the_source_config_alone():
    config = {"password": "p", "port": 1}
    assert with_temp_passwords(config, 7) == {"password": rollback_temp_password("p", 7), "port": 1}
    assert config == {"password": "p", "port": 1}


def test_plan_carries_max_concurrency_override():
    planner = _planner(host_count=2, spec=_spec())
    planner.info["max_concurrency"] = 2
    assert planner.build(pack=False).max_concurrency == 2
