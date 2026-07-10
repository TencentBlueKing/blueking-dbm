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
from collections.abc import Sequence

from backend.bk_web.constants import LEN_NORMAL
from backend.flow.utils.mysql.dts.constants import MigrateTopology

# 与 DTS Task.name / MysqlDtsInfo.dts_task_id 上限一致
TASK_NAME_MAX_LEN = LEN_NORMAL
TASK_NAME_PREFIX = "mysql-dts"
# 超长时对完整候选名取 sha1 短哈希（hex）
TASK_NAME_HASH_HEX_LEN = 8


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


def build_migrate_task_name(
    ticket_id: int | str,
    src_cluster_ids: Sequence[int | str],
    dst_cluster_id: int | str,
    *,
    max_len: int = TASK_NAME_MAX_LEN,
) -> str:
    """按规则生成迁移任务名：mysql-dts-{ticket_id}-{src}-{dst}（多源用 _ 拼接），并保证 ≤max_len。"""
    src_part = "_".join(str(cid) for cid in src_cluster_ids)
    full = f"{TASK_NAME_PREFIX}-{ticket_id}-{src_part}-{dst_cluster_id}"
    return fit_task_name_max_len(full, max_len=max_len)


def patch_migrate_task_names_into_details(details: dict, ticket_id: int | str) -> dict:
    """按 migrate.topology 将自动生成的 task_name 写回分层 details（原地修改并返回）。"""
    migrate = details.get("migrate") or {}
    topology = migrate.get("topology")
    if not topology or not ticket_id:
        return details

    if topology == MigrateTopology.ONE_TO_ONE.value:
        block = migrate.setdefault("one_to_one", {})
        src_id = (block.get("source") or {}).get("cluster_id")
        dst_id = (block.get("target") or {}).get("cluster_id")
        block["task_name"] = build_migrate_task_name(ticket_id, [src_id], dst_id)
    elif topology == MigrateTopology.MANY_TO_ONE.value:
        block = migrate.setdefault("many_to_one", {})
        src_ids = [(s or {}).get("cluster_id") for s in (block.get("sources") or [])]
        dst_id = (block.get("target") or {}).get("cluster_id")
        block["task_name"] = build_migrate_task_name(ticket_id, src_ids, dst_id)
    elif topology == MigrateTopology.ONE_TO_MANY.value:
        block = migrate.setdefault("one_to_many", {})
        src_id = (block.get("source") or {}).get("cluster_id")
        targets = block.get("targets") or []
        for target in targets:
            dst_id = (target or {}).get("cluster_id")
            target["task_name"] = build_migrate_task_name(ticket_id, [src_id], dst_id)
        block["targets"] = targets

    details["migrate"] = migrate
    return details
