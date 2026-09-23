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

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.constants import BACKUP_BATCH_DEFAULT_WINDOW_DAYS
from backend.db_services.redis.rollback.locator import BackupLocator
from backend.db_services.redis.rollback.shards import ShardResolver, extract_identify_prefix

logger = logging.getLogger("flow")

_SPLIT_INDEX_RE = re.compile(r"\.split\.(\d+)$")


def _parse_dt(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def split_indexes(file_name: str) -> Optional[int]:
    matched = _SPLIT_INDEX_RE.search(file_name or "")
    if not matched:
        return None
    return int(matched.group(1))


def is_split_round_complete(files: Sequence[dict]) -> bool:
    """A round is complete when all files are non-split, or all are split with indexes 0..N.

    Backup never mixes a whole file and ``.split.NNN`` under the same round_key.
    Mixed input is treated as incomplete rather than silently accepting the split subset.
    """
    if not files:
        return False
    indexes = [split_indexes(f.get("file_name") or "") for f in files]
    if all(idx is None for idx in indexes):
        return True
    if any(idx is None for idx in indexes):
        return False
    present = sorted(indexes)
    return present == list(range(0, max(present) + 1))


def group_rounds(records: Sequence[dict]) -> Dict[Tuple[str, str], List[dict]]:
    """Group records by (shard_value, round_key)."""
    buckets: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for record in records:
        shard = record.get("shard_value") or ""
        round_key = record.get("round_key") or record.get("file_name") or ""
        buckets[(shard, round_key)].append(record)
    return buckets


def latest_round_per_shard(records: Sequence[dict]) -> Dict[str, List[dict]]:
    """Pick the round with max backup_begin_time for each shard."""
    by_round = group_rounds(records)
    latest: Dict[str, Tuple[datetime, List[dict]]] = {}
    for (shard, _round_key), files in by_round.items():
        begins = [_parse_dt(f.get("backup_begin_time") or f.get("file_last_mtime")) for f in files]
        begins = [b for b in begins if b]
        begin = max(begins) if begins else datetime.min.replace(tzinfo=timezone.utc)
        current = latest.get(shard)
        if current is None or begin > current[0]:
            latest[shard] = (begin, files)
    return {shard: files for shard, (_begin, files) in latest.items()}


class BackupBatchService:
    def __init__(self, cluster: Cluster):
        self.cluster = cluster
        self.locator = BackupLocator(cluster)
        self.resolver = ShardResolver(cluster)

    def list_batches(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        shard_values: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Batch-level summaries only.

        The shard/round/file tree lives behind :meth:`batch_details`: a 180-shard cluster
        backed up three times a day produces thousands of file objects over a 30 day window,
        and whole-cluster rollback (the common case) only needs to pick a batch.
        """
        end_time = end_time or datetime.now(timezone.utc)
        start_time = start_time or (end_time - timedelta(days=BACKUP_BATCH_DEFAULT_WINDOW_DAYS))
        records = self.locator.list_full_in_window(start_time, end_time)
        records = self._filter_shards(records, shard_values)

        current_by_shard = self._current_by_shard()
        return {
            "locator_source": self.locator.locator_source,
            "cluster_shards": self.resolver.cluster_shard_map(),
            "batches": self._summaries(records, current_by_shard),
        }

    def batch_details(self, backup_identify: str, shard_values: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """Expand one batch into its shard / round / file tree, for custom shard selection."""
        records = self._filter_shards(self.locator.locate_full_by_identify(backup_identify), shard_values)
        current_by_shard = self._current_by_shard()
        return {
            "locator_source": self.locator.locator_source,
            "backup_identify": backup_identify,
            "cluster_shards": self.resolver.cluster_shard_map(),
            "shards": self._shard_tree(records, current_by_shard),
        }

    def _current_by_shard(self) -> dict:
        return {ref.shard_value: ref for ref in self.resolver.from_db_meta() if ref.shard_value}

    @staticmethod
    def _filter_shards(records: Sequence[dict], shard_values: Optional[Sequence[str]]) -> List[dict]:
        if not shard_values:
            return list(records)
        wanted = set(shard_values)
        return [r for r in records if (r.get("shard_value") or "") in wanted]

    def _summaries(self, records: Sequence[dict], current_by_shard: dict) -> List[Dict[str, Any]]:
        """One row per ``backup_identify``, no nested shards or files."""
        batches = []
        for identify, files in self._group_by_identify(records).items():
            latest = latest_round_per_shard(files)
            round_keys_by_shard: Dict[str, set] = defaultdict(set)
            for shard, round_key in group_rounds(files):
                round_keys_by_shard[shard].add(round_key)

            begins = [f.get("backup_begin_time") or f.get("file_last_mtime") or "" for f in files]
            ends = [f.get("backup_end_time") or f.get("uptime") or "" for f in files]
            batch_shards = set(round_keys_by_shard)
            batches.append(
                {
                    "backup_identify": identify,
                    "backup_type": extract_identify_prefix(identify),
                    "start_time": min([b for b in begins if b], default=""),
                    "end_time": max([e for e in ends if e], default=""),
                    "total_size": sum(int(f.get("size") or 0) for f in files),
                    "shard_count": len(batch_shards),
                    "is_complete": all(is_split_round_complete(round_files) for round_files in latest.values()),
                    "is_all_shards_covered": bool(current_by_shard) and set(current_by_shard) <= batch_shards,
                    "has_multi_rounds": any(len(keys) > 1 for keys in round_keys_by_shard.values()),
                    "source_is_all_current": bool(latest)
                    and all(
                        self._source_is_current(round_files[0], current_by_shard.get(shard))
                        for shard, round_files in latest.items()
                    ),
                }
            )
        batches.sort(key=lambda b: b["start_time"], reverse=True)
        return batches

    def _shard_tree(self, records: Sequence[dict], current_by_shard: dict) -> List[Dict[str, Any]]:
        """Shape one batch's records into shard -> round, the granularity the ticket selects on."""
        latest = latest_round_per_shard(records)
        latest_round_key = {
            shard: (round_files[0].get("round_key") or round_files[0].get("file_name") or "")
            for shard, round_files in latest.items()
        }

        rounds_by_shard: Dict[str, List[dict]] = defaultdict(list)
        for (shard, round_key), round_files in group_rounds(records).items():
            rounds_by_shard[shard].append(
                self._round_detail(shard, round_key, round_files, current_by_shard, latest_round_key)
            )

        shards = []
        for shard, rounds in rounds_by_shard.items():
            rounds.sort(key=lambda r: r["backup_begin_time"] or "", reverse=True)
            current = current_by_shard.get(shard)
            shards.append(
                {
                    "shard_value": shard,
                    "in_current_topology": current is not None,
                    "current_master": current.current_master if current else None,
                    "rounds": rounds,
                }
            )
        shards.sort(key=lambda s: s["shard_value"])
        return shards

    @staticmethod
    def _group_by_identify(records: Sequence[dict]) -> Dict[str, List[dict]]:
        by_identify: Dict[str, List[dict]] = defaultdict(list)
        for record in records:
            identify = record.get("backup_identify") or ""
            if not identify:
                continue
            by_identify[identify].append(record)
        return by_identify

    @staticmethod
    def _source_is_current(record: dict, current) -> bool:
        if not current:
            return False
        source = "{}:{}".format(record.get("source_ip"), record.get("server_port"))
        return source in {current.current_master, current.current_slave}

    @classmethod
    def _round_detail(
        cls,
        shard: str,
        round_key: str,
        round_files: Sequence[dict],
        current_by_shard: dict,
        latest_round_key: Dict[str, str],
    ) -> Dict[str, Any]:
        first = round_files[0]
        source_is_current = cls._source_is_current(first, current_by_shard.get(shard))
        begins = [f.get("backup_begin_time") or f.get("file_last_mtime") or "" for f in round_files]
        ends = [f.get("backup_end_time") or f.get("uptime") or "" for f in round_files]
        return {
            "round_key": round_key,
            "is_latest": latest_round_key.get(shard) == round_key,
            "is_complete": is_split_round_complete(round_files),
            "size": sum(int(f.get("size") or 0) for f in round_files),
            "backup_begin_time": min([b for b in begins if b], default=""),
            "backup_end_time": max([e for e in ends if e], default=""),
            "source_ip": first.get("source_ip"),
            "source_port": first.get("server_port"),
            "source_is_current": source_is_current,
            "files": [
                {
                    "file_name": f.get("file_name"),
                    "task_id": f.get("task_id"),
                    "size": int(f.get("size") or 0),
                }
                for f in round_files
            ],
        }
