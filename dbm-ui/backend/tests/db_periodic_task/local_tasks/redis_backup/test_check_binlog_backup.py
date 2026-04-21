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
# Tests for CheckBinlogBackupTask — _check_instance and _check_cluster.
#
# Source-module imports are done lazily to avoid triggering the
# ``local_tasks/__init__.py`` import chain.
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from .conftest import make_binlog_entry

pytestmark = pytest.mark.django_db

_PATCH_FIND = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.find_and_verify_failed_tasks"
_PATCH_IS_PLUS = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.is_tendisplus_instance_type"
_PATCH_IS_SSD = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.is_tendisssd_instance_type"
_PATCH_CLUSTER_CONFIG = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup._get_cluster_config"
_PATCH_FETCH_CLUSTER = (
    "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.fetch_cluster_backup_logs"
)
_PATCH_FETCH_IP = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.fetch_ip_backup_logs"
_PATCH_FETCH_INSTANCE = (
    "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.fetch_instance_backup_logs"
)

_DUMMY_START = timezone.now()
_DUMMY_END = timezone.now()


def _yesterday_local():
    """Today 00:00 local time as a naive datetime (used as analysis cutoff)."""
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


def _ts_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _task_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import CheckBinlogBackupTask

    return CheckBinlogBackupTask


def _report_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import RedisBackupClusterReport

    return RedisBackupClusterReport


def _state():
    from backend.db_report.enums import ReportStateType

    return ReportStateType


def _cluster_type():
    from backend.db_meta.enums import ClusterType

    return ClusterType


def _make_cluster(cluster_type=None):
    if cluster_type is None:
        cluster_type = _cluster_type().TwemproxyTendisSSDInstance.value
    cluster = MagicMock()
    cluster.bk_biz_id = 3
    cluster.bk_cloud_id = 0
    cluster.immute_domain = "test.example.db"
    cluster.cluster_type = cluster_type
    cluster.major_version = "7.0"
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


def _make_slave_master(slave_ip, slave_port, master_ip, master_port, slave_age_hours=72, tuple_age_hours=72):
    slave = SimpleNamespace(
        machine=SimpleNamespace(ip=slave_ip),
        port=slave_port,
        create_at=timezone.now() - timedelta(hours=slave_age_hours),
    )
    return SimpleNamespace(
        machine=SimpleNamespace(ip=master_ip),
        port=master_port,
        ejector_tuples=[SimpleNamespace(receiver=slave, create_at=timezone.now() - timedelta(hours=tuple_age_hours))],
    )


def _run_check_instance(bklogs, cluster=None, kvstorecount=None, ip="3.3.3.2", port="30000", analysis_end_local=None):
    if cluster is None:
        cluster = _make_cluster()
    report = _report_cls()(cluster, "binlog_backup")
    instance = f"{ip}:{port}"
    with patch(_PATCH_FIND, return_value=set()):
        _task()._check_instance(
            report, bklogs, cluster, instance, ip, port, kvstorecount, analysis_end_local=analysis_end_local
        )
    return report


def _cluster_with_slave(cluster_type=None):
    if cluster_type is None:
        cluster_type = _cluster_type().TwemproxyTendisSSDInstance.value
    cluster = _make_cluster(cluster_type)
    cluster.storages = [_make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000)]
    return cluster


# ---------------------------------------------------------------------------
# _check_instance
# ---------------------------------------------------------------------------
def test_check_instance_no_bklogs_abnormal():
    ST = _state()
    report = _run_check_instance([])
    records = report.records[ST.ABNORMAL.value]
    assert len(records) == 1
    assert "no logs found" in records[0]["msg"]


def test_check_instance_no_terminal_entries_warning():
    ST = _state()
    logs = [make_binlog_entry(status="to_backup_system_start", ip="3.3.3.2", port=30000)]
    report = _run_check_instance(logs)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "no terminal" in records[0]["msg"]


def test_check_instance_all_failed_warning():
    ST = _state()
    logs = [
        make_binlog_entry(
            status="to_backup_system_failed",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    report = _run_check_instance(logs)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "all" in records[0]["msg"] and "failed" in records[0]["msg"]


def test_check_instance_ssd_no_missing_normal():
    ST = _state()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=f"binlog-3.3.3.2-30000-{i}-1234.log.zst",
        )
        for i in range(5)
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_check_instance_ssd_with_gaps_warning():
    ST = _state()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-5-1234.log.zst",
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "seq gaps" in records[0]["msg"]


def test_check_instance_tendisplus_all_ok():
    ST = _state()
    CT = _cluster_type()
    cluster = _make_cluster(CT.TendisPredixyTendisplusCluster.value)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=f"binlog-3.3.3.2-30000-0-{i}-1234.log.zst",
        )
        for i in range(3)
    ]
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_IS_SSD, return_value=False):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=1)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1


def test_check_instance_tendisplus_kv_gaps_warning():
    ST = _state()
    CT = _cluster_type()
    cluster = _make_cluster(CT.TendisPredixyTendisplusCluster.value)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-0-1-1234.log.zst",
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-0-5-1234.log.zst",
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_IS_SSD, return_value=False):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=1)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "kv0" in records[0]["msg"]


def test_check_instance_tendisplus_kv_all_failed():
    ST = _state()
    CT = _cluster_type()
    cluster = _make_cluster(CT.TendisPredixyTendisplusCluster.value)
    logs = [
        make_binlog_entry(
            status="to_backup_system_failed",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-0-1-1234.log.zst",
        )
    ]
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_IS_SSD, return_value=False):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=1)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "failed" in records[0]["msg"]


# ---------------------------------------------------------------------------
# content-time filter (analysis_end_local) tests
# ---------------------------------------------------------------------------
def _ssd_filename(ip, port, idx, content_time):
    return f"binlog-{ip}-{port}-{idx}-{_ts_str(content_time)}.log.zst"


def _plus_filename(ip, port, kv, idx, content_time):
    return f"binlog-{ip}-{port}-{kv}-{idx}-{_ts_str(content_time)}.log.zst"


def test_check_instance_day_boundary_no_false_positive():
    """User scenario: idx=2 yesterday is uploaded too late (out of window),
    idx=3 today is in the buffer.  Without filter, [1, 3] would falsely
    flag idx=2 as missing.  With filter, today's idx=3 is excluded and
    only idx=1 remains -- no gap reported."""
    ST = _state()
    today_start = _yesterday_local()
    yesterday_late = today_start - timedelta(minutes=10)
    today_first_hour = today_start + timedelta(minutes=10)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 1, yesterday_late),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 3, today_first_hour),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_end_local=today_start)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_check_instance_tail_missing_within_yesterday_still_detected():
    """Genuine gap inside yesterday content (idx=3 missing between 1, 2, 4)
    must still be flagged even with the content-time filter active."""
    ST = _state()
    today_start = _yesterday_local()
    base = today_start - timedelta(hours=12)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, idx, base + timedelta(minutes=10 * idx)),
        )
        for idx in (1, 2, 4)
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_end_local=today_start)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "seq gaps" in records[0]["msg"]
    assert "3" in records[0]["msg"]


def test_check_instance_late_uploaded_yesterday_seq_in_buffer_normal():
    """idx=2 has yesterday content but uploaded after midnight (still in
    the 1h buffer window).  Buffer brings it in, content-time filter
    keeps it, no gap reported -- this validates the buffer's purpose."""
    ST = _state()
    today_start = _yesterday_local()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 1, today_start - timedelta(minutes=20)),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 2, today_start - timedelta(minutes=5)),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 3, today_start + timedelta(minutes=15)),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_end_local=today_start)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_check_instance_filename_timestamp_unparseable_excluded():
    """Entries whose file_name has an unparseable timestamp segment are
    treated as 'not yesterday' and excluded from gap analysis."""
    ST = _state()
    today_start = _yesterday_local()
    yest = today_start - timedelta(hours=2)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 1, yest),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_ssd_filename("3.3.3.2", 30000, 2, yest + timedelta(minutes=10)),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-99-not_a_timestamp.log.zst",
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_end_local=today_start)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1, f"unexpected report: {report.records}"


def test_check_instance_tendisplus_day_boundary_no_false_positive():
    """Same false-positive scenario, TendisPlus per-kvstore variant."""
    ST = _state()
    CT = _cluster_type()
    cluster = _make_cluster(CT.TendisPredixyTendisplusCluster.value)
    today_start = _yesterday_local()
    yest_late = today_start - timedelta(minutes=10)
    today_first = today_start + timedelta(minutes=20)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_plus_filename("3.3.3.2", 30000, 0, 1, yest_late),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_plus_filename("3.3.3.2", 30000, 0, 3, today_first),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_IS_SSD, return_value=False):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=1, analysis_end_local=today_start)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1


def test_check_instance_api_promoted_counted():
    ST = _state()
    logs = [
        make_binlog_entry(
            status="to_backup_system_start",
            ip="3.3.3.2",
            port=30000,
            task_id="tx",
            file_name="binlog-3.3.3.2-30000-0-1234.log.zst",
        )
    ]
    with (
        patch(_PATCH_FIND, return_value={"tx"}),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        cluster = _make_cluster()
        report = _report_cls()(cluster, "binlog_backup")
        _task()._check_instance(report, logs, cluster, "3.3.3.2:30000", "3.3.3.2", "30000", None)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1


# ---------------------------------------------------------------------------
# _check_cluster
# ---------------------------------------------------------------------------
def test_check_cluster_cloud_id_skip(mock_config):
    cluster = _cluster_with_slave()
    mock_config.target_bk_cloud_ids = [99]
    rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert "skipped" in rows[0].msg


def test_check_cluster_no_eligible_slaves(mock_config):
    cluster = _make_cluster()
    cluster.storages = [_make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000, slave_age_hours=1)]
    rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert "no eligible" in rows[0].msg


def test_check_cluster_kvstorecount_failure(mock_config):
    CT = _cluster_type()
    cluster = _cluster_with_slave(CT.TendisPredixyTendisplusCluster.value)
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_CLUSTER_CONFIG, side_effect=Exception("boom")):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert rows[0].state == _state().ABNORMAL.value
    assert "kvstorecount" in rows[0].msg


def test_check_cluster_normal_summary(mock_config):
    ST = _state()
    cluster = _cluster_with_slave()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=(logs, False)),
        patch(_PATCH_FIND, return_value=set()),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert rows[0].state == ST.NORMAL.value


def test_check_cluster_mixed_per_ip(mock_config):
    ST = _state()
    cluster = _make_cluster()
    cluster.storages = [
        _make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000),
        _make_slave_master("3.3.3.3", 30001, "3.3.3.1", 30001),
    ]
    all_logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=(all_logs, False)),
        patch(_PATCH_FIND, return_value=set()),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) >= 2
    assert rows[0].state == ST.ABNORMAL.value


def test_check_cluster_tiered_no_fallback(mock_config):
    """When cluster-level fetch is not truncated, no per-IP/instance calls."""
    cluster = _make_cluster()
    cluster.storages = [
        _make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000),
        _make_slave_master("3.3.3.3", 30001, "3.3.3.1", 30001),
    ]
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=([], False)) as mock_cluster,
        patch(_PATCH_FETCH_IP) as mock_ip,
        patch(_PATCH_FETCH_INSTANCE) as mock_inst,
        patch(_PATCH_FIND, return_value=set()),
    ):
        _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert mock_cluster.call_count == 1
    assert mock_ip.call_count == 0
    assert mock_inst.call_count == 0


def test_check_cluster_tiered_fallback_to_ip(mock_config):
    """Cluster truncated -> falls back to per-IP; no per-instance calls."""
    cluster = _make_cluster()
    cluster.storages = [
        _make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000),
    ]
    ip_logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=([], True)),
        patch(_PATCH_FETCH_IP, return_value=(ip_logs, False)) as mock_ip,
        patch(_PATCH_FETCH_INSTANCE) as mock_inst,
        patch(_PATCH_FIND, return_value=set()),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert mock_ip.call_count == 1
    assert mock_inst.call_count == 0
    assert rows[0].state == _state().NORMAL.value


def test_check_cluster_tiered_fallback_to_instance(mock_config):
    """Cluster and IP both truncated -> falls back to per-instance."""
    cluster = _make_cluster()
    cluster.storages = [
        _make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000),
    ]
    inst_logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=([], True)),
        patch(_PATCH_FETCH_IP, return_value=([], True)),
        patch(_PATCH_FETCH_INSTANCE, return_value=inst_logs) as mock_inst,
        patch(_PATCH_FIND, return_value=set()),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert mock_inst.call_count == 1
    assert rows[0].state == _state().NORMAL.value
