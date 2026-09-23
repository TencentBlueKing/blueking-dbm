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

from typing import Dict, List, Sequence

from django.utils.translation import gettext as _

from backend.components.mysql_backup.client import RedisBackupApi
from backend.db_services.redis.rollback.exceptions import RollbackPlanError

BACKUP_QUERY_BATCH_SIZE = 100
BACKUP_TASK_SUCCESS = 4
_NOT_EXPIRED = {None, "", 0, "0", False, "false", "False"}


def confirm_backup_tasks(task_ids_by_shard: Dict[str, Sequence[str]]) -> Dict[str, List[str]]:
    """Ask the backup system whether each planned task_id is still downloadable.

    Empty shard lists are skipped (placeholder instances). An API failure raises
    ``RollbackPlanError`` so callers fail the whole plan instead of continuing to download.
    """
    problems: Dict[str, List[str]] = {}
    wanted: Dict[str, List[str]] = {}
    query_ids: List[str] = []
    for shard, raw_ids in task_ids_by_shard.items():
        ids: List[str] = []
        for raw in raw_ids or []:
            task_id = str(raw or "").strip()
            if not task_id:
                problems.setdefault(shard, []).append(_("分片 {} 缺少 backup_taskid").format(shard))
                continue
            ids.append(task_id)
            query_ids.append(task_id)
        if ids:
            wanted[shard] = ids
    if not query_ids:
        return problems

    try:
        rows = _query_task_ids(query_ids)
    except RollbackPlanError:
        raise
    except Exception as exc:  # pylint: disable=broad-except
        raise RollbackPlanError(context={"message": _("无法向备份系统确认文件仍在: {}").format(exc)})

    by_id = {}
    for row in rows:
        task_id = str((row or {}).get("task_id") or "").strip()
        if task_id:
            by_id[task_id] = row

    for shard, ids in wanted.items():
        for task_id in ids:
            row = by_id.get(task_id)
            if row is None:
                problems.setdefault(shard, []).append(_("分片 {} 的备份 {} 在备份系统中不存在或已过期").format(shard, task_id))
                continue
            if _marked_expired(row):
                problems.setdefault(shard, []).append(_("分片 {} 的备份 {} 已过期").format(shard, task_id))
                continue
            if not _status_ok(row.get("status")):
                problems.setdefault(shard, []).append(_("分片 {} 的备份 {} 上传状态不是成功").format(shard, task_id))
    return problems


def _query_task_ids(task_ids: Sequence[str]) -> List[dict]:
    unique = list(dict.fromkeys(task_ids))
    rows: List[dict] = []
    for offset in range(0, len(unique), BACKUP_QUERY_BATCH_SIZE):
        batch = unique[offset : offset + BACKUP_QUERY_BATCH_SIZE]
        result = RedisBackupApi.query_for_task_ids({"task_ids": batch})
        if result is None:
            continue
        if not isinstance(result, list):
            raise RollbackPlanError(context={"message": _("备份系统返回的文件列表无法解析")})
        rows.extend(result)
    return rows


def _status_ok(status) -> bool:
    try:
        return int(status) == BACKUP_TASK_SUCCESS
    except (TypeError, ValueError):
        return False


def _marked_expired(row: dict) -> bool:
    if "expired" not in row:
        return False
    return row.get("expired") not in _NOT_EXPIRED
