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

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.db_services.redis.rollback.constants import (
    FILTER_MODE_DELETE_MATCHED,
    FILTER_MODE_KEEP_MATCHED,
    SCOPE_CLUSTER,
    SELECT_MODE_BY_TIME,
)
from backend.db_services.redis.rollback.shards import ShardRef


@dataclass
class FullBackupRef:
    task_id: str
    file_name: str
    size: int
    source_ip: str
    source_port: int
    shard_value: str
    backup_identify: str
    backup_begin_time: str
    backup_end_time: str
    round_key: str


@dataclass
class BinlogRef:
    task_id: str
    file_name: str
    size: int
    source_ip: str
    source_port: int


@dataclass
class KeyFilterSpec:
    white_regex: str = ""
    black_regex: str = ""
    filter_mode: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.white_regex or self.black_regex)

    @classmethod
    def from_ticket(cls, white: str = "", black: str = "") -> "KeyFilterSpec":
        white = (white or "").strip()
        black = (black or "").strip()
        if not white and not black:
            return cls()
        if white:
            return cls(white_regex=white, black_regex=black, filter_mode=FILTER_MODE_KEEP_MATCHED)
        return cls(white_regex=".*", black_regex=black, filter_mode=FILTER_MODE_DELETE_MATCHED)


@dataclass
class RollbackItem:
    shard: ShardRef
    source_ip: str
    source_port: int
    source_is_current: bool
    dest_ip: str
    dest_port: int
    full_files: List[FullBackupRef] = field(default_factory=list)
    binlog_files: List[BinlogRef] = field(default_factory=list)
    # 未勾选的批次分片：只拉起空实例占住这段 slot，让临时 Proxy 的后端有所指
    is_placeholder: bool = False

    @property
    def download_bytes(self) -> int:
        return sum(int(f.size or 0) for f in self.full_files) + sum(int(b.size or 0) for b in self.binlog_files)

    @property
    def task_ids(self) -> List[str]:
        return [f.task_id for f in self.full_files] + [b.task_id for b in self.binlog_files]


@dataclass
class DestHost:
    ip: str
    ports: List[int] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    download_bytes: int = 0


@dataclass
class RollbackPlan:
    cluster_id: int
    immute_domain: str
    cluster_type: str
    tendis_type: str
    bk_cloud_id: int
    bk_biz_id: int
    db_version: str
    proxy_port: int
    scope: str = SCOPE_CLUSTER
    select_mode: str = SELECT_MODE_BY_TIME
    recover_at: Optional[datetime] = None
    backup_identify: Optional[str] = None
    locator_source: str = ""
    shard_keyed: bool = True
    topology_changed: bool = False
    items: List[RollbackItem] = field(default_factory=list)
    dest_hosts: List[DestHost] = field(default_factory=list)
    key_filter: KeyFilterSpec = field(default_factory=KeyFilterSpec)
    warnings: List[str] = field(default_factory=list)

    def to_rollback_detail(self) -> Dict[str, Any]:
        shards = []
        for item in self.items:
            shards.append(
                {
                    "shard_value": item.shard.shard_value,
                    "source_ip": item.source_ip,
                    "source_port": item.source_port,
                    "source_is_current": item.source_is_current,
                    "dest_ip": item.dest_ip,
                    "dest_port": item.dest_port,
                    "task_ids": item.task_ids,
                    "file_names": [f.file_name for f in item.full_files],
                    "is_placeholder": item.is_placeholder,
                }
            )
        return {
            "shards": shards,
            "key_filter": asdict(self.key_filter),
            "locator_source": self.locator_source,
            "topology_changed": self.topology_changed,
            "shard_keyed": self.shard_keyed,
            "warnings": list(self.warnings),
        }
