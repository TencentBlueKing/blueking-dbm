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
import datetime
from unittest.mock import patch

"""
Tests for bklog_query.py — _convert_log, find_and_verify_failed_tasks, batch_fetch_backup_logs.

Source-module imports are done lazily to avoid triggering the
``local_tasks/__init__.py`` import chain.
"""

_PATCH_ESQUERY = "backend.db_periodic_task.local_tasks.redis_backup.bklog_query.BKLogApi.esquery_search"
_PATCH_BACKUP_API = "backend.db_periodic_task.local_tasks.redis_backup.bklog_query.RedisBackupApi.query_for_task_ids"
_PATCH_GET_LOG = "backend.db_periodic_task.local_tasks.redis_backup.bklog_query._get_log_from_bklog"


def _convert_log(raw):
    from backend.db_periodic_task.local_tasks.redis_backup.bklog_query import _convert_log

    return _convert_log(raw)


def _find_and_verify(bklogs):
    from backend.db_periodic_task.local_tasks.redis_backup.bklog_query import find_and_verify_failed_tasks

    return find_and_verify_failed_tasks(bklogs)


def _batch_fetch(*a, **kw):
    from backend.db_periodic_task.local_tasks.redis_backup.bklog_query import batch_fetch_backup_logs

    return batch_fetch_backup_logs(*a, **kw)


def _backup_task_success():
    from backend.db_periodic_task.constants import BACKUP_TASK_SUCCESS

    return BACKUP_TASK_SUCCESS


def _log_result(domains):
    logs = []
    for d in domains:
        logs.append(
            {
                "domain": d,
                "backup_taskid": "t1",
                "status": "to_backup_system_success",
                "backup_tag": "",
                "end_time": "",
                "message": "",
                "server_ip": "1.1.1.1",
                "server_port": "30000",
                "role": "",
                "backup_file_size": "0",
                "backup_file": "f.tar",
                "start_time": "",
            }
        )
    return logs, False


# ---------------------------------------------------------------------------
# _convert_log
# ---------------------------------------------------------------------------
def test_convert_log_field_mapping():
    raw = {
        "domain": "test.db",
        "backup_taskid": "t42",
        "backup_tag": "full",
        "end_time": "2024-01-15T05:30:00",
        "status": "to_backup_system_success",
        "message": "",
        "server_ip": "3.3.3.1",
        "server_port": "30000",
        "role": "slave",
        "backup_file_size": "1024",
        "backup_file": "/data/dbbak/full-backup.tar",
        "start_time": "2024-01-15T05:00:00",
    }
    result = _convert_log(raw)
    assert result["cluster_domain"] == "test.db"
    assert result["task_id"] == "t42"
    assert result["file_type"] == "full"
    assert result["uptime"] == "2024-01-15T05:30:00"
    assert result["backup_status"] == "to_backup_system_success"
    assert result["redis_ip"] == "3.3.3.1"
    assert result["redis_port"] == "30000"
    assert result["file_size"] == 1024
    assert result["file_name"] == "full-backup.tar"


def test_convert_log_missing_fields():
    result = _convert_log({})
    assert result["cluster_domain"] == ""
    assert result["task_id"] == ""
    assert result["file_size"] == 0
    assert result["file_name"] == ""


# ---------------------------------------------------------------------------
# find_and_verify_failed_tasks
# ---------------------------------------------------------------------------
def test_find_verify_no_stuck_tasks():
    bklogs = [{"task_id": "t1", "backup_status": "to_backup_system_success"}]
    result = _find_and_verify(bklogs)
    assert result == set()


def test_find_verify_stuck_confirmed():
    bklogs = [{"task_id": "t1", "backup_status": "to_backup_system_start"}]
    with patch(_PATCH_BACKUP_API, return_value=[{"task_id": "t1", "status": _backup_task_success()}]):
        result = _find_and_verify(bklogs)
    assert result == {"t1"}


def test_find_verify_stuck_not_confirmed():
    bklogs = [{"task_id": "t1", "backup_status": "to_backup_system_start"}]
    with patch(_PATCH_BACKUP_API, return_value=[{"task_id": "t1", "status": 99}]):
        result = _find_and_verify(bklogs)
    assert result == set()


def test_find_verify_api_failure_returns_empty():
    bklogs = [{"task_id": "t1", "backup_status": "to_backup_system_start"}]
    with patch(_PATCH_BACKUP_API, side_effect=Exception("API down")):
        result = _find_and_verify(bklogs)
    assert result == set()


def test_find_verify_success_entry_prevents_api_call():
    bklogs = [
        {"task_id": "t1", "backup_status": "to_backup_system_start"},
        {"task_id": "t1", "backup_status": "to_backup_system_success"},
    ]
    with patch(_PATCH_BACKUP_API) as mock_api:
        result = _find_and_verify(bklogs)
    mock_api.assert_not_called()
    assert result == set()


# ---------------------------------------------------------------------------
# batch_fetch_backup_logs
# ---------------------------------------------------------------------------
def test_batch_fetch_normal_grouped():
    start = datetime.datetime(2024, 1, 15)
    end = datetime.datetime(2024, 1, 16)
    domains = ["d1.db", "d2.db"]
    with patch(_PATCH_GET_LOG, return_value=_log_result(domains)):
        result = _batch_fetch("collector", start, end, domains)
    assert "d1.db" in result
    assert "d2.db" in result
    assert len(result["d1.db"]) == 1


def test_batch_fetch_truncated_triggers_subdivision():
    start = datetime.datetime(2024, 1, 15)
    end = datetime.datetime(2024, 1, 16)
    domains = ["d1.db", "d2.db"]

    call_count = 0

    def _mock_get_log(collector, s, e, query_string="*", page_size=10000):
        nonlocal call_count
        call_count += 1
        if "d1" in query_string and "d2" in query_string:
            return [], True
        domain = "d1.db" if "d1" in query_string else "d2.db"
        return _log_result([domain])

    with patch(_PATCH_GET_LOG, side_effect=_mock_get_log):
        result = _batch_fetch("collector", start, end, domains)
    assert call_count == 3
    assert "d1.db" in result
    assert "d2.db" in result


def test_batch_fetch_empty_domains():
    result = _batch_fetch("collector", datetime.datetime(2024, 1, 15), datetime.datetime(2024, 1, 16), [])
    assert result == {}
