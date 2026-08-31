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
import hashlib
import re
import uuid
from collections.abc import Sequence

from backend.flow.utils.mysql.dts.constants import MigrateTopology

# DTS 会在任务名后拼 `_lightning_checkpoint_list` 建 checkpoint 表，
# 生成名必须小于 50，避免表名超长；MysqlDtsInfo.dts_task_id 列仍为 64
TASK_NAME_MAX_LEN = 49
TASK_NAME_PREFIX = "mysql-dts"
# 超长时对完整候选名取 sha1 短哈希（hex）
TASK_NAME_HASH_HEX_LEN = 8
# 多行 infos：同源同目标但迁移对象不同时，用随机后缀区分 task_name
TASK_NAME_RAND_LEN = 12
_TASK_NAME_RAND_RE = re.compile(rf"-[0-9a-f]{{{TASK_NAME_RAND_LEN}}}$")


def fit_task_name_max_len(name: str, max_len: int = TASK_NAME_MAX_LEN) -> str:
    """将 task_name 适配到 max_len；超长则截断并追加完整名的短哈希，保证稳定且 ≤max_len。"""
    if len(name) <= max_len:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:TASK_NAME_HASH_HEX_LEN]
    suffix = f"-{digest}"
    keep = max_len - len(suffix)
    if keep < 1:
        return digest[:max_len]
    return f"{name[:keep]}{suffix}"


def _has_task_name_random_suffix(name: str) -> bool:
    return bool(name and _TASK_NAME_RAND_RE.search(name))


def build_migrate_task_name(
    ticket_id: int | str,
    src_cluster_ids: Sequence[int | str],
    dst_cluster_id: int | str,
    *,
    max_len: int = TASK_NAME_MAX_LEN,
    uniqueness_token: str = "",
) -> str:
    """按规则生成迁移任务名：mysql-dts-{ticket_id}-{src}-{dst}（多源用 _ 拼接），并保证 ≤max_len。

    uniqueness_token：多行 infos 追加随机后缀，同源同目标但迁移对象不同时仍可区分。
    """
    src_part = "_".join(str(cid) for cid in src_cluster_ids)
    full = f"{TASK_NAME_PREFIX}-{ticket_id}-{src_part}-{dst_cluster_id}"
    token = (uniqueness_token or "").strip()
    if not token:
        return fit_task_name_max_len(full, max_len=max_len)
    suffix = f"-{token}"
    keep = max_len - len(suffix)
    if keep < 1:
        return token[:max_len]
    return f"{fit_task_name_max_len(full, max_len=keep)}{suffix}"


def _assign_unique_task_name(
    current: str,
    ticket_id: int | str,
    src_cluster_ids: Sequence[int | str],
    dst_cluster_id: int | str,
    used: set[str],
) -> str:
    name = (current or "").strip()
    if name and _has_task_name_random_suffix(name) and name not in used:
        used.add(name)
        return name
    while True:
        token = uuid.uuid4().hex[:TASK_NAME_RAND_LEN]
        name = build_migrate_task_name(ticket_id, src_cluster_ids, dst_cluster_id, uniqueness_token=token)
        if name not in used:
            used.add(name)
            return name


def patch_migrate_task_names_into_details(details: dict, ticket_id: int | str) -> dict:
    """按 migrate.topology 将自动生成的 task_name 写回分层 details（原地修改并返回）。"""
    if not ticket_id:
        return details

    infos = details.get("infos")
    if infos:
        used: set[str] = set()
        for row in infos:
            _patch_one_migrate_block(row.get("migrate") or {}, ticket_id, used_names=used, unique=True)
        return details

    migrate = details.get("migrate") or {}
    _patch_one_migrate_block(migrate, ticket_id)
    details["migrate"] = migrate
    return details


def _patch_one_migrate_block(
    migrate: dict,
    ticket_id: int | str,
    *,
    used_names: set[str] | None = None,
    unique: bool = False,
) -> dict:
    topology = migrate.get("topology")
    if not topology:
        return migrate
    used = used_names if used_names is not None else set()

    if topology == MigrateTopology.ONE_TO_ONE.value:
        block = migrate.setdefault("one_to_one", {})
        src_id = (block.get("source") or {}).get("cluster_id")
        dst_id = (block.get("target") or {}).get("cluster_id")
        if unique:
            block["task_name"] = _assign_unique_task_name(
                block.get("task_name") or "", ticket_id, [src_id], dst_id, used
            )
        else:
            block["task_name"] = build_migrate_task_name(ticket_id, [src_id], dst_id)
    elif topology == MigrateTopology.MANY_TO_ONE.value:
        block = migrate.setdefault("many_to_one", {})
        src_ids = [(s or {}).get("cluster_id") for s in (block.get("sources") or [])]
        dst_id = (block.get("target") or {}).get("cluster_id")
        if unique:
            block["task_name"] = _assign_unique_task_name(
                block.get("task_name") or "", ticket_id, src_ids, dst_id, used
            )
        else:
            block["task_name"] = build_migrate_task_name(ticket_id, src_ids, dst_id)
    elif topology == MigrateTopology.ONE_TO_MANY.value:
        block = migrate.setdefault("one_to_many", {})
        src_id = (block.get("source") or {}).get("cluster_id")
        targets = block.get("targets") or []
        for target in targets:
            dst_id = (target or {}).get("cluster_id")
            if unique:
                target["task_name"] = _assign_unique_task_name(
                    target.get("task_name") or "", ticket_id, [src_id], dst_id, used
                )
            else:
                target["task_name"] = build_migrate_task_name(ticket_id, [src_id], dst_id)
        block["targets"] = targets
    return migrate
