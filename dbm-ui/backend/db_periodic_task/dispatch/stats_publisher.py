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

import json
import logging
import time
import uuid
from datetime import timedelta
from typing import Any, Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.lua import RELEASE_LOCK_LUA, compile_script, eval_script
from backend.db_periodic_task.dispatch.observability import DispatchStats, QueueDispatchReport
from backend.db_periodic_task.register import register_periodic_task

"""Publish one compact schema-v2 cumulative snapshot to global Redis.

Namespace shards remain the source of truth. The publisher lock elects one
Celery process to copy live gauges, cumulative counters, and histogram
sufficient statistics every 30 seconds. Missing cycles are caught up by the
next cumulative snapshot.
"""

logger = logging.getLogger("root")

PUBLISH_INTERVAL_SECONDS = 30
LATEST_KEY_TTL_SECONDS = 15 * 60

KEY_LATEST = "dispatch:prometheus:latest"
KEY_HEARTBEAT = "dispatch:prometheus:publisher_heartbeat"
KEY_PUBLISHER_LOCK = "dispatch:prometheus:publisher_lock"

PUBLISHER_LOCK_TTL_SECONDS = 60
PUBLISHER_LOCK_OWNER_PREFIX = "stats_publisher:"

SCHEMA_VERSION = 2
MAX_TASK_EXPORTS = 500
PAYLOAD_WARN_BYTES = 1024 * 1024

_release_lock_script = compile_script(RELEASE_LOCK_LUA)


def _nonneg(value: Any) -> Optional[int]:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _try_acquire_publisher_lock(client, owner: str) -> bool:
    try:
        return bool(client.set(KEY_PUBLISHER_LOCK, owner, nx=True, ex=PUBLISHER_LOCK_TTL_SECONDS))
    except Exception as exc:
        logger.warning("dispatch stats publisher: lock acquisition failed: %s", exc)
        return False


def _release_publisher_lock(client, owner: str) -> None:
    try:
        eval_script(_release_lock_script, client=client, keys=[KEY_PUBLISHER_LOCK], args=[owner])
    except Exception as exc:
        logger.warning("dispatch stats publisher: lock release failed: %s", exc)


def _update_heartbeat(client, now: float) -> None:
    try:
        client.set(KEY_HEARTBEAT, str(now), ex=LATEST_KEY_TTL_SECONDS)
    except Exception as exc:
        logger.warning("dispatch stats publisher: heartbeat update failed: %s", exc)


def _queue_payload(report: QueueDispatchReport) -> dict:
    controller = report.controller or {}
    config = report.config or {}
    diagnosis = report.diagnosis or []
    histograms = {
        stage: {
            "buckets": [[upper_bound, count] for upper_bound, count in summary.buckets],
            "count": int(summary.count),
            "sum": float(summary.sum),
        }
        for stage, summary in report.histograms.items()
    }
    return {
        "namespace": report.namespace,
        "pending": _nonneg(report.pending_total),
        "pending_ready": _nonneg(report.pending_ready),
        "pending_delayed": _nonneg(report.pending_delayed),
        "reserved": _nonneg(report.reserved),
        "max_admitted_jobs": _nonneg(config.get("max_admitted_jobs")),
        "max_reserved": _nonneg(config.get("max_reserved")),
        "budget": _nonneg(controller.get("effective_budget")),
        "congestion_window": _nonneg(controller.get("congestion_window")),
        "pump_paused": 1 if (report.pump_lock or {}).get("state") == "paused" else 0,
        "producer_paused": 1 if (report.producer_gate or {}).get("state") == "paused" else 0,
        "reserved_saturated": 1 if "reserved_saturated" in diagnosis else 0,
        "events": dict(report.events or {}),
        "histograms": histograms,
        "metrics_started_at": report.metrics_started_at,
        "partial": 1 if report.partial else 0,
    }


def _select_allowed_tasks(snapshot: Any) -> tuple[set[str], set[str]]:
    ordered = sorted({report.task_key for report in snapshot.task_reports})
    if len(ordered) <= MAX_TASK_EXPORTS:
        return set(ordered), set()
    dropped = set(ordered[MAX_TASK_EXPORTS:])
    dropped_ns = {report.namespace for report in snapshot.task_reports if report.task_key in dropped}
    logger.warning(
        "dispatch stats publisher: task export capped at %d (registered %d); truncating %d task(s)",
        MAX_TASK_EXPORTS,
        len(ordered),
        len(dropped),
    )
    return set(ordered[:MAX_TASK_EXPORTS]), dropped_ns


def build_payload(snapshot: Any) -> dict:
    allowed, truncated_ns = _select_allowed_tasks(snapshot)
    partial_task_ns = {report.namespace for report in snapshot.task_reports if report.partial}
    queues = [_queue_payload(report) for report in snapshot.queues]
    for queue in queues:
        if queue["namespace"] in truncated_ns or queue["namespace"] in partial_task_ns:
            queue["partial"] = 1
    tasks = [
        {
            "task_key": report.task_key,
            "namespace": report.namespace,
            "pending": _nonneg(report.pending),
            "reserved": _nonneg(report.reserved),
            "outcomes": dict(report.outcomes or {}),
            "partial": 1 if report.partial else 0,
        }
        for report in snapshot.task_reports
        if report.task_key in allowed
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": snapshot.timestamp,
        "queues": queues,
        "tasks": tasks,
    }


def publish_dispatch_stats() -> None:
    now = time.time()
    client = routing.global_conn()
    owner = f"{PUBLISHER_LOCK_OWNER_PREFIX}{uuid.uuid4().hex}"
    if not _try_acquire_publisher_lock(client, owner):
        logger.info("dispatch stats publisher: another process holds the lock; skip")
        return
    try:
        _update_heartbeat(client, now)
        try:
            snapshot = DispatchStats.snapshot()
        except Exception:
            logger.exception("dispatch stats publisher: snapshot failed; keeping existing cache")
            return
        payload = build_payload(snapshot)
        blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        byte_size = len(blob.encode("utf-8"))
        if byte_size > PAYLOAD_WARN_BYTES:
            logger.warning(
                "dispatch stats publisher: payload exceeds %d bytes (%d)",
                PAYLOAD_WARN_BYTES,
                byte_size,
            )
        client.set(KEY_LATEST, blob, ex=LATEST_KEY_TTL_SECONDS)
    finally:
        _release_publisher_lock(client, owner)


@register_periodic_task(run_every=timedelta(seconds=PUBLISH_INTERVAL_SECONDS))
def dispatch_publish_stats():
    try:
        publish_dispatch_stats()
    except Exception:
        logger.exception("dispatch stats publisher: unexpected failure")
