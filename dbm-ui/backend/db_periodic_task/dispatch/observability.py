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
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional, TextIO

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.config import PUMP_INTERVAL_SECONDS, DispatchPumpConfig
from backend.db_periodic_task.dispatch.controller import PumpController
from backend.db_periodic_task.dispatch.metrics import DispatchMetrics, HistogramSummary, tick_id
from backend.db_periodic_task.dispatch.queue import KEY_REGISTERED, DispatchQueue

_BAR_WIDTH = 20
_ANSI_CLEAR = "\033[2J\033[H"


def _progress_bar(value: int | float, capacity: int | float, width: int = _BAR_WIDTH) -> str:
    try:
        current = max(0.0, float(value))
        total = float(capacity)
    except (TypeError, ValueError):
        return f"[{'?' * width}]"
    filled = 0 if total <= 0 else max(0, min(width, int(round(width * current / total))))
    return f"[{'#' * filled}{'-' * (width - filled)}]"


def _fmt_int(value: Any, default: str = "?") -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return default


def _fmt_epoch(timestamp: float | int | None, default: str = "?") -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(timestamp)))
    except (TypeError, ValueError, OSError, OverflowError):
        return default


def _fmt_tick(tick: int | float, default: str = "?") -> str:
    try:
        return _fmt_epoch(int(tick) * PUMP_INTERVAL_SECONDS, default=default)
    except (TypeError, ValueError):
        return default


def _dash_row(label: str, bar: str = "", value: str = "", note: str = "") -> str:
    return f"{label:<10}  {bar:<22}  {value:<14}  {note}".rstrip()


def _fmt_counter_group(values: dict[str, int], fields: tuple[tuple[str, str], ...]) -> str:
    return "  ".join(f"{label}={_fmt_int(values.get(name, 0))}" for name, label in fields)


_FLOW_COUNTERS = (
    ("enqueued", "enq"),
    ("ready_peeked", "ready"),
    ("reserved", "res"),
    ("published", "sent"),
    ("worker_finished", "done"),
)
_TICK_FLOW_COUNTERS = (
    ("ready_peeked", "ready"),
    ("published", "sent"),
    ("worker_finished", "done"),
)
_ISSUE_COUNTERS = (
    ("enqueue_duplicate", "dup"),
    ("enqueue_capacity_rejected", "cap_reject"),
    ("enqueue_producer_paused", "prod_reject"),
    ("enqueue_deadline_expired", "expired"),
    ("enqueue_unavailable", "unavail"),
    ("blocked", "blocked"),
    ("congestion", "congest"),
    ("missing", "missing"),
    ("reserve_unavailable", "res_unavail"),
    ("publish_failed", "pub_fail"),
    ("celery_failure", "celery_fail"),
    ("pump_ticks_skipped", "skipped"),
    ("pump_lock_contention", "lock_contend"),
    ("pump_not_started", "not_started"),
)
_TICK_ISSUE_COUNTERS = (
    ("blocked", "blocked"),
    ("congestion", "congest"),
    ("publish_failed", "pub_fail"),
)


def _fmt_decide_note(decide_tick_id: int, last_tick_id: int) -> str:
    if decide_tick_id < 0:
        return "decide=?"
    try:
        last = int(last_tick_id)
    except (TypeError, ValueError):
        return f"decide=#{decide_tick_id}"
    delta = decide_tick_id - last
    sign = f"+{delta}" if delta > 0 else str(delta)
    return f"decide=#{decide_tick_id} (last=#{last}, Δ{sign} tick)"


def _decide_tick_delta(controller: dict[str, Any], last_tick_id: int) -> Optional[int]:
    try:
        decide_tick_id = int(controller.get("tick_id", ""))
        return decide_tick_id - int(last_tick_id) if decide_tick_id >= 0 else None
    except (TypeError, ValueError):
        return None


@dataclass
class QueueDispatchReport:
    namespace: str
    timestamp: float
    tick_seconds: int
    pending_total: int
    pending_ready: int
    pending_delayed: int
    reserved: int
    config: dict[str, Any]
    controller: dict[str, Any]
    events: dict[str, int]
    histograms: dict[str, HistogramSummary]
    metrics_started_at: Optional[float]
    pump_lock: dict[str, Any] = field(default_factory=dict)
    producer_gate: dict[str, Any] = field(default_factory=dict)
    diagnosis: list[str] = field(default_factory=list)
    partial: bool = False
    last_tick_id: int = 0
    last_tick_counts: dict[str, int] = field(default_factory=dict)

    def format_summary(self) -> str:
        limits = (
            f"admitted={self.config.get('max_admitted_jobs', '?')} " f"reserved={self.config.get('max_reserved', '?')}"
        )
        pump_state = str(self.pump_lock.get("state") or "unknown")
        producer_state = str(self.producer_gate.get("state") or "unknown")
        lines = [
            (
                f"dispatch queue[{self.namespace}] @ {_fmt_epoch(self.timestamp)} "
                f"partial={self.partial} pump={pump_state} producer={producer_state}"
            ),
            f"  pending={self.pending_total} ready={self.pending_ready} delayed={self.pending_delayed}",
            (
                f"  reserved={self.reserved} budget={self.controller.get('effective_budget', '?')} "
                f"slots={self.controller.get('available_slots', '?')} "
                f"cwnd={self.controller.get('congestion_window', '?')} {limits}"
            ),
            f"  metrics_generation_started={_fmt_epoch(self.metrics_started_at)}",
        ]
        if self.last_tick_counts:
            tick_bits = ", ".join(f"{key}={value}" for key, value in sorted(self.last_tick_counts.items()))
            lines.append(f"  last_tick={_fmt_tick(self.last_tick_id)} (#{self.last_tick_id}): {tick_bits}")
        if self.events:
            lines.append(
                "  generation_events: " + ", ".join(f"{key}={value}" for key, value in sorted(self.events.items()))
            )
        if self.diagnosis:
            lines.append("  diagnosis: " + ", ".join(self.diagnosis))
        return "\n".join(lines)

    def format_dashboard(self) -> str:
        max_reserved = int(self.config.get("max_reserved", 0) or 0)
        max_admitted = int(self.config.get("max_admitted_jobs", 0) or 0)
        budget = int(self.controller.get("effective_budget", 0) or 0)
        raw_slots = self.controller.get("available_slots")
        try:
            available_slots = (
                max(0, max_reserved - max(0, int(self.reserved)))
                if raw_slots is None or raw_slots == ""
                else int(raw_slots)
            )
        except (TypeError, ValueError):
            available_slots = 0
        try:
            congestion_window = int(self.controller.get("congestion_window") or 0)
        except (TypeError, ValueError):
            congestion_window = 0
        aimd = str(self.controller.get("aimd_action", "?") or "?")
        pump_state = str(self.pump_lock.get("state") or "unknown")
        pump_ttl = self.pump_lock.get("ttl_seconds")
        pump_label = pump_state
        if pump_state == "paused":
            pump_label += "(until_resume)" if pump_ttl == -1 else f"({_fmt_int(pump_ttl)}s)"
        producer_state = str(self.producer_gate.get("state") or "unknown")
        producer_ttl = self.producer_gate.get("ttl_seconds")
        producer_label = producer_state
        if producer_state == "paused":
            producer_label += "(until_resume)" if producer_ttl == -1 else f"({_fmt_int(producer_ttl)}s)"
        try:
            decide_tick_id = int(self.controller.get("tick_id", ""))
        except (TypeError, ValueError):
            decide_tick_id = -1

        live_slots = max(0, max_reserved - max(0, int(self.reserved))) if max_reserved else 0
        admitted = max(0, int(self.pending_total)) + max(0, int(self.reserved))
        admitted_cap = max_admitted or max(admitted, 1)
        reserved_cap = max_reserved or max(self.reserved, 1)
        issues = [item for item in self.diagnosis if item != "healthy"]
        status = (
            "PAUSED"
            if pump_state == "paused" or producer_state == "paused"
            else ("PARTIAL" if self.partial else ("WARN" if issues else "HEALTHY"))
        )
        header = (
            f"dispatch[{self.namespace}]  {_fmt_epoch(self.timestamp)}  status={status}  "
            f"pump={pump_label}  producer={producer_label}  generation={_fmt_epoch(self.metrics_started_at)}"
        )
        rule = "-" * max(100, len(header))
        lines = [
            header,
            rule,
            _dash_row(
                "queue",
                _progress_bar(admitted, admitted_cap),
                f"{_fmt_int(admitted)}/{_fmt_int(max_admitted or '?')}",
                (
                    f"pending={_fmt_int(self.pending_total)}  ready={_fmt_int(self.pending_ready)}  "
                    f"delay={_fmt_int(self.pending_delayed)}"
                ),
            ),
            _dash_row(
                "reserved",
                _progress_bar(self.reserved, reserved_cap),
                f"{_fmt_int(self.reserved)}/{_fmt_int(max_reserved or '?')}",
                f"free={_fmt_int(live_slots)}",
            ),
            _dash_row(
                "control",
                "",
                f"budget={_fmt_int(budget)}",
                (
                    f"slots={_fmt_int(available_slots)}  cwnd={_fmt_int(congestion_window)}  aimd={aimd}  "
                    f"{_fmt_decide_note(decide_tick_id, self.last_tick_id)}"
                ),
            ),
            rule,
            (
                f"tick #{self.last_tick_id}  {_fmt_tick(self.last_tick_id)}  "
                f"{_fmt_counter_group(self.last_tick_counts, _TICK_FLOW_COUNTERS)}"
            ),
            "tick issues  " + _fmt_counter_group(self.last_tick_counts, _TICK_ISSUE_COUNTERS),
            rule,
            f"generation flow    {_fmt_counter_group(self.events, _FLOW_COUNTERS)}",
            f"generation issues  {_fmt_counter_group(self.events, _ISSUE_COUNTERS)}",
        ]
        if issues:
            lines.extend((rule, f"diagnosis  {', '.join(issues)}"))
        return "\n".join(lines)


@dataclass
class TaskDispatchReport:
    task_key: str
    timestamp: float
    pending: int
    reserved: int
    admitted: int
    outcomes: dict[str, int]
    partial: bool = False
    namespace: str = ""
    metrics_started_at: Optional[float] = None

    def format_summary(self) -> str:
        values = ", ".join(f"{key}={value}" for key, value in sorted(self.outcomes.items())) or "no metrics"
        return (
            f"dispatch task[{self.task_key}] ns={self.namespace or '?'} "
            f"generation={_fmt_epoch(self.metrics_started_at)} partial={self.partial}\n"
            f"  pending={self.pending} reserved={self.reserved} admitted={self.admitted}\n"
            f"  {values}"
        )


@dataclass
class DispatchStatsSnapshot:
    timestamp: float
    tick_seconds: int
    pending_total: int
    pending_ready: int
    pending_delayed: int
    reserved: int
    registered: dict[str, Any]
    pump_config: dict[str, Any]
    queues: list[QueueDispatchReport]
    task_reports: list[TaskDispatchReport] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def format_summary(self) -> str:
        lines = [
            f"dispatch stats @ {_fmt_epoch(self.timestamp)} tick={self.tick_seconds}s",
            f"  pending: total={self.pending_total} ready={self.pending_ready} delayed={self.pending_delayed}",
            f"  reserved={self.reserved}",
            f"  registered_tasks={len(self.registered)}",
        ]
        lines.extend(report.format_summary() for report in self.queues)
        if self.task_reports:
            lines.append(f"  tasks={len(self.task_reports)}")
            lines.extend(report.format_summary() for report in self.task_reports)
        return "\n".join(lines)

    def format_dashboard(self) -> str:
        lines = [
            f"dispatch stats @ {_fmt_epoch(self.timestamp)} tick={self.tick_seconds}s",
            (
                f"pending total={self.pending_total} ready={self.pending_ready} "
                f"delayed={self.pending_delayed}  reserved={self.reserved}"
            ),
            "",
        ]
        for report in self.queues:
            lines.extend((report.format_dashboard(), ""))
        return "\n".join(lines).rstrip()


class DispatchStats:
    """Read current dispatch state without historical key fan-out."""

    @classmethod
    def queue_report(cls, namespace: str) -> QueueDispatchReport:
        now = time.time()
        queue_cls = DispatchQueue.queue_for_namespace(namespace)
        if queue_cls is None:
            return QueueDispatchReport(
                namespace=namespace,
                timestamp=now,
                tick_seconds=PUMP_INTERVAL_SECONDS,
                pending_total=-1,
                pending_ready=-1,
                pending_delayed=-1,
                reserved=-1,
                config={},
                controller={},
                events={},
                histograms={},
                metrics_started_at=None,
                diagnosis=["unregistered_queue"],
                partial=True,
            )

        partial = False
        try:
            config_obj = queue_cls.load_config()
            config = {
                "max_admitted_jobs": config_obj.max_admitted_jobs,
                "max_reserved": config_obj.max_reserved,
            }
        except Exception:
            config = {}
            partial = True
        try:
            events = DispatchMetrics.read_queue_events(namespace)
            histograms = DispatchMetrics.read_histograms(namespace)
            metrics_started_at = DispatchMetrics.read_started_at(namespace)
        except Exception:
            events = {}
            histograms = {}
            metrics_started_at = None
            partial = True
        controller = PumpController.read_state(namespace)
        if not controller:
            partial = True

        from backend.db_periodic_task.dispatch.pump import inspect_queue_pump_lock

        pump_lock_raw = inspect_queue_pump_lock(namespace)
        pump_lock = pump_lock_raw if isinstance(pump_lock_raw, dict) else {}
        from backend.db_periodic_task.dispatch.producer import inspect_queue_producer_gate

        producer_gate_raw = inspect_queue_producer_gate(namespace)
        producer_gate = producer_gate_raw if isinstance(producer_gate_raw, dict) else {}
        last_tick_id = tick_id(now) - 1
        try:
            last_tick_counts = DispatchMetrics.queue_tick_counts(namespace, last_tick_id)
        except Exception:
            last_tick_counts = {}
            partial = True

        pending_total = queue_cls.pending_count()
        pending_ready = queue_cls.ready_count(now)
        pending_delayed = queue_cls.delayed_count(now)
        reserved = queue_cls.reserved_count()
        if min(pending_total, pending_ready, pending_delayed, reserved) < 0:
            partial = True
        report = QueueDispatchReport(
            namespace=namespace,
            timestamp=now,
            tick_seconds=PUMP_INTERVAL_SECONDS,
            pending_total=pending_total,
            pending_ready=pending_ready,
            pending_delayed=pending_delayed,
            reserved=reserved,
            config=config,
            controller=controller,
            events=events,
            histograms=histograms,
            metrics_started_at=metrics_started_at,
            pump_lock=pump_lock,
            producer_gate=producer_gate,
            partial=partial,
            last_tick_id=last_tick_id,
            last_tick_counts=last_tick_counts,
        )
        report.diagnosis = cls._diagnose(report)
        return report

    @classmethod
    def task_report(cls, task_key: str) -> TaskDispatchReport:
        now = time.time()
        registered = cls._load_registered()
        metadata = registered.get(task_key)
        namespace = metadata.get("namespace", "") if isinstance(metadata, dict) else ""
        queue_cls = DispatchQueue.queue_for_namespace(namespace) if namespace else None
        pending, reserved = queue_cls.task_counts(task_key) if queue_cls else (-1, -1)
        admitted = pending + reserved if pending >= 0 and reserved >= 0 else -1
        partial = metadata is None or admitted < 0
        try:
            outcomes = DispatchMetrics.read_task_outcomes(namespace, task_key) if namespace else {}
            metrics_started_at = DispatchMetrics.read_started_at(namespace) if namespace else None
        except Exception:
            outcomes = {}
            metrics_started_at = None
            partial = True
        return TaskDispatchReport(
            task_key=task_key,
            namespace=namespace,
            timestamp=now,
            pending=pending,
            reserved=reserved,
            admitted=admitted,
            outcomes=outcomes,
            metrics_started_at=metrics_started_at,
            partial=partial,
        )

    @classmethod
    def diagnose_queue(cls, namespace: str) -> list[str]:
        return cls.queue_report(namespace).diagnosis

    @classmethod
    def watch_queue(
        cls,
        namespace: str,
        *,
        interval_seconds: Optional[float] = None,
        ticks: Optional[int] = None,
        clear: bool = True,
        stream: Optional[TextIO] = None,
    ) -> None:
        """Live-refresh current queue/controller/last-tick state (Ctrl-C to stop)."""
        if not namespace:
            raise ValueError("namespace is required")
        out = stream or sys.stdout
        interval = float(2.0 if interval_seconds is None else interval_seconds)
        if interval < 0:
            raise ValueError("interval_seconds must be >= 0")
        use_clear = bool(clear and hasattr(out, "isatty") and out.isatty())
        n = 0
        try:
            while ticks is None or n < ticks:
                frame = cls.queue_report(namespace).format_dashboard()
                if use_clear:
                    out.write(_ANSI_CLEAR)
                elif n:
                    out.write("\n" + "=" * 72 + "\n")
                out.write(frame + "\n")
                out.flush()
                n += 1
                if ticks is not None and n >= ticks:
                    break
                if interval > 0:
                    time.sleep(interval)
        except KeyboardInterrupt:
            out.write("\n")
            out.flush()

    @staticmethod
    def _diagnose(report: QueueDispatchReport) -> list[str]:
        diagnosis: list[str] = []
        pump_state = str(report.pump_lock.get("state") or "")
        if pump_state == "paused":
            diagnosis.append("pump_paused")
        else:
            delta = _decide_tick_delta(report.controller, report.last_tick_id)
            if delta is not None and delta < 0:
                diagnosis.append("pump_delayed")
        if str(report.producer_gate.get("state") or "") == "paused":
            diagnosis.append("producer_paused")
        max_reserved = int(report.config.get("max_reserved", 0) or 0)
        if max_reserved and report.reserved >= max_reserved:
            diagnosis.append("reserved_saturated")
        if report.last_tick_counts.get("publish_failed", 0):
            diagnosis.append("broker_publish_failures")
        if report.last_tick_counts.get("blocked", 0):
            diagnosis.append("reservation_blocked")
        if report.partial:
            diagnosis.append("metrics_partial")
        return diagnosis or ["healthy"]

    @classmethod
    def snapshot(cls, *, include_tasks: bool = True) -> DispatchStatsSnapshot:
        now = time.time()
        registered = cls._load_registered()
        queue_classes = DispatchQueue.registered_queues()
        queues = [cls.queue_report(queue_cls.namespace) for queue_cls in queue_classes]
        queue_by_ns = {queue_cls.namespace: queue_cls for queue_cls in queue_classes}
        started_by_ns = {report.namespace: report.metrics_started_at for report in queues}
        task_reports: list[TaskDispatchReport] = []
        if include_tasks:
            for task_key, metadata in registered.items():
                namespace = metadata.get("namespace", "") if isinstance(metadata, dict) else ""
                queue_cls = queue_by_ns.get(namespace) if namespace else None
                pending, reserved = queue_cls.task_counts(task_key) if queue_cls else (-1, -1)
                admitted = pending + reserved if pending >= 0 and reserved >= 0 else -1
                partial = metadata is None or admitted < 0
                try:
                    outcomes = DispatchMetrics.read_task_outcomes(namespace, task_key) if namespace else {}
                except Exception:
                    outcomes = {}
                    partial = True
                task_reports.append(
                    TaskDispatchReport(
                        task_key=task_key,
                        namespace=namespace,
                        timestamp=now,
                        pending=pending,
                        reserved=reserved,
                        admitted=admitted,
                        outcomes=outcomes,
                        metrics_started_at=started_by_ns.get(namespace),
                        partial=partial,
                    )
                )
        return DispatchStatsSnapshot(
            timestamp=now,
            tick_seconds=PUMP_INTERVAL_SECONDS,
            pending_total=DispatchQueue.aggregate_pending_count(),
            pending_ready=DispatchQueue.aggregate_ready_count(now),
            pending_delayed=DispatchQueue.aggregate_delayed_count(now),
            reserved=DispatchQueue.aggregate_reserved_count(),
            registered=registered,
            pump_config=cls._load_pump_config(),
            queues=queues,
            task_reports=task_reports,
        )

    @staticmethod
    def _load_registered() -> dict[str, Any]:
        try:
            raw = routing.global_conn().hgetall(KEY_REGISTERED) or {}
            result = {}
            for key, value in raw.items():
                key = key.decode() if isinstance(key, bytes) else key
                value = value.decode() if isinstance(value, bytes) else value
                result[key] = json.loads(value) if isinstance(value, str) else value
            return result
        except Exception:
            return {}

    @staticmethod
    def _load_pump_config() -> dict[str, int]:
        try:
            return {"max_parallel_queues": DispatchPumpConfig().max_parallel_queues}
        except Exception:
            return {}

    @classmethod
    def parse_raw(cls, raw: dict) -> DispatchStatsSnapshot:
        queues = []
        for item in raw.get("queues", []):
            item = dict(item)
            item["histograms"] = {
                stage: HistogramSummary(**summary) for stage, summary in (item.get("histograms") or {}).items()
            }
            queues.append(QueueDispatchReport(**item))
        return DispatchStatsSnapshot(
            timestamp=float(raw.get("timestamp", 0)),
            tick_seconds=int(raw.get("tick_seconds", PUMP_INTERVAL_SECONDS)),
            pending_total=int(raw.get("pending_total", -1)),
            pending_ready=int(raw.get("pending_ready", -1)),
            pending_delayed=int(raw.get("pending_delayed", -1)),
            reserved=int(raw.get("reserved", -1)),
            registered=raw.get("registered", {}),
            pump_config=raw.get("pump_config", {}),
            queues=queues,
            task_reports=[TaskDispatchReport(**item) for item in raw.get("task_reports", [])],
        )
