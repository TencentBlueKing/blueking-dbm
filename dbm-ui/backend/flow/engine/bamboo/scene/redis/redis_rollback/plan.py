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

from backend.db_services.redis.rollback.binlogs import binlog_fingerprint, index_segments
from backend.db_services.redis.rollback.constants import SCOPE_CLUSTER, SELECT_MODE_BY_TIME
from backend.db_services.redis.rollback.models import TbTendisRollbackPlan
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
    index: int = 0


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
    # Index gaps let through by allow_binlog_nonconsecutive: {missing_count, missing}.
    binlog_gaps: Optional[Dict[str, Any]] = None
    # 未勾选的批次分片：只拉起空实例占住这段 slot，让临时 Proxy 的后端有所指
    is_placeholder: bool = False

    @property
    def download_bytes(self) -> int:
        return sum(int(f.size or 0) for f in self.full_files) + sum(int(b.size or 0) for b in self.binlog_files)

    @property
    def task_ids(self) -> List[str]:
        return [f.task_id for f in self.full_files] + [b.task_id for b in self.binlog_files]

    @property
    def binlog_digest(self) -> Dict[str, Any]:
        names = [b.file_name for b in self.binlog_files]
        digest = {
            "count": len(names),
            "first": names[0] if names else "",
            "last": names[-1] if names else "",
            "fingerprint": binlog_fingerprint(names) if names else "",
            "segments": index_segments([b.index for b in self.binlog_files]),
        }
        if self.binlog_gaps:
            digest["gaps"] = dict(self.binlog_gaps)
        return digest

    def actuator_instance(self) -> Dict[str, Any]:
        """One port of the actuator payload. Binlogs go as a digest the actuator checks its local files against."""
        binlogs = self.binlog_files
        return {
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "dest_port": self.dest_port,
            "full_files": [f.file_name for f in self.full_files],
            "binlog_range": {
                "first_index": binlogs[0].index if binlogs else 0,
                "last_index": binlogs[-1].index if binlogs else 0,
            },
            "binlog_count": len(binlogs),
            "binlog_fingerprint": self.binlog_digest["fingerprint"],
            "binlog_segments": self.binlog_digest["segments"],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RollbackItem":
        data = dict(data)
        data["shard"] = ShardRef(**data["shard"])
        data["full_files"] = [FullBackupRef(**f) for f in data.get("full_files") or []]
        data["binlog_files"] = [BinlogRef(**b) for b in data.get("binlog_files") or []]
        return cls(**data)


@dataclass
class DestHost:
    ip: str
    ports: List[int] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    download_bytes: int = 0
    unpacked_bytes: int = 0


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
    allow_binlog_nonconsecutive: bool = False
    warnings: List[str] = field(default_factory=list)

    @property
    def locked_rounds(self) -> List[Dict[str, str]]:
        """Rounds chosen for each restored shard, fixed into the ticket so the flow reuses them."""
        return [
            {"shard_value": item.shard.shard_value, "round_key": item.full_files[0].round_key}
            for item in self.items
            if not item.is_placeholder
        ]

    def dest_host(self, ip: str) -> DestHost:
        return next(host for host in self.dest_hosts if host.ip == ip)

    def actuator_instances(self, ip: str) -> List[Dict[str, Any]]:
        return [item.actuator_instance() for item in self.items if item.dest_ip == ip]

    def to_rollback_detail(self) -> Dict[str, Any]:
        """Per-shard summary for the task record; the full file lists stay in the persisted plan."""
        shards = []
        for item in self.items:
            shard = {
                "shard_value": item.shard.shard_value,
                "source_ip": item.source_ip,
                "source_port": item.source_port,
                "source_is_current": item.source_is_current,
                "dest_ip": item.dest_ip,
                "dest_port": item.dest_port,
                "task_ids": [f.task_id for f in item.full_files],
                "file_names": [f.file_name for f in item.full_files],
                "is_placeholder": item.is_placeholder,
            }
            if item.binlog_files:
                shard["binlog"] = item.binlog_digest
            shards.append(shard)
        return {
            "shards": shards,
            "locator_source": self.locator_source,
            "topology_changed": self.topology_changed,
            "shard_keyed": self.shard_keyed,
            "warnings": list(self.warnings),
        }

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["recover_at"] = self.recover_at.isoformat() if self.recover_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RollbackPlan":
        data = dict(data)
        data["recover_at"] = datetime.fromisoformat(data["recover_at"]) if data.get("recover_at") else None
        data["items"] = [RollbackItem.from_dict(item) for item in data.get("items") or []]
        data["dest_hosts"] = [DestHost(**host) for host in data.get("dest_hosts") or []]
        return cls(**data)

    def save(self, plan_id: Optional[int] = None) -> int:
        if plan_id:
            TbTendisRollbackPlan.objects.filter(id=plan_id).update(plan=self.to_dict())
            return plan_id
        return TbTendisRollbackPlan.objects.create(
            bk_biz_id=self.bk_biz_id, cluster_id=self.cluster_id, plan=self.to_dict()
        ).id

    @classmethod
    def load(cls, plan_id: int) -> "RollbackPlan":
        return cls.from_dict(TbTendisRollbackPlan.objects.get(id=plan_id).plan)
