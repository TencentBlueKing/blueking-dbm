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
import json
import logging
import random
import time
from collections import defaultdict
from typing import Dict, List

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.components.mysql_backup.client import RedisBackupApi
from backend.db_periodic_task.constants import BACKUP_TASK_SUCCESS
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str

logger = logging.getLogger("root")

DEFAULT_PAGE_SIZE = 10000
MAX_RETRIES = 3
DOMAIN_BATCH_SIZE = 50
INTER_PAGE_DELAY = 0.5
BACKUP_API_BATCH_SIZE = 100
ES_MAX_RESULT_WINDOW = 10000


def _convert_log(bk_log: Dict) -> Dict:
    """Convert a snake_case BKLog entry to our internal field names."""
    return {
        "cluster_domain": bk_log.get("domain", ""),
        "task_id": bk_log.get("backup_taskid", ""),
        "file_type": bk_log.get("backup_tag", ""),
        "uptime": bk_log.get("end_time", ""),
        "backup_status": bk_log.get("status", ""),
        "backup_status_info": bk_log.get("message", ""),
        "redis_ip": bk_log.get("server_ip", ""),
        "redis_port": bk_log.get("server_port", ""),
        "redis_role": bk_log.get("role", ""),
        "file_size": int(bk_log.get("backup_file_size", 0)),
        "file_name": bk_log.get("backup_file", "").split("/")[-1],
        "file_last_mtime": bk_log.get("start_time", ""),
    }


def batch_fetch_backup_logs(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    domains: list[str],
) -> dict[str, list[dict]]:
    """Fetch backup logs for a list of domains and group by domain.

    Builds a Lucene OR query: ``domain: (d1 OR d2 OR ... OR dN)``.
    If the result set is truncated by the ES ``max_result_window`` limit,
    the domain list is split in half and each half is fetched separately
    (recursive subdivision) so that no data is lost.
    """
    if not domains:
        return {}

    query_string = "domain: (" + " OR ".join(domains) + ")"
    raw_logs, truncated = _get_log_from_bklog(collector, start_time, end_time, query_string=query_string)

    if truncated and len(domains) > 1:
        mid = len(domains) // 2
        result = batch_fetch_backup_logs(collector, start_time, end_time, domains[:mid])
        right = batch_fetch_backup_logs(collector, start_time, end_time, domains[mid:])
        for domain, logs in right.items():
            result[domain].extend(logs)
        return result

    if truncated and len(domains) <= 1:
        logger.warning(
            "Single-domain batch for %s still exceeds ES max_result_window; results are truncated",
            domains[0] if domains else "?",
        )

    result: dict[str, list[dict]] = defaultdict(list)
    for log in raw_logs:
        result[log.get("domain", "")].append(_convert_log(log))
    return result


def fetch_cluster_backup_logs(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    domain: str,
) -> tuple[list[dict], bool]:
    """Fetch backup logs for a single cluster domain.

    Returns ``(converted_logs, truncated)``.  The caller can decide
    whether to fall back to a narrower query when *truncated* is True.
    """
    query_string = f"domain: {domain}"
    raw_logs, truncated = _get_log_from_bklog(collector, start_time, end_time, query_string=query_string)
    return [_convert_log(log) for log in raw_logs], truncated


def fetch_ip_backup_logs(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    domain: str,
    ip: str,
) -> tuple[list[dict], bool]:
    """Fetch backup logs scoped to one IP across all ports on a domain.

    Returns ``(converted_logs, truncated)``.  If truncated, the caller
    should fall back to :func:`fetch_instance_backup_logs` per port.
    """
    query_string = f"domain: {domain} AND server_ip: {ip}"
    raw_logs, truncated = _get_log_from_bklog(collector, start_time, end_time, query_string=query_string)
    return [_convert_log(log) for log in raw_logs], truncated


def fetch_instance_backup_logs(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    domain: str,
    ip: str,
    port: str | int,
) -> list[dict]:
    """Fetch backup logs for a single instance, queried by domain + ip + port.

    Unlike :func:`batch_fetch_backup_logs` which queries by domain only,
    this scopes the ES query to one instance so that large clusters
    (e.g. high-volume binlog producers) are far less likely to exceed
    ES ``max_result_window``.
    """
    query_string = f"domain: {domain} AND server_ip: {ip} AND server_port: {port}"
    raw_logs, truncated = _get_log_from_bklog(collector, start_time, end_time, query_string=query_string)
    if truncated:
        logger.warning(
            "Instance %s:%s on %s exceeds ES max_result_window; results are truncated",
            ip,
            port,
            domain,
        )
    return [_convert_log(log) for log in raw_logs]


def _get_log_from_bklog(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    query_string: str = "*",
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[List[Dict], bool]:
    """Fetch logs from BKLog with automatic pagination and retry.

    Paginates through results using ``start`` offset until all hits are
    retrieved or ES returns fewer results than *page_size*.

    Returns ``(logs, truncated)`` where *truncated* is ``True`` when
    pagination was stopped because the next page would exceed
    ``ES_MAX_RESULT_WINDOW``.
    """
    all_logs: List[Dict] = []
    offset = 0
    truncated = False

    while True:
        if offset > 0:
            time.sleep(INTER_PAGE_DELAY)

        resp = _esquery_with_retry(collector, start_time, end_time, query_string, offset, page_size)
        if resp is None:
            break

        hits = resp.get("hits", {}).get("hits", [])
        for hit in hits:
            try:
                raw_log = json.loads(hit["_source"]["log"])
                all_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse BKLog hit: %s", e)
                continue

        if len(hits) < page_size:
            break
        offset += len(hits)

        if offset + page_size > ES_MAX_RESULT_WINDOW:
            truncated = True
            logger.warning(
                "BKLog results truncated at %d for %s (next page would exceed ES max_result_window=%d)",
                offset,
                collector,
                ES_MAX_RESULT_WINDOW,
            )
            break

    return all_logs, truncated


def _esquery_with_retry(
    collector: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    query_string: str,
    offset: int,
    size: int,
) -> dict | None:
    """Call BKLogApi.esquery_search with exponential backoff + jitter on failure."""
    params = {
        "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
        "start_time": datetime2str(start_time),
        "end_time": datetime2str(end_time),
        "query_string": query_string,
        "start": offset,
        "size": size,
        "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
    }
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return BKLogApi.esquery_search(params, use_admin=True)
        except Exception as e:
            if "Result window is too large" in str(e):
                logger.warning("ES max_result_window exceeded for %s (offset=%d): %s", collector, offset, e)
                return None
            last_error = e
            delay = min(2**attempt + random.uniform(0, 1), 30)
            logger.warning(
                "BKLog query attempt %d/%d failed for %s (offset=%d): %s, retrying in %.1fs",
                attempt + 1,
                MAX_RETRIES,
                collector,
                offset,
                e,
                delay,
            )
            time.sleep(delay)

    logger.error("BKLog query exhausted retries for %s: %s", collector, last_error)
    return None


def find_and_verify_failed_tasks(bklogs: list[dict]) -> set[str]:
    """Identify task_ids that appear failed in BKLog and verify them against the backup system API.

    A task_id is considered "failed" when it has a ``to_backup_system_start`` entry
    but no ``to_backup_system_success`` entry (i.e. the upload was initiated but
    never reported as successful in BKLog).

    Returns the subset of those task_ids that the backup system API confirms as
    successfully uploaded (status == BACKUP_TASK_SUCCESS).  On API error the
    function fails open and returns an empty set so the original BKLog-based
    verdict is preserved.
    """
    statuses_by_task: dict[str, set[str]] = defaultdict(set)
    for entry in bklogs:
        task_id = entry.get("task_id", "")
        status = entry.get("backup_status", "")
        if task_id and status:
            statuses_by_task[task_id].add(status)

    failed_task_ids = [
        tid
        for tid, statuses in statuses_by_task.items()
        if "to_backup_system_start" in statuses and "to_backup_system_success" not in statuses
    ]

    if not failed_task_ids:
        return set()

    logger.info("Verifying %d failed task_ids via backup system API", len(failed_task_ids))

    api_results: list[dict] = []
    try:
        for i in range(0, len(failed_task_ids), BACKUP_API_BATCH_SIZE):
            batch = failed_task_ids[i : i + BACKUP_API_BATCH_SIZE]
            api_results.extend(RedisBackupApi.query_for_task_ids({"task_ids": batch}))
    except Exception as e:
        logger.error("Backup system API unavailable, skipping cross-check (fail-open): %s", e)
        return set()

    confirmed: set[str] = set()
    for info in api_results:
        if info.get("status") == BACKUP_TASK_SUCCESS:
            confirmed.add(str(info.get("task_id", "")))

    if confirmed:
        logger.info("Backup system API confirmed %d/%d task_ids as successful", len(confirmed), len(failed_task_ids))

    return confirmed
