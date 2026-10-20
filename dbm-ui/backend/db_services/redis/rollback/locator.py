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
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from django.utils import timezone as dj_timezone

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.redis_backup_result import RedisBackupResult, RedisBinlogResult
from backend.db_services.redis.rollback.binlogs import binlog_index, plus_binlog_position
from backend.db_services.redis.rollback.constants import (
    BACKUP_IDENTIFY_WINDOW_DAYS,
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
    BACKUP_STATUS_SUCCESS,
    BINLOG_LOOKUP_MARGIN_HOURS,
    LOCATOR_SOURCE_BKLOG,
    LOCATOR_SOURCE_TABLE,
    SINGLE_INSTANCE_SHARD_VALUE,
    TENDISPLUS_TYPES,
)
from backend.db_services.redis.rollback.shards import round_key_from_filename, source_role
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str, str2datetime

logger = logging.getLogger("flow")

_REQUIRED_FIELDS = ("backup_taskid", "backup_file", "backup_host", "backup_port")

_BKLOG_PAGE_SIZE = 5000
# A query past this many hits is too broad to trust; BKLog is then treated as failed.
_BKLOG_MAX_HITS = 100000


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_iso(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return _as_utc(dt).isoformat()


def _iso_utc(value) -> str:
    """BKLog times are RFC3339 in the host's zone; render them like table times so both sources sort together."""
    if not value:
        return ""
    try:
        dt = str2datetime(value, aware_check=False)
    except (ValueError, OverflowError):
        logger.warning("BackupLocator unparseable time %r", value)
        return ""
    if dj_timezone.is_naive(dt):
        dt = dj_timezone.make_aware(dt, dj_timezone.get_default_timezone())
    return _dt_iso(dt)


def row_to_backup_system_format(row) -> Dict[str, Any]:
    """Convert a table row or bklog dict into backup-system style record. Times are UTC ISO strings."""
    if isinstance(row, dict):
        file_name = (row.get("backup_file") or "").split("/")[-1]
        size = int(row.get("backup_file_size") or 0)
        begin = _iso_utc(row.get("start_time") or row.get("backup_begin_time"))
        end = _iso_utc(row.get("end_time") or row.get("backup_end_time"))
        return {
            "file_tag": row.get("backup_tag") or "",
            "status": row.get("status") or row.get("backup_status") or "",
            "uptime": end,
            "file_last_mtime": begin,
            "size": size,
            "source_ip": row.get("server_ip") or row.get("backup_host") or "",
            "server_port": int(row.get("server_port") or row.get("backup_port") or 0),
            "source_role": source_role(row.get("redis_role") or row.get("role"), file_name),
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
        "source_role": source_role(row.redis_role, file_name),
        "task_id": str(row.backup_taskid or ""),
        "file_name": file_name,
        "shard_value": row.shard_value or "",
        "backup_identify": row.backup_identify or "",
        "backup_begin_time": _dt_iso(row.backup_begin_time),
        "backup_end_time": _dt_iso(row.backup_end_time),
        "round_key": round_key_from_filename(file_name),
    }


_IDENTIFY_HOUR = re.compile(r"-(\d{10})$")


def identify_window(backup_identify: str) -> Optional[Tuple[datetime, datetime]]:
    """BKLog window for a batch stamped ``...-YYYYMMDDHH``; None when the identify carries no hour.

    dbmon stamps the hour in host local time, taken to be the platform's time zone.
    """
    match = _IDENTIFY_HOUR.search(backup_identify or "")
    if not match:
        return None
    try:
        start = datetime.strptime(match.group(1), "%Y%m%d%H")
    except ValueError:
        return None
    start = dj_timezone.make_aware(start, dj_timezone.get_default_timezone())
    return _as_utc(start), _as_utc(start) + timedelta(days=BACKUP_IDENTIFY_WINDOW_DAYS)


def dedupe(records: Sequence[Dict[str, Any]], *keys: str) -> List[Dict[str, Any]]:
    """BKLog holds every report twice; keep the first record of each key."""
    seen, unique = set(), []
    for record in records:
        key = tuple(record.get(k) for k in keys)
        if not any(key):
            unique.append(record)
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def merge_sources(
    table: Optional[List[Dict[str, Any]]], bklog: Optional[Sequence[Dict[str, Any]]]
) -> Tuple[List[Dict[str, Any]], bool]:
    """Table records first, then BKLog, one per ``(task_id, file_name)``. None marks a failed source.

    Returns the merged records and whether BKLog had to answer: the table failed (None), was
    empty, or BKLog added files the table lacks.
    """
    bklog = list(bklog or [])
    merged = dedupe(list(table or []) + bklog, "task_id", "file_name")
    bklog_ids = {id(record) for record in bklog}
    return merged, not table or any(id(record) in bklog_ids for record in merged)


def _convert(
    logs: Sequence[Dict[str, Any]], convert: Callable[[Dict[str, Any]], Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """A malformed log is skipped alone; the rest of the batch still counts."""
    records = []
    for log in logs:
        try:
            records.append(convert(log))
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("BackupLocator skip bklog record %s: %s", log.get("backup_file"), exc)
    return records


def binlog_record(
    file_name: str, task_id, size, source_ip: str, source_port, begin_time, plus: bool = False
) -> Dict[str, Any]:
    """``index`` is None for a name that is not a binlog of the engine; Tendisplus adds ``kvstore``."""
    file_name = (file_name or "").split("/")[-1]
    if isinstance(begin_time, str):
        begin_time = str2datetime(begin_time) if begin_time else None
    kvstore, index = 0, binlog_index(file_name)
    if plus:
        kvstore, index = plus_binlog_position(file_name) or (0, None)
    return {
        "task_id": str(task_id or ""),
        "file_name": file_name,
        "size": int(size or 0),
        "source_ip": source_ip or "",
        "source_port": int(source_port or 0),
        "begin_time": _as_utc(begin_time) if begin_time else None,
        "index": index,
        "kvstore": kvstore,
    }


class BackupLocator:
    """Locate full backups by (immute_domain, shard_value) and binlogs by source instance.

    While the result table is rolled out, every query asks both the table and BKLog and merges
    the two by ``(task_id, file_name)``, table records first. ``locator_source`` describes the
    latest full backup query: ``table`` only when every merged record came from the table.
    """

    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.locator_source = LOCATOR_SOURCE_TABLE
        self._plus = cluster.cluster_type in TENDISPLUS_TYPES

    def locate_full_by_identify(self, backup_identify: str) -> List[Dict[str, Any]]:
        if not backup_identify:
            return []
        table = self._query_table(backup_identify=backup_identify)
        window = identify_window(backup_identify)
        start_time, end_time = window if window else (None, None)
        bklog = self._query_bklog(start_time=start_time, end_time=end_time, backup_identify=backup_identify)
        return self._merge_full("identify={}".format(backup_identify), table, bklog)

    def locate_full_by_task_ids(self, task_ids: Sequence[str]) -> List[Dict[str, Any]]:
        task_ids = [str(t) for t in task_ids if t]
        if not task_ids:
            return []
        table = self._query_table(task_ids=task_ids)
        bklog = self._query_bklog(task_ids=task_ids)
        return self._merge_full("task_ids={}".format(len(task_ids)), table, bklog)

    def list_full_in_window(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        table = self._query_table(start_time=start_time, end_time=end_time)
        bklog = self._query_bklog(start_time=start_time, end_time=end_time)
        return self._merge_full("window", table, bklog)

    def locate_binlogs(
        self, source_ip: str, source_port: int, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Binlogs of one source instance begun within the window widened by the lookup margin.

        Only files named with a parseable index are returned; ``begin_time`` is the time in the name.
        """
        margin = timedelta(hours=BINLOG_LOOKUP_MARGIN_HOURS)
        start_time, end_time = _as_utc(start_time) - margin, _as_utc(end_time) + margin
        table = self._query_binlog_table(source_ip, source_port, start_time, end_time)
        bklog = self._query_binlog_bklog(source_ip, source_port, start_time, end_time)
        records, _from_bklog = merge_sources(table, bklog)
        self._log_merge("binlogs of {}:{}".format(source_ip, source_port), table, bklog, records)
        return [r for r in records if r["index"] is not None and r["begin_time"] is not None]

    def _query_binlog_table(self, source_ip, source_port, start_time, end_time) -> Optional[List[Dict[str, Any]]]:
        try:
            rows = RedisBinlogResult.objects.using("report_db").filter(
                immute_domain=self.cluster.immute_domain,
                backup_host=source_ip,
                backup_port=source_port,
                backup_status=BACKUP_STATUS_SUCCESS,
                backup_begin_time__gte=start_time,
                backup_begin_time__lte=end_time,
            )
            return [
                binlog_record(
                    row.backup_file,
                    row.backup_taskid,
                    row.backup_file_size,
                    row.backup_host,
                    row.backup_port,
                    row.backup_begin_time,
                    plus=self._plus,
                )
                for row in rows
            ]
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("BackupLocator binlog table query failed for %s:%s: %s", source_ip, source_port, exc)
            return None

    def _query_binlog_bklog(self, source_ip, source_port, start_time, end_time) -> Optional[List[Dict[str, Any]]]:
        query_string = f"server_ip: {source_ip} AND server_port: {source_port} AND status: {BACKUP_STATUS_SUCCESS}"
        # Logs are indexed by report time, which trails the file's begin time.
        logs = self._esquery(
            start_time,
            end_time + timedelta(hours=BINLOG_LOOKUP_MARGIN_HOURS),
            query_string,
            collector="redis_binlog_backup_result",
        )
        if logs is None:
            return None
        records = _convert(
            logs,
            lambda log: binlog_record(
                log.get("backup_file"),
                log.get("backup_taskid"),
                log.get("backup_file_size"),
                log.get("server_ip"),
                log.get("server_port"),
                log.get("start_time"),
                plus=self._plus,
            ),
        )
        records = dedupe(records, "task_id", "file_name")
        return [r for r in records if r["begin_time"] and start_time <= r["begin_time"] <= end_time]

    def _merge_full(
        self, detail: str, table: Optional[List[Dict[str, Any]]], bklog: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        records, from_bklog = merge_sources(table, bklog)
        self.locator_source = LOCATOR_SOURCE_BKLOG if from_bklog else LOCATOR_SOURCE_TABLE
        self._log_merge(detail, table, bklog, records)
        if self.cluster.cluster_type == ClusterType.TendisRedisInstance.value:
            # dbmon reports a master-slave cluster's only shard with an empty shard_value.
            for record in records:
                record["shard_value"] = record["shard_value"] or SINGLE_INSTANCE_SHARD_VALUE
        return records

    def _log_merge(
        self, detail: str, table: Optional[List[Dict[str, Any]]], bklog: Optional[List[Dict[str, Any]]], merged
    ):
        """Counts per source, kept so the result table's coverage can be measured before BKLog is dropped."""
        logger.info(
            "BackupLocator %s %s: table=%s bklog=%s merged=%s",
            self.cluster.immute_domain,
            detail,
            "error" if table is None else len(table),
            "error" if bklog is None else len(bklog),
            len(merged),
        )

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
            logger.exception("BackupLocator table query failed for %s: %s", self.cluster.immute_domain, exc)
            return None

        converted = []
        for row in rows:
            if any(not getattr(row, field, None) for field in _REQUIRED_FIELDS):
                logger.warning("BackupLocator skip row id=%s missing required fields", getattr(row, "id", None))
                continue
            converted.append(row_to_backup_system_format(row))
        return converted

    def _query_bklog(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        backup_identify: Optional[str] = None,
        task_ids: Optional[Sequence[str]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """``backup_identify`` is not an extracted field of the collector, so it is matched after parsing."""
        end_time = end_time or datetime.now(timezone.utc)
        start_time = start_time or (end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS))
        clauses = [
            f"domain: {self.cluster.immute_domain}",
            f"status: {BACKUP_STATUS_SUCCESS}",
        ]
        if task_ids:
            id_clause = " OR ".join([f'backup_taskid: "{tid}"' for tid in task_ids])
            clauses.append(f"({id_clause})")
        query_string = " AND ".join(clauses)
        logs = self._esquery(start_time, end_time, query_string)
        if logs is None:
            return None
        records = _convert(dedupe(logs, "backup_taskid", "backup_file"), row_to_backup_system_format)
        if backup_identify:
            records = [r for r in records if r["backup_identify"] == backup_identify]
        return records

    def _esquery(
        self, start_time: datetime, end_time: datetime, query_string: str, collector: str = "redis_fullbackup_result"
    ) -> Optional[List[Dict]]:
        """Every hit, paged by ``search_after``. None when BKLog fails, times out or matches too many
        logs, so the caller keeps what the table found instead of a partial answer."""
        hits, search_after = [], []
        try:
            while True:
                resp = BKLogApi.esquery_search(
                    {
                        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
                        "start_time": datetime2str(_as_utc(start_time)),
                        "end_time": datetime2str(_as_utc(end_time)),
                        "query_string": query_string,
                        "start": 0,
                        "size": _BKLOG_PAGE_SIZE,
                        "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
                        "search_after": search_after,
                    },
                    use_admin=True,
                )
                page = resp.get("hits", {}).get("hits", [])
                hits.extend(page)
                if len(page) < _BKLOG_PAGE_SIZE:
                    break
                if len(hits) >= _BKLOG_MAX_HITS:
                    logger.error(
                        "BackupLocator bklog %s matched over %d logs for %s, ignored",
                        collector,
                        len(hits),
                        query_string,
                    )
                    return None
                search_after = page[-1]["sort"]
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("BackupLocator bklog %s query failed for %s: %s", collector, query_string, exc)
            return None
        backup_logs = []
        for hit in hits:
            try:
                raw_log = json.loads(hit["_source"]["log"])
                backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                logger.warning("BackupLocator skip unparseable bklog hit in %s: %s", collector, exc)
        return backup_logs
