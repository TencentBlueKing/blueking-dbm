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
# Tests are organised into six categories that mirror the distinct
# responsibilities exercised by the implementation:
#
#   A. Input-shape preconditions for _check_instance
#      (early-return branches: no logs, no terminal entries, all failed)
#   B. Yesterday-only gap detection
#      (_find_missing_binlogs over yesterday's content, no buffer involved)
#   C. Content-time filtering
#      (_in_window excludes leading/trailing buffer entries from yesterday_logs)
#   D. Buffer-fill defensive behaviour
#      (the missing -= fillable subtraction in _find_missing_binlogs)
#   E. API promotion via find_and_verify_failed_tasks
#   F. _check_cluster orchestration
#      (skip rules, error paths, end-to-end runs, tiered fetch fallback)
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

# Sentinel timestamp for tests where filename content time is irrelevant
# (the content-time filter is inactive because analysis_*_local is None).
_DONT_CARE_TS = datetime(2024, 1, 1, 12, 0, 0)


def _yesterday_start_local():
    """Yesterday 00:00 local time as a naive datetime.

    Mirrors the production ``analysis_window.start``.  Tests derive
    ``today_start = yesterday_start + timedelta(days=1)`` when they need
    the upper bound, so all timing anchors are expressed relative to
    the same reference point.
    """
    today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    return today_start - timedelta(days=1)


def _ts_str(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


def _task_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import CheckBinlogBackupTask

    return CheckBinlogBackupTask


def _analysis_window(start, end):
    """Build an ``AnalysisWindow`` with a lazy import.

    Mirrors the lazy-import pattern used elsewhere in this module to
    avoid triggering the ``local_tasks/__init__.py`` chain at test
    collection time.
    """
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import AnalysisWindow

    return AnalysisWindow(start=start, end=end)


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


def _run_check_instance(
    bklogs,
    cluster=None,
    kvstorecount=None,
    ip="3.3.3.2",
    port="30000",
    analysis_window=None,
):
    if cluster is None:
        cluster = _make_cluster()
    report = _report_cls()(cluster, "binlog_backup")
    instance = f"{ip}:{port}"
    with patch(_PATCH_FIND, return_value=set()):
        _task()._check_instance(
            report,
            bklogs,
            cluster,
            instance,
            ip,
            port,
            kvstorecount,
            analysis_window=analysis_window,
        )
    return report


def _cluster_with_slave(cluster_type=None):
    if cluster_type is None:
        cluster_type = _cluster_type().TwemproxyTendisSSDInstance.value
    cluster = _make_cluster(cluster_type)
    cluster.storages = [_make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000)]
    return cluster


def _binlog_filename(cluster_type, ip, port, idx, content_time, kv=0):
    """Build a binlog filename matching the cluster type's layout.

    TendisSSD:  binlog-{ip}-{port}-{idx}-{ts}.log.zst
    TendisPlus: binlog-{ip}-{port}-{kv}-{idx}-{ts}.log.zst
    """
    if cluster_type == _cluster_type().TendisPredixyTendisplusCluster.value:
        return f"binlog-{ip}-{port}-{kv}-{idx}-{_ts_str(content_time)}.log.zst"
    return f"binlog-{ip}-{port}-{idx}-{_ts_str(content_time)}.log.zst"


# Variant fixtures for tests that should exercise both SSD and TendisPlus
# code paths with the same scenario shape.  ``is_plus`` toggles the
# ``is_tendisplus_instance_type`` / ``is_tendisssd_instance_type``
# patches; ``kvstorecount`` is None for SSD and 1 for TendisPlus.
_VARIANT_PARAMS = [
    pytest.param(False, None, id="ssd"),
    pytest.param(True, 1, id="tendisplus"),
]


def _variant_cluster(is_plus):
    CT = _cluster_type()
    if is_plus:
        return _make_cluster(CT.TendisPredixyTendisplusCluster.value)
    return _make_cluster(CT.TwemproxyTendisSSDInstance.value)


# ===========================================================================
# Class A: input-shape preconditions for _check_instance
# ===========================================================================
def test_input_no_bklogs_abnormal():
    """Empty ``bklogs`` is the strongest abnormal signal: BKLog returned
    nothing for the instance even after the 1h leading and trailing
    buffer hours, so report ABNORMAL ``no logs found``."""
    ST = _state()
    report = _run_check_instance([])
    records = report.records[ST.ABNORMAL.value]
    assert len(records) == 1
    assert "no logs found" in records[0]["msg"]


def test_input_only_non_terminal_warning():
    """All entries are ``to_backup_system_start`` with no terminal
    statuses anywhere -- nothing to verify.  Report WARNING ``no
    terminal binlog status found``."""
    ST = _state()
    logs = [make_binlog_entry(status="to_backup_system_start", ip="3.3.3.2", port=30000)]
    report = _run_check_instance(logs)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "no terminal" in records[0]["msg"]


@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_input_all_uploads_failed_warning(is_plus, kvstorecount):
    """Every terminal entry is ``to_backup_system_failed`` -- the
    ``success_count == 0`` branch fires before any cluster-type-specific
    logic, so both SSD and TendisPlus produce the same WARNING."""
    ST = _state()
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_failed",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(cluster.cluster_type, "3.3.3.2", 30000, 1, _DONT_CARE_TS),
        )
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=kvstorecount)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "all" in records[0]["msg"] and "failed" in records[0]["msg"]


# ===========================================================================
# Class B: yesterday-only gap detection
# ===========================================================================
@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_yesterday_no_gap_normal(is_plus, kvstorecount):
    """Contiguous successful indexes produce NORMAL for both cluster
    types."""
    ST = _state()
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(cluster.cluster_type, "3.3.3.2", 30000, i, _DONT_CARE_TS),
        )
        for i in range(3)
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=kvstorecount)
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_yesterday_with_gap_warning(is_plus, kvstorecount):
    """An interior gap between the observed min and max indexes is
    flagged for both cluster types.  TendisPlus reports the gap
    per-kvstore (``kv0(...)``); SSD reports it as ``seq gaps``."""
    ST = _state()
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(cluster.cluster_type, "3.3.3.2", 30000, idx, _DONT_CARE_TS),
        )
        for idx in (1, 5)
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(logs, cluster=cluster, kvstorecount=kvstorecount)
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    if is_plus:
        assert "kv0" in records[0]["msg"]
    else:
        assert "seq gaps (2-4)" in records[0]["msg"]


def test_yesterday_real_gap_detected_with_filter():
    """Genuine interior gap in yesterday content (idx=3 missing between
    1, 2, 4) must still be flagged when the content-time filter is
    active -- the filter removes neighbouring-day boundary noise but
    must not hide real gaps."""
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    base = today_start - timedelta(hours=12)
    CT = _cluster_type()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                CT.TwemproxyTendisSSDInstance.value,
                "3.3.3.2",
                30000,
                idx,
                base + timedelta(minutes=10 * idx),
            ),
        )
        for idx in (1, 2, 4)
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_window=_analysis_window(yesterday_start, today_start))
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "seq gaps" in records[0]["msg"]
    assert "3" in records[0]["msg"]


# ===========================================================================
# Class C: content-time filtering (_in_window)
# ===========================================================================
@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_filter_excludes_trailing_buffer(is_plus, kvstorecount):
    """User scenario: idx=2 yesterday is uploaded too late (out of
    window), idx=3 today is in the trailing buffer.  Without the
    filter, [1, 3] would falsely flag idx=2 as missing.  With the
    filter, today's idx=3 is excluded and only idx=1 remains -- no
    gap reported.  Exercised for both SSD and TendisPlus."""
    ST = _state()
    cluster = _variant_cluster(is_plus)
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    yest_late = today_start - timedelta(minutes=10)
    today_first = today_start + timedelta(minutes=20)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(cluster.cluster_type, "3.3.3.2", 30000, 1, yest_late),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(cluster.cluster_type, "3.3.3.2", 30000, 3, today_first),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(
            logs,
            cluster=cluster,
            kvstorecount=kvstorecount,
            analysis_window=_analysis_window(yesterday_start, today_start),
        )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1


def test_filter_excludes_leading_buffer():
    """Mirror of the trailing-buffer case for the leading edge.

    idx=1 is day-before-yesterday content that landed in the leading
    buffer hour, idx=3 is yesterday content.  Without the filter,
    [1, 3] would falsely flag idx=2 as missing.  With the filter,
    idx=1 is excluded and only idx=3 remains in yesterday_logs -- no
    gap reported.
    """
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    dby_late = yesterday_start - timedelta(minutes=10)
    yest_mid = yesterday_start + timedelta(hours=12)
    CT = _cluster_type()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(CT.TwemproxyTendisSSDInstance.value, "3.3.3.2", 30000, 1, dby_late),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(CT.TwemproxyTendisSSDInstance.value, "3.3.3.2", 30000, 3, yest_mid),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(
            logs,
            analysis_window=_analysis_window(yesterday_start, today_start),
        )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_filter_retains_yesterday_late_content():
    """Yesterday-late content (just before midnight) must be retained
    and today-first-hour content must be excluded.

    Yesterday content [1, 2] is contiguous, so there is no gap to
    fill -- this test asserts the filter's *retention* behaviour for
    yesterday-late uploads alongside its *exclusion* behaviour for
    today's first-hour entries.
    """
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    CT = _cluster_type()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                CT.TwemproxyTendisSSDInstance.value,
                "3.3.3.2",
                30000,
                1,
                today_start - timedelta(minutes=20),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                CT.TwemproxyTendisSSDInstance.value,
                "3.3.3.2",
                30000,
                2,
                today_start - timedelta(minutes=5),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                CT.TwemproxyTendisSSDInstance.value,
                "3.3.3.2",
                30000,
                3,
                today_start + timedelta(minutes=15),
            ),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_window=_analysis_window(yesterday_start, today_start))
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


def test_filter_excludes_unparseable_filename():
    """Entries whose ``file_name`` has an unparseable timestamp segment
    are treated as 'not yesterday' and excluded from gap analysis
    via the ``ts is None`` short-circuit in ``_in_window``.  This is
    fail-safe: an unparseable filename can never cause a false
    positive."""
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    yest = today_start - timedelta(hours=2)
    CT = _cluster_type()
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(CT.TwemproxyTendisSSDInstance.value, "3.3.3.2", 30000, 1, yest),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                CT.TwemproxyTendisSSDInstance.value,
                "3.3.3.2",
                30000,
                2,
                yest + timedelta(minutes=10),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-99-not_a_timestamp.log.zst",
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=False), patch(_PATCH_IS_SSD, return_value=True):
        report = _run_check_instance(logs, analysis_window=_analysis_window(yesterday_start, today_start))
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1, f"unexpected report: {report.records}"


# ===========================================================================
# Class D: buffer-fill defensive behaviour (missing -= fillable)
# ===========================================================================
#
# Note on the two ``*_fills_gap_defensive`` tests below: under
# monotonic binlog rotation (T_i < T_j whenever i < j), neither
# scenario can physically occur.  They construct invariant-violating
# orderings (idx=2 with content time earlier than idx=1) on purpose,
# to validate the defensive ``missing -= fillable`` subtraction in
# ``_find_missing_binlogs``.  If the buffer-fill subtraction were
# removed, these tests would fail; in real-world traffic where
# monotonicity holds, that line is a no-op.
@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_buffer_leading_fills_gap_defensive(is_plus, kvstorecount):
    """Defensive scenario: idx=1 yesterday, idx=2 in the leading buffer
    (DBY content), idx=3 yesterday.  This ordering cannot occur under
    monotonic rotation; the test exists to ensure ``missing -=
    fillable`` continues to suppress the would-be gap so a future
    invariant violation (e.g. counter reset, clock skew) does not
    cause a false positive."""
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                1,
                yesterday_start + timedelta(minutes=5),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                2,
                yesterday_start - timedelta(minutes=5),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                3,
                yesterday_start + timedelta(minutes=10),
            ),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(
            logs,
            cluster=cluster,
            kvstorecount=kvstorecount,
            analysis_window=_analysis_window(yesterday_start, today_start),
        )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_buffer_trailing_fills_gap_defensive(is_plus, kvstorecount):
    """Mirror of the leading-buffer defensive case, on the trailing
    edge.  Same invariant-violating ordering (idx=2 with content time
    later than idx=3) -- not physically possible under monotonic
    rotation, but kept as a safety net for the buffer-fill
    subtraction."""
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                1,
                today_start - timedelta(minutes=10),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                2,
                today_start + timedelta(minutes=10),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                3,
                today_start - timedelta(minutes=5),
            ),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(
            logs,
            cluster=cluster,
            kvstorecount=kvstorecount,
            analysis_window=_analysis_window(yesterday_start, today_start),
        )
    records = report.records[ST.NORMAL.value]
    assert len(records) == 1
    assert records[0]["msg"] == "ok"


@pytest.mark.parametrize("is_plus,kvstorecount", _VARIANT_PARAMS)
def test_buffer_does_not_mask_yesterday_failure(is_plus, kvstorecount):
    """Buffer-success entries must NOT suppress a known yesterday
    failure.  If idx=2 is FAILED in yesterday and a same-index entry
    appears as success in the buffer (different binlog file, content
    time in DBY), the failure stays reported -- this guards against
    the buffer-fill subtraction over-reaching into known failures.
    """
    ST = _state()
    yesterday_start = _yesterday_start_local()
    today_start = yesterday_start + timedelta(days=1)
    cluster = _variant_cluster(is_plus)
    logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                1,
                yesterday_start + timedelta(minutes=5),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_failed",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                2,
                yesterday_start + timedelta(minutes=10),
            ),
        ),
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name=_binlog_filename(
                cluster.cluster_type,
                "3.3.3.2",
                30000,
                2,
                yesterday_start - timedelta(minutes=10),
            ),
        ),
    ]
    with patch(_PATCH_IS_PLUS, return_value=is_plus), patch(_PATCH_IS_SSD, return_value=not is_plus):
        report = _run_check_instance(
            logs,
            cluster=cluster,
            kvstorecount=kvstorecount,
            analysis_window=_analysis_window(yesterday_start, today_start),
        )
    records = report.records[ST.WARNING.value]
    assert len(records) == 1
    assert "2" in records[0]["msg"]


# ===========================================================================
# Class E: API promotion via find_and_verify_failed_tasks
# ===========================================================================
def test_api_promoted_task_counted_as_success():
    """A ``to_backup_system_start`` entry with no terminal sibling can
    still count as success when the backup-system API confirms the
    task_id -- exercises the promotion path that injects API-confirmed
    starts into both ``all_terminal`` and ``success_entries``."""
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


# ===========================================================================
# Class F: _check_cluster orchestration
# ===========================================================================
def test_cluster_skips_unmatched_cloud_id(mock_config):
    cluster = _cluster_with_slave()
    mock_config.target_bk_cloud_ids = [99]
    rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert "skipped" in rows[0].msg


def test_cluster_skips_when_no_eligible_slaves(mock_config):
    cluster = _make_cluster()
    cluster.storages = [_make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000, slave_age_hours=1)]
    rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert "no eligible" in rows[0].msg


def test_cluster_kvstorecount_fetch_failure_abnormal(mock_config):
    CT = _cluster_type()
    cluster = _cluster_with_slave(CT.TendisPredixyTendisplusCluster.value)
    with patch(_PATCH_IS_PLUS, return_value=True), patch(_PATCH_CLUSTER_CONFIG, side_effect=Exception("boom")):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert len(rows) == 1
    assert rows[0].state == _state().ABNORMAL.value
    assert "kvstorecount" in rows[0].msg


def test_cluster_normal_end_to_end(mock_config):
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


def test_cluster_mixed_per_ip_end_to_end(mock_config):
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


@pytest.mark.parametrize(
    "cluster_truncated,ip_truncated,expected_ip_calls,expected_inst_calls",
    [
        pytest.param(False, False, 0, 0, id="no_fallback"),
        pytest.param(True, False, 1, 0, id="fallback_to_ip"),
        pytest.param(True, True, 1, 1, id="fallback_to_instance"),
    ],
)
def test_cluster_tiered_fetch_fallback(
    mock_config, cluster_truncated, ip_truncated, expected_ip_calls, expected_inst_calls
):
    """Tiered BKLog fetch narrows scope on truncation:
    cluster -> per-IP -> per-instance.  At each truncation level the
    next tier is invoked exactly once per IP/instance; at the
    not-truncated tier the deeper tiers are not called."""
    cluster = _make_cluster()
    cluster.storages = [_make_slave_master("3.3.3.2", 30000, "3.3.3.1", 30000)]
    success_logs = [
        make_binlog_entry(
            status="to_backup_system_success",
            ip="3.3.3.2",
            port=30000,
            file_name="binlog-3.3.3.2-30000-1-1234.log.zst",
        )
    ]
    cluster_logs = [] if cluster_truncated else success_logs
    ip_logs = [] if ip_truncated else success_logs
    with (
        patch(_PATCH_FETCH_CLUSTER, return_value=(cluster_logs, cluster_truncated)) as mock_cluster,
        patch(_PATCH_FETCH_IP, return_value=(ip_logs, ip_truncated)) as mock_ip,
        patch(_PATCH_FETCH_INSTANCE, return_value=success_logs) as mock_inst,
        patch(_PATCH_FIND, return_value=set()),
        patch(_PATCH_IS_PLUS, return_value=False),
        patch(_PATCH_IS_SSD, return_value=True),
    ):
        rows = _task()._check_cluster(cluster, _DUMMY_START, _DUMMY_END, mock_config)
    assert mock_cluster.call_count == 1
    assert mock_ip.call_count == expected_ip_calls
    assert mock_inst.call_count == expected_inst_calls
    assert rows[0].state == _state().NORMAL.value
