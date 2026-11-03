# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

CLB snapshot producer and consumer on the ``nameservice`` dispatch lane.
"""
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Set, Tuple

from backend.components import NameServiceApi
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import ClusterEntry
from backend.db_periodic_task.clb_snapshot.snapshot import CLBEntrySnapshot, ClusterCLBSnapshot, write_many
from backend.db_periodic_task.dispatch.base import DispatchTask
from backend.db_periodic_task.dispatch.config import DispatchTaskConfig
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.db_periodic_task.dispatch.nameservice_queue import NAMESERVICE_CALL_GATE, NameserviceQueue
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.registry import register_dispatch_task
from backend.flow.utils.clb_manage import CLBManage

logger = logging.getLogger("root")

CLB_SNAPSHOT_TASK_KEY = "nameservice.clb_snapshot"
# The lane publishes at most one job per 10s pump tick; ~50 entries is ~100 calls, ~7s at 15 QPS.
CLB_SNAPSHOT_BATCH_SIZE = 50


@dataclass
class ClbSnapshotTaskConfig(DispatchTaskConfig):
    task_key: ClassVar[str] = CLB_SNAPSHOT_TASK_KEY
    enabled: bool = True
    execution_timeout_seconds: int = 300
    # A submission still waiting after this long is from a previous night and no longer useful.
    queue_wait_ttl_seconds: int = 6 * 3600


@dataclass
class ClbSnapshotSubmitSummary:
    """Counts are clusters, not batches."""

    accepted: int = 0
    duplicate: int = 0
    rejected: int = 0
    skipped: int = 0


def batch_work_item_id(cluster_ids: Iterable[int]) -> str:
    joined = ",".join(str(cid) for cid in sorted(int(cid) for cid in cluster_ids))
    return "clb:" + hashlib.sha1(joined.encode()).hexdigest()[:16]


def _fetch_listener_rs(detail) -> Tuple[Optional[List[str]], Optional[str]]:
    # Not CLBManage.get_clb_rs: it returns [] on failure, which reads as "no RS".
    try:
        NAMESERVICE_CALL_GATE.acquire()
        res = NameServiceApi.clb_get_target_private_ips(
            {"region": detail.clb_region, "loadbalancerid": detail.clb_id, "listenerid": detail.listener_id},
            raw=True,
        )
    except Exception as e:  # pylint: disable=broad-except
        return None, f"CLB listener RS query failed: {e}"
    if not isinstance(res, dict) or res.get("code") != 0:
        message = res.get("message") if isinstance(res, dict) else res
        return None, f"CLB listener RS query failed: {message}"
    ips = (res.get("data") or {}).get("ips")
    if not isinstance(ips, (list, type(None))):
        return None, f"CLB listener RS query failed: invalid ips {ips!r}"
    return sorted(str(ip) for ip in (ips or []) if ip), None


def _fetch_abnormal_rs(detail) -> Tuple[Optional[Set[str]], Optional[str]]:
    try:
        NAMESERVICE_CALL_GATE.acquire()
        health = CLBManage(
            detail.clb_id, detail.clb_ip, detail.listener_id, detail.clb_region
        ).describe_target_health()
    except Exception as e:  # pylint: disable=broad-except
        return None, f"CLB target health query failed: {e}"
    # describe_target_health returns {} when code != 0 or data is missing;
    # Go nameservice serializes an empty slice as `"abnormalips": null` when abnormalcount is 0.
    abnormal_ips = health.get("abnormalips") if isinstance(health, dict) else None
    if not isinstance(health, dict) or "abnormalips" not in health or not isinstance(abnormal_ips, (list, type(None))):
        return None, "CLB target health query failed: empty or invalid response"
    return {str(rs) for rs in (abnormal_ips or []) if rs}, None


def _snapshot_entry(entry: ClusterEntry, health_cache: Dict[Tuple[str, str], Tuple]) -> CLBEntrySnapshot:
    detail = next(iter(entry.clbentrydetail_set.all()), None)
    if detail is None:
        return CLBEntrySnapshot(cluster_entry_id=entry.id, entry=entry.entry, meta_error="CLB entry detail not found")

    snap = CLBEntrySnapshot(
        cluster_entry_id=entry.id,
        entry=entry.entry,
        clb_id=detail.clb_id,
        listener_id=detail.listener_id,
        region=detail.clb_region,
    )
    if not (detail.clb_id or "").strip() or not (detail.clb_region or "").strip():
        snap.meta_error = "CLB metadata incomplete: blank load balancer id or region"
        return snap

    snap.listener_rs, snap.listener_rs_error = _fetch_listener_rs(detail)

    # Health is reported per load balancer, so entries sharing one reuse the call.
    health_key = (detail.clb_region, detail.clb_id)
    if health_key not in health_cache:
        health_cache[health_key] = _fetch_abnormal_rs(detail)
    abnormal_rs, snap.health_error = health_cache[health_key]

    if snap.listener_rs is not None and abnormal_rs is not None:
        snap.unhealthy_rs = sorted(set(snap.listener_rs) & abnormal_rs)
    return snap


def snapshot_clusters(cluster_ids: List[int]) -> List[ClusterCLBSnapshot]:
    """Snapshot each cluster from metadata read now; per-entry errors are recorded, not raised."""
    entries_by_cluster: Dict[int, List[ClusterEntry]] = {cid: [] for cid in cluster_ids}
    for entry in ClusterEntry.objects.filter(
        cluster_id__in=cluster_ids, cluster_entry_type=ClusterEntryType.CLB
    ).prefetch_related("clbentrydetail_set"):
        entries_by_cluster.setdefault(entry.cluster_id, []).append(entry)

    health_cache: Dict[Tuple[str, str], Tuple] = {}
    snapshots = []
    for cluster_id, entries in entries_by_cluster.items():
        snapshot_entries = []
        for entry in entries:
            try:
                snapshot_entries.append(_snapshot_entry(entry, health_cache))
            except Exception as e:  # pylint: disable=broad-except
                logger.exception("clb_snapshot: entry %s of cluster %s failed", entry.entry, cluster_id)
                snapshot_entries.append(
                    CLBEntrySnapshot(cluster_entry_id=entry.id, entry=entry.entry, meta_error=f"snapshot failed: {e}")
                )
        snapshots.append(ClusterCLBSnapshot(cluster_id=cluster_id, checked_at=time.time(), entries=snapshot_entries))
    return snapshots


@register_dispatch_task(config_cls=ClbSnapshotTaskConfig, metadata={"db_type": "common"})
class ClbSnapshotTask(DispatchTask):
    queue_cls = NameserviceQueue

    def work_item_id(self, item: Any) -> str:
        return batch_work_item_id(item["cluster_ids"])

    def work_item_data(self, item: Any) -> dict:
        return {"cluster_ids": [int(cid) for cid in item["cluster_ids"]]}

    def execute(
        self, item: Any, *, job: Optional[DispatchJob] = None, overrides: Optional[dict] = None
    ) -> DispatchOutcome:
        started_at = time.monotonic()
        cluster_ids = [int(cid) for cid in item.get("cluster_ids") or []]
        snapshots = snapshot_clusters(cluster_ids)
        write_many(snapshots)
        elapsed = time.monotonic() - started_at

        entries = [entry for snap in snapshots for entry in snap.entries]
        errors = {
            "meta": [e.meta_error for e in entries if e.meta_error],
            "listener_rs": [e.listener_rs_error for e in entries if e.listener_rs_error],
            "health": [e.health_error for e in entries if e.health_error],
        }
        if any(errors.values()):
            sample = next(msg for msgs in errors.values() for msg in msgs)
            logger.warning(
                "clb_snapshot: %d/%d entries with errors (meta=%d listener_rs=%d health=%d) in %.1fs, e.g. %s",
                sum(1 for e in entries if e.meta_error or e.listener_rs_error or e.health_error),
                len(entries),
                len(errors["meta"]),
                len(errors["listener_rs"]),
                len(errors["health"]),
                elapsed,
                sample,
            )
        else:
            logger.info(
                "clb_snapshot: wrote %d cluster snapshots (%d entries) in %.1fs", len(snapshots), len(entries), elapsed
            )
        return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS)


def submit(cluster_ids: Iterable[int]) -> ClbSnapshotSubmitSummary:
    """Schedule CLB snapshots; clusters without a CLB entry are skipped, not queued."""
    summary = ClbSnapshotSubmitSummary()
    requested = list(dict.fromkeys(int(cid) for cid in cluster_ids))
    if not requested:
        return summary

    task = ClbSnapshotTask()
    if not task.config.enabled:
        logger.info("clb_snapshot: task disabled, %d clusters not submitted", len(requested))
        return summary

    with_clb = set(
        ClusterEntry.objects.filter(cluster_id__in=requested, cluster_entry_type=ClusterEntryType.CLB).values_list(
            "cluster_id", flat=True
        )
    )
    candidates = [cid for cid in requested if cid in with_clb]
    summary.skipped = len(requested) - len(candidates)

    batches = [
        {"cluster_ids": candidates[i : i + CLB_SNAPSHOT_BATCH_SIZE]}
        for i in range(0, len(candidates), CLB_SNAPSHOT_BATCH_SIZE)
    ]
    for batch, outcome in zip(batches, task.submit(batches)):
        size = len(batch["cluster_ids"])
        if outcome.outcome == DispatchOutcomeType.ENQUEUED:
            summary.accepted += size
        elif outcome.outcome == DispatchOutcomeType.ENQUEUE_DUPLICATE:
            summary.duplicate += size
        else:
            summary.rejected += size
    logger.info("clb_snapshot: submit summary %s", summary)
    return summary
