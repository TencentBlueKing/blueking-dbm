# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone as django_timezone

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.rollback.binlogs import binlog_fingerprint
from backend.db_services.redis.rollback.exceptions import RollbackPlanError
from backend.db_services.redis.rollback.models import TbTendisRollbackPlan
from backend.db_services.redis.rollback.shards import ShardRef
from backend.flow.engine.bamboo.scene.redis.redis_rollback import flow as rollback_flow
from backend.flow.engine.bamboo.scene.redis.redis_rollback.plan import (
    ORPHAN_PLAN_TTL,
    BinlogRef,
    DestHost,
    FullBackupRef,
    RollbackItem,
    RollbackPlan,
)
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner
from backend.flow.plugins.components.collections.redis import redis_rollback as rollback_components
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackContext
from backend.ticket.builders.redis.redis_rollback import RedisRollbackFlowBuilder

FULL_NAME = "3-TENDISSSD-FULL-slave-1.1.1.1-30000-20260101-000000-9.tar"


def _item(binlog_count, first_index=1000, dest_ip="", dest_port=0):
    binlogs = [
        BinlogRef(
            task_id="binlog-{}".format(i),
            file_name="binlog-1.1.1.1-30000-{:07d}-20260101000000.log.zst".format(i),
            size=1,
            source_ip="1.1.1.1",
            source_port=30000,
            index=i,
        )
        for i in range(first_index, first_index + binlog_count)
    ]
    full = FullBackupRef(
        task_id="full-1",
        file_name=FULL_NAME,
        size=10,
        source_ip="1.1.1.1",
        source_port=30000,
        shard_value="0-419999",
        backup_identify="SCHEDULED-1",
        backup_begin_time="2026-01-01T00:00:00+00:00",
        backup_end_time="2026-01-01T00:10:00+00:00",
        round_key=FULL_NAME,
    )
    return RollbackItem(
        shard=ShardRef("0-419999", current_master="1.1.1.1:30000"),
        source_ip="1.1.1.1",
        source_port=30000,
        source_is_current=True,
        dest_ip=dest_ip,
        dest_port=dest_port,
        full_files=[full],
        binlog_files=binlogs,
    )


def _plan(binlog_count=2, packed=True):
    item = _item(binlog_count, dest_ip="2.2.2.2" if packed else "", dest_port=30000 if packed else 0)
    hosts = [DestHost(ip="2.2.2.2", ports=[30000], task_ids=item.task_ids, download_bytes=item.download_bytes)]
    return RollbackPlan(
        cluster_id=1,
        immute_domain="ssd.example.db",
        cluster_type=ClusterType.TwemproxyTendisSSDInstance.value,
        tendis_type=ClusterType.TendisSSDInstance.value,
        bk_cloud_id=0,
        bk_biz_id=3,
        db_version="TendisSSD-1.3",
        proxy_port=50000,
        recover_at=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
        backup_identify="SCHEDULED-1",
        items=[item],
        dest_hosts=hosts if packed else [],
    )


def test_plan_round_trips_through_dict():
    plan = _plan()
    restored = RollbackPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
    assert restored == plan


@pytest.mark.django_db
def test_plan_is_saved_once_and_updated_in_place():
    plan = _plan(packed=False)
    plan_id = plan.save()
    assert RollbackPlan.load(plan_id) == plan

    RollbackPlanner.pack_dest_hosts(plan, ["2.2.2.2"], 1)
    assert plan.save(plan_id) == plan_id
    assert RollbackPlan.load(plan_id).dest_host("2.2.2.2").ports == [30000]


@pytest.mark.django_db
def test_plan_is_bound_to_its_ticket():
    plan = _plan(packed=False)
    bound_at_submit, bound_at_flow, unbound = plan.save(), plan.save(), plan.save()
    RollbackPlan.bind_ticket([bound_at_submit], 11)
    plan.save(bound_at_flow, ticket_id="12")
    plan.save(unbound)

    ticket_ids = dict(TbTendisRollbackPlan.objects.values_list("id", "ticket_id"))
    assert ticket_ids == {bound_at_submit: 11, bound_at_flow: 12, unbound: None}
    assert TbTendisRollbackPlan.objects.get(id=plan.save(ticket_id=13)).ticket_id == 13


@pytest.mark.django_db
def test_only_old_plans_without_a_ticket_are_cleaned():
    plan = _plan(packed=False)
    old_orphan, new_orphan, old_bound = plan.save(), plan.save(), plan.save(ticket_id=11)
    TbTendisRollbackPlan.objects.filter(id__in=[old_orphan, old_bound]).update(
        create_at=django_timezone.now() - ORPHAN_PLAN_TTL - timedelta(minutes=1)
    )

    assert RollbackPlan.delete_orphans() == 1
    assert set(TbTendisRollbackPlan.objects.values_list("id", flat=True)) == {new_orphan, old_bound}


def test_ticket_builder_binds_submitted_plans():
    builder = RedisRollbackFlowBuilder.__new__(RedisRollbackFlowBuilder)
    builder.ticket = MagicMock(id=21, details={"infos": [{"plan_id": 5}, {"plan_id": 6}, {}]})
    with patch.object(RollbackPlan, "bind_ticket") as bind:
        builder.patch_ticket_detail()
    bind.assert_called_once_with([5, 6], 21)


def test_flow_writes_its_ticket_onto_the_plan():
    with patch.object(RollbackPlan, "load", return_value=_plan(packed=False)), patch.object(
        RollbackPlan, "save", return_value=7
    ) as save, patch.object(rollback_flow, "confirm_backup_tasks", return_value={}):
        rollback_flow.RedisRollbackFlow._load_plan(MagicMock(), {"plan_id": 7}, ["2.2.2.2"], ticket_id=31)
    save.assert_called_once_with(7, ticket_id=31)


def test_actuator_instance_sends_a_digest_instead_of_file_names():
    instance = _plan(binlog_count=3).actuator_instances("2.2.2.2")[0]
    names = ["binlog-1.1.1.1-30000-{:07d}-20260101000000.log.zst".format(i) for i in (1000, 1001, 1002)]
    assert instance == {
        "source_ip": "1.1.1.1",
        "source_port": 30000,
        "dest_port": 30000,
        "full_files": [FULL_NAME],
        "binlog_range": {"first_index": 1000, "last_index": 1002},
        "binlog_count": 3,
        "binlog_fingerprint": binlog_fingerprint(names),
        "binlog_segments": "[1000-1002]",
    }


def _rollback_payload(plan):
    builder = RedisActPayload.__new__(RedisActPayload)
    builder.bk_biz_id = "3"
    builder.get_redis_install_4_scene = MagicMock(return_value={"payload": {"db_type": plan.cluster_type}})
    with patch.object(RollbackPlan, "load", return_value=plan):
        return builder.redis_rollback_payload(
            ip="2.2.2.2",
            params={
                "plan_id": 7,
                "dest_ip": "2.2.2.2",
                "dest_dir": "",
                "immute_domain": plan.immute_domain,
                "cluster_type": plan.cluster_type,
                "db_version": plan.db_version,
            },
        )


# Counts of equal digit width, so any size difference comes from listing files.
SMALL, LARGE = 1000, 5000


def test_rollback_payload_does_not_grow_with_binlog_count():
    small, large = _rollback_payload(_plan(binlog_count=SMALL)), _rollback_payload(_plan(binlog_count=LARGE))
    assert len(json.dumps(small)) == len(json.dumps(large))
    assert "binlog-1.1.1.1" not in json.dumps(large)
    assert large["payload"]["recover_at"] == "2026-01-01T01:00:00+00:00"
    assert large["payload"]["instances"][0]["binlog_count"] == LARGE


def _built_kwargs(plan):
    """Every node kwargs of one cluster's pipeline, built from ``plan``."""
    recorded = []

    class Recorder(MagicMock):
        def add_act(self, act_name, act_component_code, kwargs, **_):
            recorded.append(kwargs)

        def add_parallel_acts(self, acts_list):
            recorded.extend(act["kwargs"] for act in acts_list)

    flow = rollback_flow.RedisRollbackFlow("root", {"bk_biz_id": 3, "is_rollback_drill": True, "uid": 1})
    info = {"cluster_id": 1, "redis": [{"ip": "2.2.2.2"}], "resource_spec": {"redis": {"id": 1}}}
    with patch.object(rollback_flow.Cluster, "objects"), patch.object(
        rollback_flow.RedisRollbackFlow, "_load_plan", return_value=(7, plan)
    ), patch.object(rollback_flow, "SubBuilder", Recorder), patch.object(rollback_flow, "GetFileList"), patch.object(
        rollback_flow.PayloadHandler, "redis_get_os_account", return_value={"os_user": "u", "os_password": "p"}
    ):
        flow.build_cluster_rollback(info)
    return recorded


def test_node_kwargs_reference_the_plan_and_do_not_grow_with_binlog_count():
    small, large = _built_kwargs(_plan(binlog_count=SMALL)), _built_kwargs(_plan(binlog_count=LARGE))
    assert len(json.dumps(small, default=str)) == len(json.dumps(large, default=str))
    # Only the rollback_detail digest names binlogs: the first and the last.
    assert json.dumps(large, default=str).count("binlog-1.1.1.1") == 2

    download = next(kwargs for kwargs in large if "login_passwd" in kwargs)
    assert download["plan_id"] == 7 and download["dest_ip"] == "2.2.2.2"
    assert "task_ids" not in download
    recover = next(k for k in large if k.get("get_redis_payload_func") == "redis_rollback_payload")
    assert recover["cluster"]["plan_id"] == 7 and "instances" not in recover["cluster"]


def test_flow_runs_the_submitted_plan_without_replanning():
    submitted = _plan(packed=False)
    with patch.object(RollbackPlan, "load", return_value=submitted), patch.object(
        RollbackPlan, "save", side_effect=lambda plan_id=None, ticket_id=None: plan_id
    ), patch.object(rollback_flow, "confirm_backup_tasks", return_value={}) as confirm, patch.object(
        rollback_flow, "RollbackPlanner", wraps=rollback_flow.RollbackPlanner
    ) as planner:
        plan_id, plan = rollback_flow.RedisRollbackFlow._load_plan(MagicMock(), {"plan_id": 7}, ["2.2.2.2"])

    planner.assert_not_called()
    assert plan_id == 7 and plan is submitted
    assert confirm.call_args.args[0] == {"0-419999": submitted.items[0].task_ids}
    assert [(item.dest_ip, item.dest_port) for item in plan.items] == [("2.2.2.2", 30000)]


def test_flow_keeps_an_allowed_binlog_gap_without_rechecking_the_chain():
    submitted = _plan(packed=False)
    submitted.allow_binlog_nonconsecutive = True
    submitted.items[0].binlog_gaps = {"missing_count": 1, "missing": [1001]}
    with patch.object(RollbackPlan, "load", return_value=submitted), patch.object(
        RollbackPlan, "save", side_effect=lambda plan_id=None, ticket_id=None: plan_id
    ), patch.object(rollback_flow, "confirm_backup_tasks", return_value={}), patch.object(
        rollback_flow, "select_binlog_chain", create=True
    ) as chain, patch.object(
        rollback_flow, "RollbackPlanner", wraps=rollback_flow.RollbackPlanner
    ) as planner:
        # Flow-time info no longer carries the flag; the plan decides.
        _, plan = rollback_flow.RedisRollbackFlow._load_plan(MagicMock(), {"plan_id": 7}, ["2.2.2.2"])

    planner.assert_not_called()
    chain.assert_not_called()
    assert plan.to_rollback_detail()["shards"][0]["binlog"]["gaps"] == {"missing_count": 1, "missing": [1001]}


def test_flow_refuses_a_plan_whose_files_are_gone():
    with patch.object(RollbackPlan, "load", return_value=_plan(packed=False)), patch.object(
        rollback_flow, "confirm_backup_tasks", return_value={"0-419999": ["full-1 已过期"]}
    ):
        with pytest.raises(RollbackPlanError) as exc:
            rollback_flow.RedisRollbackFlow._load_plan(MagicMock(), {"plan_id": 7}, ["2.2.2.2"])
    assert "已过期" in exc.value.message


def _download_service():
    svc = rollback_components.RedisRollbackDownloadService.__new__(rollback_components.RedisRollbackDownloadService)
    svc.log_info = svc.log_error = svc.log_debug = lambda *a, **k: None
    svc.finish_schedule = MagicMock()
    return svc


def test_download_submits_one_bill_per_batch():
    plan = _plan(binlog_count=rollback_components.DOWNLOAD_BATCH_SIZE)
    kwargs = {
        "bk_cloud_id": 0,
        "plan_id": 7,
        "dest_ip": "2.2.2.2",
        "login_user": "u",
        "login_passwd": "p",
        "set_trans_data_dataclass": RedisRollbackContext.__name__,
    }
    trans_data = RedisRollbackContext(disk_used={"2.2.2.2": {"backup_dir": "/data"}})
    data = SimpleNamespace(
        get_one_of_inputs={"kwargs": kwargs, "trans_data": trans_data}.get, outputs=SimpleNamespace()
    )
    bills = iter([11, 12])
    with patch.object(RollbackPlan, "load", return_value=plan), patch.object(
        rollback_components.RedisBackupApi, "download", side_effect=lambda params: {"bill_id": next(bills)}
    ) as download:
        assert _download_service()._execute(data, None) is True

    batches = [call.kwargs["params"]["taskid_list"] for call in download.call_args_list]
    assert [len(batch) for batch in batches] == [rollback_components.DOWNLOAD_BATCH_SIZE, 1]
    assert sum(batches, []) == plan.dest_hosts[0].task_ids
    assert data.outputs.backup_bill_ids == [11, 12]


def test_download_failure_logs_the_bills_already_submitted():
    plan = _plan(binlog_count=rollback_components.DOWNLOAD_BATCH_SIZE)
    kwargs = {
        "bk_cloud_id": 0,
        "plan_id": 7,
        "dest_ip": "2.2.2.2",
        "login_user": "u",
        "login_passwd": "p",
        "set_trans_data_dataclass": RedisRollbackContext.__name__,
    }
    trans_data = RedisRollbackContext(disk_used={"2.2.2.2": {"backup_dir": "/data"}})
    data = SimpleNamespace(
        get_one_of_inputs={"kwargs": kwargs, "trans_data": trans_data}.get, outputs=SimpleNamespace()
    )
    svc = _download_service()
    errors = []
    svc.log_error = errors.append
    bills = iter([{"bill_id": 11}, {"bill_id": -1}])
    with patch.object(RollbackPlan, "load", return_value=plan), patch.object(
        rollback_components.RedisBackupApi, "download", side_effect=lambda params: next(bills)
    ):
        assert svc._execute(data, None) is False
    assert "[11]" in errors[0]


def _schedule(outputs, totals):
    data = SimpleNamespace(get_one_of_outputs=outputs.get, outputs=SimpleNamespace())
    svc = _download_service()
    with patch.object(
        rollback_components.RedisBackupApi, "download_result", side_effect=lambda p: {"total": totals[p["bill_id"]]}
    ):
        return svc._schedule(data, None), svc.finish_schedule.called


def test_schedule_waits_for_every_bill_and_fails_on_any():
    done = {"todo": 0, "doing": 0, "fail": 0}
    busy = {"todo": 1, "doing": 1, "fail": 0}
    failed = {"todo": 0, "doing": 0, "fail": 1}
    assert _schedule({"backup_bill_ids": [11, 12]}, {11: done, 12: busy}) == (True, False)
    assert _schedule({"backup_bill_ids": [11, 12]}, {11: done, 12: done}) == (True, True)
    assert _schedule({"backup_bill_ids": [11, 12]}, {11: busy, 12: failed}) == (False, True)
    # Nodes started before batching recorded a single bill.
    assert _schedule({"backup_bill_id": 11}, {11: done}) == (True, True)
