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
from typing import Any, Optional

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, HistogramMetricFamily

logger = logging.getLogger("root")

KEY_LATEST = "dispatch:prometheus:latest"
KEY_HEARTBEAT = "dispatch:prometheus:publisher_heartbeat"
EXPORT_LEASE_PREFIX = "dispatch:prometheus:export_lease:"
EXPORT_SLOT_SECONDS = 30
EXPORT_LEASE_TTL_SECONDS = 30
REFRESH_TOLERANCE_SECONDS = 60
SCHEMA_VERSION = 2

HEALTH_STATUSES = ("ok", "cache_miss", "cache_stale", "parse_error", "redis_error")
EVENT_WHITELIST = frozenset(
    {
        "enqueued",
        "ready_peeked",
        "reserved",
        "published",
        "worker_finished",
        "enqueue_duplicate",
        "enqueue_capacity_rejected",
        "enqueue_producer_paused",
        "enqueue_deadline_expired",
        "enqueue_unavailable",
        "blocked",
        "congestion",
        "missing",
        "reserve_unavailable",
        "publish_failed",
        "celery_failure",
        "pump_ticks_skipped",
        "pump_lock_contention",
        "pump_not_started",
    }
)
OUTCOME_WHITELIST = frozenset(
    {
        "success",
        "timeout",
        "requeued",
        "requeue_exhausted",
        "error",
        "skipped",
        "enqueued",
        "enqueue_duplicate",
        "enqueue_capacity_rejected",
        "enqueue_producer_paused",
        "enqueue_deadline_expired",
        "enqueue_unavailable",
        "expired",
    }
)
LATENCY_STAGE_WHITELIST = frozenset({"queue_wait_seconds", "execution_seconds", "pump_seconds"})

_LIVE_GAUGES = (
    ("dbm_dispatch_pending", "pending"),
    ("dbm_dispatch_pending_ready", "pending_ready"),
    ("dbm_dispatch_pending_delayed", "pending_delayed"),
    ("dbm_dispatch_reserved", "reserved"),
    ("dbm_dispatch_max_admitted_jobs", "max_admitted_jobs"),
    ("dbm_dispatch_max_reserved", "max_reserved"),
    ("dbm_dispatch_budget", "budget"),
    ("dbm_dispatch_congestion_window", "congestion_window"),
    ("dbm_dispatch_pump_paused", "pump_paused"),
    ("dbm_dispatch_producer_paused", "producer_paused"),
    ("dbm_dispatch_reserved_saturated", "reserved_saturated"),
)


class DispatchMetricsCollector:
    """Read one schema-v2 cumulative snapshot and expose Prometheus families."""

    def __init__(self, client: Optional[Any] = None):
        self._client = client

    def describe(self):
        families = [
            GaugeMetricFamily(
                "dbm_dispatch_collector_health",
                "Dispatch collector health (one-hot over a fixed status set).",
                labels=["status"],
            )
        ]
        for metric, _key in _LIVE_GAUGES:
            families.append(GaugeMetricFamily(metric, f"Dispatch {metric} (per namespace)", labels=["namespace"]))
        families.extend(
            [
                CounterMetricFamily(
                    "dbm_dispatch_events",
                    "Cumulative dispatch events per namespace.",
                    labels=["namespace", "event"],
                ),
                HistogramMetricFamily(
                    "dbm_dispatch_latency_seconds",
                    "Cumulative dispatch latency histogram per stage.",
                    labels=["namespace", "stage"],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_task_pending",
                    "Pending work items per dispatch task.",
                    labels=["namespace", "task_key"],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_task_reserved",
                    "Reserved work items per dispatch task.",
                    labels=["namespace", "task_key"],
                ),
                CounterMetricFamily(
                    "dbm_dispatch_task_outcome",
                    "Cumulative outcomes per dispatch task.",
                    labels=["namespace", "task_key", "outcome"],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_report_partial",
                    "Dispatch data completeness per namespace (1 = incomplete).",
                    labels=["namespace"],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_refresh_timestamp_seconds",
                    "Unix timestamp of the latest cumulative snapshot.",
                    labels=[],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_publisher_heartbeat_timestamp_seconds",
                    "Unix timestamp of the last publisher lock acquisition.",
                    labels=[],
                ),
                GaugeMetricFamily(
                    "dbm_dispatch_metrics_started_at_timestamp_seconds",
                    "Unix timestamp when the current namespace metric generation started.",
                    labels=["namespace"],
                ),
            ]
        )
        return families

    def _get_client(self):
        if self._client is None:
            from django_redis import get_redis_connection

            self._client = get_redis_connection("default")
        return self._client

    def _acquire_export_lease(self, client) -> bool:
        slot = int(time.time()) // EXPORT_SLOT_SECONDS
        key = f"{EXPORT_LEASE_PREFIX}{slot}"
        return bool(client.set(key, "1", nx=True, ex=EXPORT_LEASE_TTL_SECONDS))

    def _load_payload(self, client) -> tuple[Optional[dict], str]:
        raw = client.get(KEY_LATEST)
        if raw is None:
            return None, "cache_miss"
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("dispatch collector: payload corrupt: %s", exc)
            return None, "parse_error"
        if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
            return None, "parse_error"
        return payload, "ok"

    def collect(self):
        health = GaugeMetricFamily(
            "dbm_dispatch_collector_health",
            "Dispatch collector health (one-hot over a fixed status set).",
            labels=["status"],
        )
        try:
            client = self._get_client()
            lease_held = self._acquire_export_lease(client)
        except Exception:
            self._set_health(health, "redis_error")
            return [health]
        if not lease_held:
            return []
        try:
            payload, status = self._load_payload(client)
        except Exception:
            self._set_health(health, "redis_error")
            return [health]
        if status != "ok":
            self._set_health(health, status)
            return [health]

        try:
            families = self._build_families(payload)
        except Exception as exc:
            logger.warning("dispatch collector: invalid schema-v2 payload: %s", exc)
            self._set_health(health, "parse_error")
            return [health]
        self._set_health(health, self._freshness_status(payload))
        return [health] + families

    def _build_families(self, payload: dict) -> list:
        families: list = []
        for metric, key in _LIVE_GAUGES:
            family = GaugeMetricFamily(metric, f"Dispatch {metric} (per namespace)", labels=["namespace"])
            for queue in payload.get("queues") or []:
                value = queue.get(key)
                if value is not None:
                    family.add_metric([queue.get("namespace") or ""], float(value))
            families.append(family)
        families.extend(
            [
                self._events_family(payload),
                self._latency_family(payload),
                *self._task_families(payload),
                self._partial_family(payload),
                self._refresh_family(payload),
                self._heartbeat_family(),
                self._started_at_family(payload),
            ]
        )
        return families

    def _events_family(self, payload: dict) -> CounterMetricFamily:
        family = CounterMetricFamily(
            "dbm_dispatch_events",
            "Cumulative dispatch events per namespace.",
            labels=["namespace", "event"],
        )
        for queue in payload.get("queues") or []:
            namespace = queue.get("namespace") or ""
            for event, count in (queue.get("events") or {}).items():
                if event in EVENT_WHITELIST and count is not None:
                    family.add_metric([namespace, event], float(count))
        return family

    def _latency_family(self, payload: dict) -> HistogramMetricFamily:
        family = HistogramMetricFamily(
            "dbm_dispatch_latency_seconds",
            "Cumulative dispatch latency histogram per stage.",
            labels=["namespace", "stage"],
        )
        for queue in payload.get("queues") or []:
            namespace = queue.get("namespace") or ""
            for stage, histogram in (queue.get("histograms") or {}).items():
                if stage not in LATENCY_STAGE_WHITELIST or not isinstance(histogram, dict):
                    continue
                raw_buckets = histogram.get("buckets") or []
                buckets: list[tuple[str, float]] = []
                for item in raw_buckets:
                    if not isinstance(item, (list, tuple)) or len(item) != 2:
                        continue
                    buckets.append((str(item[0]), float(item[1])))
                if not buckets or buckets[-1][0] != "+Inf":
                    continue
                family.add_metric(
                    [namespace, stage.removesuffix("_seconds")],
                    buckets=buckets,
                    sum_value=float(histogram.get("sum") or 0.0),
                )
        return family

    def _task_families(self, payload: dict) -> list:
        pending_family = GaugeMetricFamily(
            "dbm_dispatch_task_pending",
            "Pending work items per dispatch task.",
            labels=["namespace", "task_key"],
        )
        reserved_family = GaugeMetricFamily(
            "dbm_dispatch_task_reserved",
            "Reserved work items per dispatch task.",
            labels=["namespace", "task_key"],
        )
        outcome_family = CounterMetricFamily(
            "dbm_dispatch_task_outcome",
            "Cumulative outcomes per dispatch task.",
            labels=["namespace", "task_key", "outcome"],
        )
        for task in payload.get("tasks") or []:
            task_key = task.get("task_key") or ""
            namespace = task.get("namespace") or ""
            if task.get("pending") is not None:
                pending_family.add_metric([namespace, task_key], float(task["pending"]))
            if task.get("reserved") is not None:
                reserved_family.add_metric([namespace, task_key], float(task["reserved"]))
            for outcome, count in (task.get("outcomes") or {}).items():
                if outcome in OUTCOME_WHITELIST and count is not None:
                    outcome_family.add_metric([namespace, task_key, outcome], float(count))
        return [pending_family, reserved_family, outcome_family]

    def _partial_family(self, payload: dict) -> GaugeMetricFamily:
        family = GaugeMetricFamily(
            "dbm_dispatch_report_partial",
            "Dispatch data completeness per namespace (1 = incomplete).",
            labels=["namespace"],
        )
        for queue in payload.get("queues") or []:
            family.add_metric(
                [queue.get("namespace") or ""],
                float(1 if queue.get("partial") else 0),
            )
        return family

    def _refresh_family(self, payload: dict) -> GaugeMetricFamily:
        family = GaugeMetricFamily(
            "dbm_dispatch_refresh_timestamp_seconds",
            "Unix timestamp of the latest cumulative snapshot.",
            labels=[],
        )
        value = payload.get("generated_at")
        if value is not None:
            family.add_metric([], float(value))
        return family

    def _heartbeat_family(self) -> GaugeMetricFamily:
        family = GaugeMetricFamily(
            "dbm_dispatch_publisher_heartbeat_timestamp_seconds",
            "Unix timestamp of the last publisher lock acquisition.",
            labels=[],
        )
        try:
            raw = self._get_client().get(KEY_HEARTBEAT)
            if raw is not None:
                family.add_metric([], float(raw))
        except Exception:
            pass
        return family

    def _started_at_family(self, payload: dict) -> GaugeMetricFamily:
        family = GaugeMetricFamily(
            "dbm_dispatch_metrics_started_at_timestamp_seconds",
            "Unix timestamp when the current namespace metric generation started.",
            labels=["namespace"],
        )
        for queue in payload.get("queues") or []:
            value = queue.get("metrics_started_at")
            if value is not None:
                family.add_metric([queue.get("namespace") or ""], float(value))
        return family

    def _freshness_status(self, payload: dict) -> str:
        generated_at = payload.get("generated_at")
        try:
            age = time.time() - float(generated_at)
        except (TypeError, ValueError):
            return "cache_stale"
        return "cache_stale" if age > REFRESH_TOLERANCE_SECONDS else "ok"

    @staticmethod
    def _set_health(family: GaugeMetricFamily, status: str) -> None:
        if status not in HEALTH_STATUSES:
            status = "redis_error"
        for candidate in HEALTH_STATUSES:
            family.add_metric([candidate], 1.0 if candidate == status else 0.0)
