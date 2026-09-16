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

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.db_meta.models import Cluster
from backend.db_report.models.redis_backup_result import RedisBackupResult
from backend.db_services.redis.rollback.constants import (
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
    BACKUP_STATUS_SUCCESS,
    LOCATOR_SOURCE_BKLOG,
    LOCATOR_SOURCE_TABLE,
)
from backend.db_services.redis.rollback.shards import round_key_from_filename
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str

logger = logging.getLogger("flow")

_REQUIRED_FIELDS = ("backup_taskid", "backup_file", "backup_host", "backup_port")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_iso(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return _as_utc(dt).isoformat()


def row_to_backup_system_format(row) -> Dict[str, Any]:
    """Convert a table row or bklog dict into backup-system style record."""
    if isinstance(row, dict):
        file_name = (row.get("backup_file") or "").split("/")[-1]
        size = int(row.get("backup_file_size") or 0)
        begin = row.get("start_time") or row.get("backup_begin_time") or ""
        end = row.get("end_time") or row.get("backup_end_time") or ""
        return {
            "file_tag": row.get("backup_tag") or "",
            "status": row.get("status") or row.get("backup_status") or "",
            "uptime": end,
            "file_last_mtime": begin,
            "size": size,
            "source_ip": row.get("server_ip") or row.get("backup_host") or "",
            "server_port": int(row.get("server_port") or row.get("backup_port") or 0),
            "task_id": str(row.get("backup_taskid") or ""),
            "file_name": file_name,
            "shard_value": row.get("shard_value") or "",
            "backup_identify": row.get("backup_identify") or "",
            "backup_begin_time": begin,
            "backup_end_time": end,
            "round_key": round_key_from_filename(file_name),
        }

    file_name = (row.backup_file or "").split("/")[-1]
    return {
        "file_tag": row.backup_tag or "",
        "status": row.backup_status or "",
        "uptime": _dt_iso(row.backup_end_time),
        "file_last_mtime": _dt_iso(row.backup_begin_time),
        "size": int(row.backup_file_size or 0),
        "source_ip": row.backup_host or "",
        "server_port": int(row.backup_port or 0),
        "task_id": str(row.backup_taskid or ""),
        "file_name": file_name,
        "shard_value": row.shard_value or "",
        "backup_identify": row.backup_identify or "",
        "backup_begin_time": _dt_iso(row.backup_begin_time),
        "backup_end_time": _dt_iso(row.backup_end_time),
        "round_key": round_key_from_filename(file_name),
    }


class BackupLocator:
    """Locate full backups by (immute_domain, shard_value). Table first, BKLog fallback.

    Phase 1 implements the full-backup path only. Binlog lookup is a stub.
    """

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.locator_source = LOCATOR_SOURCE_TABLE

    def locate_full_by_identify(self, backup_identify: str) -> List[Dict[str, Any]]:
        if not backup_identify:
            return []
        records = self._query_table(backup_identify=backup_identify)
        if records is None:
            self.locator_source = LOCATOR_SOURCE_BKLOG
            records = self._query_bklog(backup_identify=backup_identify)
        return records

    def locate_full_by_task_ids(self, task_ids: Sequence[str]) -> List[Dict[str, Any]]:
        task_ids = [str(t) for t in task_ids if t]
        if not task_ids:
            return []
        records = self._query_table(task_ids=task_ids)
        if records is None:
            self.locator_source = LOCATOR_SOURCE_BKLOG
            records = self._query_bklog(task_ids=task_ids)
        return records

    def list_full_in_window(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        records = self._query_table(start_time=start_time, end_time=end_time)
        if records is None:
            self.locator_source = LOCATOR_SOURCE_BKLOG
            records = self._query_bklog(start_time=start_time, end_time=end_time)
        return records

    def _query_table(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        backup_identify: Optional[str] = None,
        task_ids: Optional[Sequence[str]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            qs = RedisBackupResult.objects.using("report_db").filter(
                immute_domain=self.cluster.immute_domain,
                backup_status=BACKUP_STATUS_SUCCESS,
            )
            if backup_identify:
                qs = qs.filter(backup_identify=backup_identify)
            if task_ids:
                qs = qs.filter(backup_taskid__in=list(task_ids))
            if start_time:
                qs = qs.filter(backup_end_time__gte=_as_utc(start_time))
            if end_time:
                qs = qs.filter(backup_end_time__lte=_as_utc(end_time))
            rows = list(qs)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "BackupLocator table query failed for %s, fallback bklog: %s",
                self.cluster.immute_domain,
                exc,
            )
            self.locator_source = LOCATOR_SOURCE_BKLOG
            return None

        if not rows:
            logger.info(
                "BackupLocator table empty for domain=%s identify=%s, fallback bklog",
                self.cluster.immute_domain,
                backup_identify,
            )
            self.locator_source = LOCATOR_SOURCE_BKLOG
            return None

        converted = []
        for row in rows:
            if any(not getattr(row, field, None) for field in _REQUIRED_FIELDS):
                logger.warning("BackupLocator skip row id=%s missing required fields", getattr(row, "id", None))
                continue
            converted.append(row_to_backup_system_format(row))
        if not converted:
            self.locator_source = LOCATOR_SOURCE_BKLOG
            return None
        self.locator_source = LOCATOR_SOURCE_TABLE
        return converted

    def _query_bklog(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        backup_identify: Optional[str] = None,
        task_ids: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        self.locator_source = LOCATOR_SOURCE_BKLOG
        end_time = end_time or datetime.now(timezone.utc)
        start_time = start_time or (end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS))
        clauses = [
            f"domain: {self.cluster.immute_domain}",
            f"status: {BACKUP_STATUS_SUCCESS}",
        ]
        if backup_identify:
            clauses.append(f'backup_identify: "{backup_identify}"')
        if task_ids:
            id_clause = " OR ".join([f'backup_taskid: "{tid}"' for tid in task_ids])
            clauses.append(f"({id_clause})")
        query_string = " AND ".join(clauses)
        raw_logs = self._esquery(start_time, end_time, query_string)
        return [row_to_backup_system_format(log) for log in raw_logs]

    def _esquery(self, start_time: datetime, end_time: datetime, query_string: str) -> List[Dict]:
        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.redis_fullbackup_result",
                "start_time": datetime2str(_as_utc(start_time)),
                "end_time": datetime2str(_as_utc(end_time)),
                "query_string": query_string,
                "start": 0,
                "size": 6000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            },
            use_admin=True,
        )
        backup_logs = []
        for hit in resp.get("hits", {}).get("hits", []):
            raw_log = json.loads(hit["_source"]["log"])
            backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})
        return backup_logs
