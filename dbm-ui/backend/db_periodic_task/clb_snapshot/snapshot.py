# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Per-cluster CLB snapshot records and their default-cache storage.

Kept free of flow / dispatch imports so report code can read snapshots cheaply.
Freshness is the reader's call: records carry ``checked_at`` and nothing else.
"""
import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from django.core.cache import cache

logger = logging.getLogger("root")

CLB_SNAPSHOT_KEY = "dbm:clb_snapshot:{cluster_id}"
# Must outlive the longest consumer staleness window (Redis entry check: 48h).
CLB_SNAPSHOT_TTL_SECONDS = 72 * 3600


@dataclass
class CLBEntrySnapshot:
    """One CLB entry. ``None`` for ``listener_rs`` / ``unhealthy_rs`` means unknown, never empty."""

    cluster_entry_id: int
    entry: str
    clb_id: str = ""
    listener_id: str = ""
    region: str = ""
    listener_rs: Optional[List[str]] = None
    unhealthy_rs: Optional[List[str]] = None
    meta_error: Optional[str] = None
    listener_rs_error: Optional[str] = None
    health_error: Optional[str] = None

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "CLBEntrySnapshot":
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in names})


@dataclass
class ClusterCLBSnapshot:
    cluster_id: int
    checked_at: float
    entries: List[CLBEntrySnapshot] = field(default_factory=list)

    def entry_by_id(self, cluster_entry_id: int) -> Optional[CLBEntrySnapshot]:
        return next((e for e in self.entries if e.cluster_entry_id == cluster_entry_id), None)

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "checked_at": self.checked_at,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "ClusterCLBSnapshot":
        return cls(
            cluster_id=int(raw["cluster_id"]),
            checked_at=float(raw["checked_at"]),
            entries=[CLBEntrySnapshot.from_dict(entry) for entry in raw.get("entries") or []],
        )


def _key(cluster_id: int) -> str:
    return CLB_SNAPSHOT_KEY.format(cluster_id=cluster_id)


def write_many(snapshots: Iterable[ClusterCLBSnapshot]) -> None:
    records = {_key(snap.cluster_id): snap.to_dict() for snap in snapshots}
    if records:
        cache.set_many(records, timeout=CLB_SNAPSHOT_TTL_SECONDS)


def get_many(cluster_ids: Iterable[int]) -> Dict[int, Optional[ClusterCLBSnapshot]]:
    """Return a snapshot or ``None`` for every requested cluster id; a corrupt record reads as ``None``."""
    ids = [int(cid) for cid in cluster_ids]
    if not ids:
        return {}
    hits = cache.get_many([_key(cid) for cid in ids])
    result: Dict[int, Optional[ClusterCLBSnapshot]] = {}
    for cid in ids:
        raw = hits.get(_key(cid))
        if not isinstance(raw, dict):
            result[cid] = None
            continue
        try:
            result[cid] = ClusterCLBSnapshot.from_dict(raw)
        except (KeyError, TypeError, ValueError, AttributeError):
            logger.warning("clb_snapshot: corrupt snapshot cluster_id=%s raw=%r", cid, raw)
            result[cid] = None
    return result
