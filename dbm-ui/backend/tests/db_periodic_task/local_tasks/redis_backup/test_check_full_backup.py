# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from .conftest import make_fullbackup_entry

"""
Tests for CheckFullBackupTask — _process_bklog_entries, _evaluate_slave, _check_cluster, _collect_instance_pairs.

Source-module imports are done lazily to avoid triggering the
``local_tasks/__init__.py`` import chain.
"""

pytestmark = pytest.mark.django_db

_PATCH_FIND = "backend.db_periodic_task.local_tasks.redis_backup.check_full_backup.find_and_verify_failed_tasks"
_PATCH_FETCH = "backend.db_periodic_task.local_tasks.redis_backup.check_full_backup.batch_fetch_backup_logs"


def _task_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import CheckFullBackupTask

    return CheckFullBackupTask


def _report_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import RedisBackupClusterReport

    return RedisBackupClusterReport


def _state():
    from backend.db_report.enums import ReportStateType

    return ReportStateType


def _make_cluster(cluster_type="TwemproxyTendisSSDInstance"):
    cluster = MagicMock()
    cluster.bk_biz_id = 3
    cluster.bk_cloud_id = 0
    cluster.immute_domain = "test.example.db"
    cluster.cluster_type = cluster_type
    return cluster


def _task():
    return _task_cls()()


def _config(**overrides):
    from backend.db_periodic_task.local_tasks.redis_backup.config import RedisBackupCheckConfig

    defaults = dict(
        target_bk_cloud_ids=[0],
        ignore_domains=[],
        min_instance_age_hours=48,
        max_schedule_deviation_hours=2.5,
    )
    defaults.update(overrides)
    return RedisBackupCheckConfig(**defaults)


def _run_evaluate_slave(
    slave_count,
    master_count,
    schedule=None,
    slave_seen=True,
    master_seen=True,
    slave_errors=None,
    master_errors=None,
    slave_times=None,
    master_times=None,
    recently_switched=None,
    api_promoted_count=0,
):
    if schedule is None:
        schedule = [5]
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    slave_inst = "3.3.3.2:30000"
    master_inst = "3.3.3.1:30000"

    sc = {slave_inst: slave_count, master_inst: master_count}
    st = {
        slave_inst: slave_times or [f"2024-01-15T{h:02d}:30:00+08:00" for h in schedule[:slave_count]],
        master_inst: master_times or [f"2024-01-15T{h:02d}:30:00+08:00" for h in schedule[:master_count]],
    }
    seen = set()
    if slave_seen:
        seen.add(slave_inst)
    if master_seen:
        seen.add(master_inst)
    inst_errors = defaultdict(list)
    if slave_errors:
        inst_errors[slave_inst] = slave_errors
    if master_errors:
        inst_errors[master_inst] = master_errors

    _task_cls()._evaluate_slave(
        report,
        slave_inst,
        master_inst,
        sc,
        st,
        seen,
        inst_errors,
        schedule,
        len(schedule),
        ", ".join(f"{h:02d}:00" for h in schedule),
        2.5,
        recently_switched=recently_switched,
        api_promoted_count=api_promoted_count,
    )
    return report


def _setup_check_cluster(cluster=None, config=None):
    if cluster is None:
        cluster = _make_cluster()
        master = SimpleNamespace(
            machine=SimpleNamespace(ip="3.3.3.1"),
            port=30000,
            ejector_tuples=[
                SimpleNamespace(
                    receiver=SimpleNamespace(
                        machine=SimpleNamespace(ip="3.3.3.2"),
                        port=30000,
                        create_at=timezone.now() - timedelta(hours=72),
                    ),
                    create_at=timezone.now() - timedelta(hours=72),
                )
            ],
        )
        cluster.storages = [master]
    if config is None:
        config = _config()
    return cluster, config


# ---------------------------------------------------------------------------
# _process_bklog_entries
# ---------------------------------------------------------------------------
def test_process_bklog_all_success():
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    entries = [
        make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.2", port=30000, task_id="t1"),
        make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.2", port=30001, task_id="t2"),
    ]
    tracked = ["3.3.3.2:30000", "3.3.3.2:30001"]
    with patch(_PATCH_FIND, return_value=set()):
        sc, st, seen, errors, promoted = _task()._process_bklog_entries(report, entries, tracked)
    assert sc["3.3.3.2:30000"] == 1
    assert sc["3.3.3.2:30001"] == 1
    assert len(errors) == 0
    assert promoted == {}


def test_process_bklog_failed_dedup_by_success_taskid():
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    entries = [
        make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.2", port=30000, task_id="t1"),
        make_fullbackup_entry(status="to_backup_system_failed", ip="3.3.3.2", port=30000, task_id="t1"),
    ]
    tracked = ["3.3.3.2:30000"]
    with patch(_PATCH_FIND, return_value=set()):
        sc, st, seen, errors, promoted = _task()._process_bklog_entries(report, entries, tracked)
    assert sc["3.3.3.2:30000"] == 1
    assert len(errors.get("3.3.3.2:30000", [])) == 0
    assert promoted == {}


def test_process_bklog_api_confirmed_counted():
    ST = _state()
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    entries = [
        make_fullbackup_entry(status="to_backup_system_start", ip="3.3.3.2", port=30000, task_id="t1"),
    ]
    tracked = ["3.3.3.2:30000"]
    with patch(_PATCH_FIND, return_value={"t1"}):
        sc, st, seen, errors, promoted = _task()._process_bklog_entries(report, entries, tracked)
    assert sc["3.3.3.2:30000"] == 1
    # API-promoted entries must not produce per-task normal report rows.
    assert report.records[ST.NORMAL.value] == []
    # The promoted slot must be tracked so _evaluate_slave can annotate the row.
    assert promoted["3.3.3.2:30000"] == 1


def test_process_bklog_failed_collects_errors():
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    entries = [
        make_fullbackup_entry(
            status="to_backup_system_failed",
            ip="3.3.3.2",
            port=30000,
            task_id="t1",
            status_info="upload err",
        ),
    ]
    tracked = ["3.3.3.2:30000"]
    with patch(_PATCH_FIND, return_value=set()):
        sc, st, seen, errors, promoted = _task()._process_bklog_entries(report, entries, tracked)
    assert sc["3.3.3.2:30000"] == 0
    assert "upload err" in errors["3.3.3.2:30000"]
    assert promoted == {}


def test_process_bklog_unknown_instance_in_seen():
    cluster = _make_cluster()
    report = _report_cls()(cluster, "full_backup")
    entries = [
        make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.9", port=30000, task_id="t1"),
    ]
    tracked = ["3.3.3.2:30000"]
    with patch(_PATCH_FIND, return_value=set()):
        sc, st, seen, errors, promoted = _task()._process_bklog_entries(report, entries, tracked)
    assert "3.3.3.9:30000" in seen
    assert sc["3.3.3.2:30000"] == 0
    assert promoted == {}


# ---------------------------------------------------------------------------
# _evaluate_slave
# ---------------------------------------------------------------------------
def test_evaluate_slave_normal_ok():
    ST = _state()
    report = _run_evaluate_slave(slave_count=1, master_count=0)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_evaluate_slave_normal_ok_fully_promoted_suffix():
    """All success slots came from the API double-check -> NORMAL with suffix."""
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=3,
        master_count=0,
        schedule=[5, 13, 21],
        api_promoted_count=3,
    )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok (3 via backup system double-check)"


def test_evaluate_slave_normal_ok_partial_promotion_shows_suffix():
    """Even one promoted slot must be surfaced so operators see the disagreement."""
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=3,
        master_count=0,
        schedule=[5, 13, 21],
        api_promoted_count=1,
    )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok (1 via backup system double-check)"


def test_evaluate_slave_off_schedule_abnormal():
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=1,
        master_count=0,
        schedule=[5],
        slave_times=["2024-01-15T10:00:00+08:00"],
    )
    records = report.records[ST.ABNORMAL.value]
    assert len(records) == 1
    assert "off-schedule" in records[0]["msg"]


def test_evaluate_slave_master_covers_warning():
    ST = _state()
    report = _run_evaluate_slave(slave_count=0, master_count=1, schedule=[5])
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "covered by master" in records[0]["msg"]


def test_evaluate_slave_both_insufficient_warning():
    ST = _state()
    report = _run_evaluate_slave(slave_count=0, master_count=0, schedule=[5, 13, 21])
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "missing" in records[0]["msg"]


def test_evaluate_slave_complementary_slots_shows_slave_missing():
    """Slave and master cover all slots together but neither alone is sufficient.

    Before the fix, missing was computed from combined times, producing an
    empty string after 'missing'.  Now it uses slave-only times so the
    slave's gap (05:00) is always displayed.
    """
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=2,
        master_count=1,
        schedule=[5, 13, 21],
        slave_times=["2024-01-15T13:30:00+08:00", "2024-01-15T21:30:00+08:00"],
        master_times=["2024-01-15T05:30:00+08:00"],
    )
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "missing 05:00" in records[0]["msg"]


def test_evaluate_slave_no_log_abnormal():
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=0,
        master_count=0,
        schedule=[5],
        slave_seen=False,
        master_seen=False,
    )
    records = report.records[ST.ABNORMAL.value]
    assert len(records) == 1
    assert "no log found" in records[0]["msg"]


def test_evaluate_slave_recently_switched_downgrades_no_log():
    """No-log case normally produces ABNORMAL; recently_switched downgrades to WARNING."""
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=0,
        master_count=0,
        schedule=[5],
        slave_seen=False,
        master_seen=False,
        recently_switched=6,
    )
    assert len(report.records[ST.ABNORMAL.value]) == 0
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "possible recent master-slave switch (6h ago)" in records[0]["msg"]
    assert "no log found" in records[0]["msg"]


def test_evaluate_slave_recently_switched_insufficient():
    """Both-insufficient case with recently_switched adds switch note and stays WARNING."""
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=0,
        master_count=0,
        schedule=[5, 13, 21],
        recently_switched=48,
    )
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "possible recent master-slave switch (48h ago)" in records[0]["msg"]
    assert "missing" in records[0]["msg"]


def test_evaluate_slave_errors_quoted():
    ST = _state()
    report = _run_evaluate_slave(
        slave_count=0,
        master_count=0,
        schedule=[5],
        slave_errors=["upload failed"],
    )
    records = report.records[ST.WARNING.value]
    assert "errors(upload failed)" in records[0]["msg"]


# ---------------------------------------------------------------------------
# _check_cluster
# ---------------------------------------------------------------------------
def test_check_cluster_cloud_id_skip():
    ST = _state()
    cluster, cfg = _setup_check_cluster()
    cfg.target_bk_cloud_ids = [99]
    rows = _task()._check_cluster(cluster, [], cfg)
    assert len(rows) == 1
    assert rows[0].state == ST.NORMAL.value
    assert "skipped" in rows[0].msg


def test_check_cluster_domain_ignore_skip():
    cluster, cfg = _setup_check_cluster()
    cfg.ignore_domains = [cluster.immute_domain]
    rows = _task()._check_cluster(cluster, [], cfg)
    assert "ignore" in rows[0].msg


def test_check_cluster_no_eligible_instances():
    cluster, cfg = _setup_check_cluster()
    for master in cluster.storages:
        master.ejector_tuples[0].receiver.create_at = timezone.now() - timedelta(hours=1)
    rows = _task()._check_cluster(cluster, [], cfg)
    assert "no eligible" in rows[0].msg


def test_check_cluster_no_bklogs_error():
    ST = _state()
    cluster, cfg = _setup_check_cluster()
    with patch(_PATCH_FIND, return_value=set()):
        rows = _task()._check_cluster(cluster, [], cfg)
    assert rows[0].state == ST.ABNORMAL.value
    assert "no full backup logs found" in rows[0].msg


def test_check_cluster_happy_path():
    ST = _state()
    cluster, cfg = _setup_check_cluster()
    bklogs = [make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.2", port=30000)]
    with patch(_PATCH_FIND, return_value=set()):
        rows = _task()._check_cluster(cluster, bklogs, cfg)
    assert len(rows) == 1
    assert rows[0].state == ST.NORMAL.value


def test_check_cluster_api_confirmed_groups_with_ok_ports():
    """API-promoted ports must NOT introduce per-task `task_id` messages.

    Mirrors the production noise scenario: ports 30000~30002 have
    `to_backup_system_start` entries that the backup system API confirms as
    successful, ports 30003 has the expected 3 successes, and port 30004 is
    missing one schedule slot.  The final per-IP report should collapse all
    healthy ports into a single `ok` segment and only call out the missing
    port; the cross-check `task_id` text must not appear.
    """
    ST = _state()
    cluster = _make_cluster(cluster_type="TwemproxyRedisInstance")  # schedule [5, 13, 21]

    storages = []
    for port in (30000, 30001, 30002, 30003, 30004):
        storages.append(
            SimpleNamespace(
                machine=SimpleNamespace(ip="3.3.3.1"),
                port=port,
                ejector_tuples=[
                    SimpleNamespace(
                        receiver=SimpleNamespace(
                            machine=SimpleNamespace(ip="3.3.3.2"),
                            port=port,
                            create_at=timezone.now() - timedelta(hours=72),
                        ),
                        create_at=timezone.now() - timedelta(hours=72),
                    )
                ],
            )
        )
    cluster.storages = storages
    cfg = _config()

    schedule_hours = (5, 13, 21)
    bklogs: list[dict] = []
    api_confirmed: set[str] = set()

    # 30000~30002: every slot recorded as `to_backup_system_start` but API-confirmed.
    for port in (30000, 30001, 30002):
        for h in schedule_hours:
            tid = f"start-{port}-{h}"
            bklogs.append(
                make_fullbackup_entry(
                    status="to_backup_system_start",
                    ip="3.3.3.2",
                    port=port,
                    task_id=tid,
                    uptime=f"2024-01-15T{h:02d}:30:00+08:00",
                )
            )
            api_confirmed.add(tid)

    # 30003: clean 3/3 successes.
    for h in schedule_hours:
        bklogs.append(
            make_fullbackup_entry(
                status="to_backup_system_success",
                ip="3.3.3.2",
                port=30003,
                task_id=f"ok-30003-{h}",
                uptime=f"2024-01-15T{h:02d}:30:00+08:00",
            )
        )

    # 30004: only 2/3 successes -- missing the 21:00 slot.
    for h in (5, 13):
        bklogs.append(
            make_fullbackup_entry(
                status="to_backup_system_success",
                ip="3.3.3.2",
                port=30004,
                task_id=f"ok-30004-{h}",
                uptime=f"2024-01-15T{h:02d}:30:00+08:00",
            )
        )

    with patch(_PATCH_FIND, return_value=api_confirmed):
        rows = _task()._check_cluster(cluster, bklogs, cfg)

    # Records are grouped per IP, so all five slave ports collapse into one row.
    assert len(rows) == 1
    row = rows[0]
    assert row.instance == "3.3.3.2"
    # Worst port drives the row state.
    assert row.state == ST.WARNING.value
    # Fully-promoted ports group separately with a NORMAL suffix indicating the double-check.
    assert "30000~30002: ok (3 via backup system double-check)" in row.msg
    # The cleanly-successful port stays plain `ok` and forms its own segment.
    assert "30003: ok" in row.msg
    # The struggling port must surface its missing slot.
    assert "30004: " in row.msg
    assert "missing 21:00" in row.msg
    # No per-task noise should leak into the message.
    assert "task_id" not in row.msg
    assert "backup system confirms success" not in row.msg


def test_check_cluster_mixed_per_ip_rows():
    ST = _state()
    cluster = _make_cluster()
    m1 = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.1"),
        port=30000,
        ejector_tuples=[
            SimpleNamespace(
                receiver=SimpleNamespace(
                    machine=SimpleNamespace(ip="3.3.3.2"),
                    port=30000,
                    create_at=timezone.now() - timedelta(hours=72),
                ),
                create_at=timezone.now() - timedelta(hours=72),
            )
        ],
    )
    m2 = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.1"),
        port=30001,
        ejector_tuples=[
            SimpleNamespace(
                receiver=SimpleNamespace(
                    machine=SimpleNamespace(ip="3.3.3.3"),
                    port=30001,
                    create_at=timezone.now() - timedelta(hours=72),
                ),
                create_at=timezone.now() - timedelta(hours=72),
            )
        ],
    )
    cluster.storages = [m1, m2]
    cfg = _config()
    bklogs = [make_fullbackup_entry(status="to_backup_system_success", ip="3.3.3.2", port=30000)]
    with patch(_PATCH_FIND, return_value=set()):
        rows = _task()._check_cluster(cluster, bklogs, cfg)
    assert len(rows) >= 2
    assert rows[0].state != ST.NORMAL.value


# ---------------------------------------------------------------------------
# _collect_instance_pairs
# ---------------------------------------------------------------------------
def test_collect_instance_pairs_normal(mock_cluster, mock_config):
    slaves, masters, s2m, switched = _task_cls()._collect_instance_pairs(mock_cluster, mock_config)
    assert len(slaves) == 2
    assert len(masters) == 2
    assert all(s in s2m for s in slaves)
    assert switched == {}


def test_collect_instance_pairs_no_ejector_skipped(mock_config):
    cluster = MagicMock()
    cluster.storages = [SimpleNamespace(machine=SimpleNamespace(ip="3.3.3.1"), port=30000, ejector_tuples=None)]
    slaves, masters, s2m, switched = _task_cls()._collect_instance_pairs(cluster, mock_config)
    assert slaves == []


def test_collect_instance_pairs_young_slave_skipped(mock_config):
    cluster = MagicMock()
    young_slave = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.2"),
        port=30000,
        create_at=timezone.now() - timedelta(hours=1),
    )
    master = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.1"),
        port=30000,
        ejector_tuples=[SimpleNamespace(receiver=young_slave, create_at=timezone.now() - timedelta(hours=72))],
    )
    cluster.storages = [master]
    slaves, masters, s2m, switched = _task_cls()._collect_instance_pairs(cluster, mock_config)
    assert slaves == []


def test_collect_instance_pairs_recently_switched(mock_config):
    """Tuple created 6h ago (within 48h threshold) -> slave in recently_switched."""
    cluster = MagicMock()
    cluster.immute_domain = "test.example.db"
    slave = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.2"),
        port=30000,
        create_at=timezone.now() - timedelta(hours=72),
    )
    master = SimpleNamespace(
        machine=SimpleNamespace(ip="3.3.3.1"),
        port=30000,
        ejector_tuples=[SimpleNamespace(receiver=slave, create_at=timezone.now() - timedelta(hours=6))],
    )
    cluster.storages = [master]
    slaves, masters, s2m, switched = _task_cls()._collect_instance_pairs(cluster, mock_config)
    assert len(slaves) == 1
    assert "3.3.3.2:30000" in switched
    assert switched["3.3.3.2:30000"] == 6


def test_start_ingests_portrait_and_survives_ingest_failure():
    from backend.db_report.portrait.redis_dimensions import RedisPortraitDimensionCode

    task = _task()
    cluster = _make_cluster()
    row = SimpleNamespace(
        state=_state().ABNORMAL.value,
        cluster=cluster.immute_domain,
        bk_biz_id=cluster.bk_biz_id,
        msg="missing backup",
    )
    cfg = _config()
    patches = [
        patch(
            "backend.db_periodic_task.local_tasks.redis_backup.check_full_backup.RedisBackupCheckConfig.from_settings",
            return_value=cfg,
        ),
        patch("backend.db_periodic_task.local_tasks.redis_backup.check_full_backup.RedisBackupCheckBatchOps"),
        patch.object(task, "_get_cluster_ids", return_value=[1]),
        patch.object(task, "_get_cluster_queryset", return_value=[cluster]),
        patch(_PATCH_FETCH, return_value={cluster.immute_domain: []}),
        patch.object(task, "_check_cluster_with_retry", return_value=[row]),
    ]

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patch(
        "backend.db_periodic_task.local_tasks.redis_backup.check_full_backup.ingest_abnormal_cluster_rows"
    ) as ingest:
        task.start()

    ingest.assert_called_once()
    assert ingest.call_args.kwargs["prefix"] == "[全备]"
    assert ingest.call_args.kwargs["dimension"] == RedisPortraitDimensionCode.RELIABILITY

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patch(
        "backend.db_report.portrait.redis_ingest.ingest_summary",
        side_effect=RuntimeError("portrait boom"),
    ):
        task.start()
