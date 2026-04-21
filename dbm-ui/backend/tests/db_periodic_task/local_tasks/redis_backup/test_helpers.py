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
import datetime as _dt
from unittest.mock import patch

import pytest

# Pure function tests — no DB, minimal mocking.
# All source-module imports are done inside test functions to avoid triggering
# the ``local_tasks/__init__.py`` import chain that registers periodic tasks.
# ---------------------------------------------------------------------------
# lazy-import helpers
# ---------------------------------------------------------------------------


def _parse_backup_hour(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import _parse_backup_hour

    return _parse_backup_hour(*a, **kw)


def _map_to_schedule_slot(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import _map_to_schedule_slot

    return _map_to_schedule_slot(*a, **kw)


def _find_missing_slots(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import _find_missing_slots

    return _find_missing_slots(*a, **kw)


def _find_off_schedule_backups(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import _find_off_schedule_backups

    return _find_off_schedule_backups(*a, **kw)


def _format_hours(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_full_backup import _format_hours

    return _format_hours(*a, **kw)


def _compress_ranges(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import _compress_ranges

    return _compress_ranges(*a, **kw)


def _format_ranges(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import _format_ranges

    return _format_ranges(*a, **kw)


def _extract_binlog_index(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import _extract_binlog_index

    return _extract_binlog_index(*a, **kw)


def _extract_binlog_timestamp(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import _extract_binlog_timestamp

    return _extract_binlog_timestamp(*a, **kw)


def _find_missing_binlogs(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup import _find_missing_binlogs

    return _find_missing_binlogs(*a, **kw)


def _compress_port_ranges(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import _compress_port_ranges

    return _compress_port_ranges(*a, **kw)


def _format_port_ranges(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import _format_port_ranges

    return _format_port_ranges(*a, **kw)


def _group_records_by_ip(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import _group_records_by_ip

    return _group_records_by_ip(*a, **kw)


_IS_PLUS = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.is_tendisplus_instance_type"
_IS_SSD = "backend.db_periodic_task.local_tasks.redis_backup.check_binlog_backup.is_tendisssd_instance_type"


# ---------------------------------------------------------------------------
# _parse_backup_hour
# ---------------------------------------------------------------------------
def test_parse_backup_hour_go_time_format():
    assert _parse_backup_hour("2024-01-15T05:30:00+08:00") == 5


def test_parse_backup_hour_space_format():
    assert _parse_backup_hour("2024-01-15 13:45:00") == 13


def test_parse_backup_hour_none():
    assert _parse_backup_hour(None) is None


def test_parse_backup_hour_empty():
    assert _parse_backup_hour("") is None


def test_parse_backup_hour_short_string():
    assert _parse_backup_hour("2024-01-15") is None


def test_parse_backup_hour_non_numeric():
    assert _parse_backup_hour("2024-01-15TXX:00:00") is None


# ---------------------------------------------------------------------------
# _map_to_schedule_slot
# ---------------------------------------------------------------------------
def test_map_to_schedule_slot_exact_match():
    assert _map_to_schedule_slot(5, [5, 13, 21]) == 5


def test_map_to_schedule_slot_between_slots():
    assert _map_to_schedule_slot(7, [5, 13, 21]) == 5


def test_map_to_schedule_slot_after_last():
    assert _map_to_schedule_slot(23, [5, 13, 21]) == 21


def test_map_to_schedule_slot_before_first_wraps():
    assert _map_to_schedule_slot(3, [5, 13, 21]) == 21


def test_map_to_schedule_slot_single():
    assert _map_to_schedule_slot(12, [5]) == 5


def test_map_to_schedule_slot_single_before():
    assert _map_to_schedule_slot(3, [5]) == 5


# ---------------------------------------------------------------------------
# _find_missing_slots
# ---------------------------------------------------------------------------
def test_find_missing_slots_all_covered():
    times = ["2024-01-15T05:30:00+08:00", "2024-01-15T14:00:00+08:00", "2024-01-15T22:00:00+08:00"]
    assert _find_missing_slots(times, [5, 13, 21]) == []


def test_find_missing_slots_some_missing():
    times = ["2024-01-15T05:30:00+08:00"]
    assert _find_missing_slots(times, [5, 13, 21]) == [13, 21]


def test_find_missing_slots_empty_times():
    assert _find_missing_slots([], [5, 13, 21]) == [5, 13, 21]


# ---------------------------------------------------------------------------
# _find_off_schedule_backups
# ---------------------------------------------------------------------------
def test_find_off_schedule_within_threshold():
    times = ["2024-01-15T06:30:00+08:00"]
    assert _find_off_schedule_backups(times, [5], 2.5) == []


def test_find_off_schedule_beyond_threshold():
    times = ["2024-01-15T10:00:00+08:00"]
    result = _find_off_schedule_backups(times, [5], 2.5)
    assert len(result) == 1
    assert result[0] == (times[0], 10, 5)


def test_find_off_schedule_empty():
    assert _find_off_schedule_backups([], [5], 2.5) == []


def test_find_off_schedule_none_hour_skipped():
    assert _find_off_schedule_backups(["short"], [5], 2.5) == []


# ---------------------------------------------------------------------------
# _format_hours
# ---------------------------------------------------------------------------
def test_format_hours_single():
    assert _format_hours([5]) == "05:00"


def test_format_hours_multiple():
    assert _format_hours([5, 13, 21]) == "05:00, 13:00, 21:00"


def test_format_hours_empty():
    assert _format_hours([]) == ""


# ---------------------------------------------------------------------------
# _compress_ranges (binlog)
# ---------------------------------------------------------------------------
def test_compress_ranges_consecutive():
    assert _compress_ranges([1, 2, 3]) == [(1, 3)]


def test_compress_ranges_gaps():
    assert _compress_ranges([1, 2, 5, 6]) == [(1, 2), (5, 6)]


def test_compress_ranges_single():
    assert _compress_ranges([42]) == [(42, 42)]


def test_compress_ranges_empty():
    assert _compress_ranges([]) == []


def test_compress_ranges_unsorted():
    assert _compress_ranges([5, 3, 4, 1]) == [(1, 1), (3, 5)]


# ---------------------------------------------------------------------------
# _format_ranges (binlog)
# ---------------------------------------------------------------------------
def test_format_ranges_basic():
    assert _format_ranges([(42, 44), (78, 78)]) == "42-44, 78"


def test_format_ranges_capped():
    ranges = [(i, i) for i in range(20)]
    result = _format_ranges(ranges, max_display=3)
    assert "...and 17 more" in result


def test_format_ranges_empty():
    assert _format_ranges([]) == ""


# ---------------------------------------------------------------------------
# _extract_binlog_index
# ---------------------------------------------------------------------------
def test_extract_binlog_index_tendisplus():
    with patch(_IS_PLUS, return_value=True), patch(_IS_SSD, return_value=False):
        assert _extract_binlog_index("binlog-3.3.3.2-30000-0-42-1234.log.zst", "TendisPlus") == 42


def test_extract_binlog_index_tendisssd():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        assert _extract_binlog_index("binlog-3.3.3.2-30000-99-1234.log.zst", "TendisSSD") == 99


def test_extract_binlog_index_invalid_type():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=False):
        with pytest.raises(ValueError, match="unsupported"):
            _extract_binlog_index("binlog-a-b-c-d.log", "UnknownType")


# ---------------------------------------------------------------------------
# _extract_binlog_timestamp
# ---------------------------------------------------------------------------
def test_extract_binlog_timestamp_tendisplus():
    with patch(_IS_PLUS, return_value=True), patch(_IS_SSD, return_value=False):
        ts = _extract_binlog_timestamp("binlog-1.2.3.4-30000-5-0022670-20251216171459.log.zst", "TendisPlus")
        assert ts == _dt.datetime(2025, 12, 16, 17, 14, 59)


def test_extract_binlog_timestamp_tendisssd():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        ts = _extract_binlog_timestamp("binlog-1.3.3.79-30009-0014018-20251216171048.log.zst", "TendisSSD")
        assert ts == _dt.datetime(2025, 12, 16, 17, 10, 48)


def test_extract_binlog_timestamp_unparseable_returns_none():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        assert _extract_binlog_timestamp("binlog-ip-30000-99-not_a_timestamp.log.zst", "TendisSSD") is None


def test_extract_binlog_timestamp_too_few_parts_returns_none():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        assert _extract_binlog_timestamp("binlog-only.log.zst", "TendisSSD") is None


def test_extract_binlog_timestamp_unsupported_type_returns_none():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=False):
        assert _extract_binlog_timestamp("binlog-a-b-c-20251216171048.log.zst", "Unknown") is None


# ---------------------------------------------------------------------------
# _find_missing_binlogs
# ---------------------------------------------------------------------------
def test_find_missing_binlogs_no_gaps():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        entries = [{"file_name": f"binlog-ip-30000-{i}-ts.log.zst"} for i in range(5)]
        assert _find_missing_binlogs(entries, entries, "ssd") == []


def test_find_missing_binlogs_interior_gaps():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        terminal = [
            {"file_name": "binlog-ip-30000-1-ts.log.zst"},
            {"file_name": "binlog-ip-30000-5-ts.log.zst"},
        ]
        assert _find_missing_binlogs(terminal, terminal, "ssd") == [2, 3, 4]


def test_find_missing_binlogs_failed_uploads():
    with patch(_IS_PLUS, return_value=False), patch(_IS_SSD, return_value=True):
        terminal = [
            {"file_name": "binlog-ip-30000-1-ts.log.zst"},
            {"file_name": "binlog-ip-30000-2-ts.log.zst"},
        ]
        success = [{"file_name": "binlog-ip-30000-1-ts.log.zst"}]
        assert _find_missing_binlogs(terminal, success, "ssd") == [2]


def test_find_missing_binlogs_empty():
    assert _find_missing_binlogs([], [], "ssd") == []


# ---------------------------------------------------------------------------
# _compress_port_ranges
# ---------------------------------------------------------------------------
def test_compress_port_ranges_consecutive():
    assert _compress_port_ranges([30000, 30001, 30002]) == [(30000, 30002)]


def test_compress_port_ranges_gaps():
    assert _compress_port_ranges([30000, 30001, 30005]) == [(30000, 30001), (30005, 30005)]


def test_compress_port_ranges_duplicates():
    assert _compress_port_ranges([30000, 30000, 30001]) == [(30000, 30001)]


def test_compress_port_ranges_empty():
    assert _compress_port_ranges([]) == []


# ---------------------------------------------------------------------------
# _format_port_ranges
# ---------------------------------------------------------------------------
def test_format_port_ranges_single():
    assert _format_port_ranges([(30005, 30005)]) == "30005"


def test_format_port_ranges_range():
    assert _format_port_ranges([(30000, 30002)]) == "30000~30002"


def test_format_port_ranges_mixed():
    assert _format_port_ranges([(30000, 30002), (30005, 30005)]) == "30000~30002, 30005"


# ---------------------------------------------------------------------------
# _group_records_by_ip
# ---------------------------------------------------------------------------
def test_group_records_single_ip_multiple_ports():
    records = [
        {"instance": "3.3.3.1:30000", "state": "normal", "msg": "ok"},
        {"instance": "3.3.3.1:30001", "state": "normal", "msg": "ok"},
    ]
    result = _group_records_by_ip(records)
    assert len(result) == 1
    assert result[0]["instance"] == "3.3.3.1"
    assert result[0]["state"] == "normal"


def test_group_records_multiple_ips():
    records = [
        {"instance": "3.3.3.1:30000", "state": "normal", "msg": "ok"},
        {"instance": "3.3.3.2:30000", "state": "abnormal", "msg": "failed"},
    ]
    result = _group_records_by_ip(records)
    assert len(result) == 2


def test_group_records_worst_state_wins():
    records = [
        {"instance": "3.3.3.1:30000", "state": "normal", "msg": "ok"},
        {"instance": "3.3.3.1:30001", "state": "abnormal", "msg": "failed"},
    ]
    result = _group_records_by_ip(records)
    assert len(result) == 1
    assert result[0]["state"] == "abnormal"


def test_group_records_passthrough_all_instance():
    records = [{"instance": "all", "state": "normal", "msg": "summary"}]
    result = _group_records_by_ip(records)
    assert len(result) == 1
    assert result[0]["instance"] == "all"


def test_group_records_message_dedup():
    records = [
        {"instance": "3.3.3.1:30000", "state": "normal", "msg": "ok"},
        {"instance": "3.3.3.1:30000", "state": "normal", "msg": "ok"},
    ]
    result = _group_records_by_ip(records)
    assert result[0]["msg"] == "30000: ok"
