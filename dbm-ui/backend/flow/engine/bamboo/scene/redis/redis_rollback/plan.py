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
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.utils import timezone

from backend.db_services.redis.rollback.binlogs import binlog_fingerprint, index_segments
from backend.db_services.redis.rollback.constants import (
    CLUSTER_PROTOCOL_TYPES,
    COMPRESSED_SUFFIXES,
    MEMORY_RATIO_AOF,
    MEMORY_RATIO_RDB,
    MEMORY_RESERVE_DIVISOR,
    SCOPE_CLUSTER,
    SELECT_MODE_BY_TIME,
    TENDISPLUS_TYPES,
    UNPACK_RATIO,
)
from backend.db_services.redis.rollback.models import TbTendisRollbackPlan
from backend.db_services.redis.rollback.shards import ShardRef, slot_ranges

ORPHAN_PLAN_TTL = timedelta(days=1)
MANIFEST_FILE_PREFIX = "rollback_manifest_"
MANIFEST_NO_MD5 = "-"


def unpacked_size(file_name: str, size: int) -> int:
    if file_name.endswith(COMPRESSED_SUFFIXES):
        return int(size) * UNPACK_RATIO
    return int(size)


def load_memory(files: Iterable[Tuple[str, int]]) -> int:
    """Estimated resident memory of a Cache instance loading these full backup files."""
    total = 0.0
    for name, size in files:
        ratio = MEMORY_RATIO_AOF if ".aof" in name else MEMORY_RATIO_RDB
        total += unpacked_size(name, size) * ratio
    return int(total)


def memory_budget(available: int) -> int:
    """What the actuator admits instances into out of ``available`` bytes."""
    return available - available // MEMORY_RESERVE_DIVISOR


def stage_slots(cpu: int, max_concurrency: int, ports: int) -> int:
    """Ports unpacking, or Tendisplus kvstores replaying, at once on a host, as the actuator
    sizes both stages (Limits.Unpack, Limits.KvstoreReplay). An unknown CPU count is taken as
    every port at once."""
    slots = cpu // 2 if cpu > 0 else ports
    if max_concurrency > 0:
        slots = min(slots, max_concurrency)
    return max(1, min(slots, ports))


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
    # Tendisplus only; every kvstore has its own chain.
    kvstore: int = 0


def _binlog_digest(binlogs: List[BinlogRef]) -> Dict[str, Any]:
    names = [b.file_name for b in binlogs]
    return {
        "count": len(names),
        "first": names[0] if names else "",
        "last": names[-1] if names else "",
        "fingerprint": binlog_fingerprint(names) if names else "",
        "segments": index_segments([b.index for b in binlogs]),
    }


def _binlog_payload(binlogs: List[BinlogRef]) -> Dict[str, Any]:
    digest = _binlog_digest(binlogs)
    return {
        "binlog_range": {
            "first_index": binlogs[0].index if binlogs else 0,
            "last_index": binlogs[-1].index if binlogs else 0,
        },
        "binlog_count": digest["count"],
        "binlog_fingerprint": digest["fingerprint"],
        "binlog_segments": digest["segments"],
    }


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
    def memory_bytes(self) -> int:
        return load_memory((f.file_name, f.size) for f in self.full_files)

    @property
    def unpacked_bytes(self) -> int:
        return sum(unpacked_size(f.file_name, f.size) for f in self.full_files)

    @property
    def binlog_unpacked_bytes(self) -> int:
        return sum(unpacked_size(b.file_name, b.size) for b in self.binlog_files)

    @property
    def binlog_digest(self) -> Dict[str, Any]:
        digest = _binlog_digest(self.binlog_files)
        if self.binlog_gaps:
            digest["gaps"] = dict(self.binlog_gaps)
        return digest

    @property
    def kvstore_binlogs(self) -> Dict[int, List[BinlogRef]]:
        """Tendisplus binlogs per kvstore, each in index order."""
        chains: Dict[int, List[BinlogRef]] = {}
        for binlog in sorted(self.binlog_files, key=lambda b: (b.kvstore, b.index)):
            chains.setdefault(binlog.kvstore, []).append(binlog)
        return chains

    @property
    def kvstore_digest(self) -> Dict[str, Any]:
        digest: Dict[str, Any] = {
            "count": len(self.binlog_files),
            "kvstores": {str(kvstore): _binlog_digest(chain) for kvstore, chain in self.kvstore_binlogs.items()},
        }
        if self.binlog_gaps:
            digest["gaps"] = dict(self.binlog_gaps)
        return digest

    def actuator_instance(self, plus: bool = False, cluster_protocol: bool = False) -> Dict[str, Any]:
        """One port of the actuator payload. Binlogs go as a digest the actuator checks its local files against;
        Tendisplus gets one per kvstore, and cluster protocol ports the slots they own."""
        instance = {
            "shard_value": self.shard.shard_value,
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "dest_port": self.dest_port,
            "full_files": [f.file_name for f in self.full_files],
            **_binlog_payload([] if plus else self.binlog_files),
        }
        if cluster_protocol:
            instance["slots"] = slot_ranges(self.shard.shard_value)
        if plus:
            instance["kvstore_binlogs"] = [
                {"kvstore": kvstore, **_binlog_payload(chain)} for kvstore, chain in self.kvstore_binlogs.items()
            ]
        return instance

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
    # Cache only: what its instances hold once loaded; 0 skips the memory precheck.
    memory_bytes: int = 0


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
    # Caps the actuator's per-stage concurrency; 0 lets it size each stage from the host.
    max_concurrency: int = 0

    @property
    def locked_rounds(self) -> List[Dict[str, str]]:
        """Rounds chosen for each restored shard, fixed into the ticket so the flow reuses them."""
        return [
            {"shard_value": item.shard.shard_value, "round_key": item.full_files[0].round_key}
            for item in self.items
            if not item.is_placeholder
        ]

    @property
    def is_plus(self) -> bool:
        return self.cluster_type in TENDISPLUS_TYPES

    @property
    def is_cluster_protocol(self) -> bool:
        return self.cluster_type in CLUSTER_PROTOCOL_TYPES

    def dest_host(self, ip: str) -> DestHost:
        return next(host for host in self.dest_hosts if host.ip == ip)

    def actuator_instances(self, ip: str) -> List[Dict[str, Any]]:
        return [
            item.actuator_instance(plus=self.is_plus, cluster_protocol=self.is_cluster_protocol)
            for item in self.items
            if item.dest_ip == ip
        ]

    def cluster_nodes(self) -> List[Dict[str, Any]]:
        """Every temp instance with the slots it must own once the cluster is formed."""
        return [
            {"ip": item.dest_ip, "port": item.dest_port, "slots": slot_ranges(item.shard.shard_value)}
            for item in self.items
        ]

    def to_rollback_detail(self, plan_id: Optional[int] = None) -> Dict[str, Any]:
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
                shard["binlog"] = item.kvstore_digest if self.is_plus else item.binlog_digest
            shards.append(shard)
        return {
            "plan_id": plan_id,
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

    def save(self, plan_id: Optional[int] = None, ticket_id: Optional[int] = None) -> int:
        fields = {"plan": self.to_dict()}
        if ticket_id:
            fields["ticket_id"] = int(ticket_id)
        if plan_id:
            TbTendisRollbackPlan.objects.filter(id=plan_id).update(**fields)
            return plan_id
        return TbTendisRollbackPlan.objects.create(bk_biz_id=self.bk_biz_id, cluster_id=self.cluster_id, **fields).id

    @staticmethod
    def bind_ticket(plan_ids: List[int], ticket_id: int) -> None:
        TbTendisRollbackPlan.objects.filter(id__in=plan_ids).update(ticket_id=ticket_id)

    @staticmethod
    def delete_orphans() -> int:
        """Plans saved by ticket validation that never became a ticket. Plans bound to a ticket stay:
        construction records keep only a binlog digest and point to the plan for the full list."""
        deleted, _ = TbTendisRollbackPlan.objects.filter(
            ticket_id__isnull=True, create_at__lt=timezone.now() - ORPHAN_PLAN_TTL
        ).delete()
        return deleted

    @classmethod
    def load(cls, plan_id: int) -> "RollbackPlan":
        return cls.from_dict(TbTendisRollbackPlan.objects.get(id=plan_id).plan)


def host_disk_needs(
    items: List[RollbackItem], is_ssd: bool, cpu: int, max_concurrency: int, is_plus: bool = False
) -> Tuple[int, int]:
    """Peak ``(backup disk, data disk)`` bytes of one host's restore.

    Downloads stay on the backup disk until their port is done; full backups are unpacked onto
    the data disk. An SSD port also holds its unpacked backup beside the rocksdb rebuilt from it
    until the rebuild ends, and replayed writes grow rocksdb; its binlogs are streamed straight
    from the downloaded files, so replay keeps no extra copy on the backup disk. Tendisplus
    moves its unpacked backup into place, and each kvstore replaying keeps one binlog
    decompressed.
    """
    real = [item for item in items if not item.is_placeholder]
    backup = sum(item.download_bytes for item in real)
    data = sum(item.unpacked_bytes for item in real)
    if is_plus and real:
        streams = sum(len(item.kvstore_binlogs) for item in real)
        decompressed = [
            unpacked_size(b.file_name, b.size)
            for item in real
            for b in item.binlog_files
            if b.file_name.endswith(COMPRESSED_SUFFIXES)
        ]
        if streams and decompressed:
            backup += stage_slots(cpu, max_concurrency, streams) * max(decompressed)
        data += sum(item.binlog_unpacked_bytes for item in real)
        return backup, data
    if not is_ssd or not real:
        return backup, data
    unpacking = stage_slots(cpu, max_concurrency, len(real))
    data += sum(sorted((item.unpacked_bytes for item in real), reverse=True)[:unpacking])
    data += sum(item.binlog_unpacked_bytes for item in real)
    return backup, data


@dataclass
class RollbackManifest:
    file_name: str
    content: str
    fingerprint: str
    count: int


def rollback_manifest(plan: RollbackPlan, plan_id: int, ip: str) -> RollbackManifest:
    """The files one host must hold before restoring, as pushed next to the downloads.

    One ``<file_name> <size> <md5>`` line per file, ``-`` when the md5 is unknown, which is
    always for now. A ``#`` header carries the line count and the sha256 of the lines, which
    the verify payload repeats so a stale or truncated manifest is caught.
    """
    lines = []
    for item in plan.items:
        if item.dest_ip != ip:
            continue
        lines.extend("{} {} {}".format(f.file_name, int(f.size or 0), MANIFEST_NO_MD5) for f in item.full_files)
        lines.extend("{} {} {}".format(b.file_name, int(b.size or 0), MANIFEST_NO_MD5) for b in item.binlog_files)
    body = "".join(line + "\n" for line in lines)
    fingerprint = hashlib.sha256(body.encode()).hexdigest()
    header = "# redis rollback manifest plan={} files={} sha256={}\n".format(plan_id, len(lines), fingerprint)
    return RollbackManifest(
        file_name="{}{}".format(MANIFEST_FILE_PREFIX, plan_id),
        content=header + body,
        fingerprint=fingerprint,
        count=len(lines),
    )
