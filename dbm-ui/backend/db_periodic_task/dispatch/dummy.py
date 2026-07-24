# -*- coding: utf-8 -*-
"""
Simple verification consumer for the dispatch pipeline.

Purpose: exercise enqueue → pump → worker with a synthetic ``execute``, and
without sharing AIMD / concurrency with production queues such as ``ai``.

Lives under ``dispatch`` (not ``dbm_aiagent``) so framework validation does not
pollute the AI adapter package; it is a plain ``DispatchTask`` because it never
talks to an Agent.

Ownership of ``DummyTaskQueue`` / namespace ``dummy``:
- Only ``DummyTask`` (``dummy.smoke``) may use this queue.
- Do **not** point other ``DispatchTask`` / ``AITask`` subclasses at
  ``DummyTaskQueue`` or ``namespace="dummy"``. Real work belongs on its own
  queue (e.g. ``AITaskQueue``) so verification traffic cannot starve or distort
  production budgets.
"""

import logging
import random
import time
from dataclasses import dataclass
from typing import ClassVar, Optional

from backend.db_periodic_task.dispatch.base import DispatchTask
from backend.db_periodic_task.dispatch.config import DispatchQueueConfig, DispatchTaskConfig
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.queue import DispatchQueue
from backend.db_periodic_task.dispatch.registry import register_dispatch_task

logger = logging.getLogger("root")

DUMMY_NAMESPACE = "dummy"
DUMMY_TASK_KEY = "dummy.smoke"
# Mimic typical agent-call latency when callers omit ``sleep``.
DUMMY_DEFAULT_SLEEP_MIN_SECONDS = 10.0
DUMMY_DEFAULT_SLEEP_MAX_SECONDS = 30.0


@dataclass
class DummyTaskQueueConfig(DispatchQueueConfig):
    """Group ceilings for the verification-only ``dummy`` queue.

    Do not reuse this namespace for production tasks; create a dedicated
    ``DispatchQueueConfig`` / ``DispatchQueue`` pair instead.
    """

    namespace: ClassVar[str] = DUMMY_NAMESPACE


class DummyTaskQueue(DispatchQueue):
    """Verification-only Redis namespace; keep production tasks off this queue.

    Reserved for ``DummyTask``. Binding other tasks here mixes verification
    injects with real work under one AIMD window — use a separate queue instead.
    """

    config_cls = DummyTaskQueueConfig

    @classmethod
    def is_congestion_outcome(cls, outcome: DispatchOutcomeType) -> bool:
        # Match AITaskQueue so ratelimit injects can exercise AIMD decrease.
        return outcome in {
            DispatchOutcomeType.REQUEUED,
            DispatchOutcomeType.REQUEUE_EXHAUSTED,
        }


@dataclass
class DummyTaskConfig(DispatchTaskConfig):
    """Runtime config for ``dummy.smoke``; defaults favor verification runs."""

    task_key: ClassVar[str] = DUMMY_TASK_KEY
    enabled: bool = True


@register_dispatch_task(config_cls=DummyTaskConfig, metadata={"db_type": "test"})
class DummyTask(DispatchTask):
    """Sole consumer of ``DummyTaskQueue``: enqueue → pump → worker path checks.

    Do not subclass this for production work, and do not set
    ``queue_cls = DummyTaskQueue`` on other tasks.

    Work-item inject flags (verification only):
    - ``raise``: raise RuntimeError
    - ``sleep``: sleep seconds (default random 10–30)
    - ``ratelimit`` / ``ratelimit_until``: mimic 429 requeue until ``retry_count`` reaches until
    - ``ratelimit_always``: keep requesting requeue until exhausted
    - ``timeout``: TIMEOUT (no requeue)
    - ``skip_execute``: on_before_execute hook
    - ``delay_seconds`` / ``ready_at``: schedule pending score in the future
    """

    # Exclusive binding: DummyTaskQueue must stay verification-only.
    queue_cls = DummyTaskQueue

    def work_item_id(self, item) -> str:
        if isinstance(item, dict):
            return str(item.get("name") or item.get("work_item_id") or item)
        return str(item)

    def on_before_execute(self, item) -> Optional[str]:
        if isinstance(item, dict) and item.get("skip_execute"):
            return "dummy_skip_execute"
        return None

    def build_job(self, item, *, overrides=None, ready_at=None, config=None) -> DispatchJob:
        job = super().build_job(item, overrides=overrides, ready_at=ready_at, config=config)
        if isinstance(item, dict):
            if item.get("ready_at") is not None:
                job.ready_at = float(item["ready_at"])
            elif item.get("delay_seconds") is not None:
                job.ready_at = time.time() + float(item["delay_seconds"])
        return job

    def execute(self, item, *, job=None, overrides=None) -> DispatchOutcome:
        if isinstance(item, dict) and item.get("raise"):
            raise RuntimeError(f"dummy forced error work_item={self.work_item_id(item)}")

        if isinstance(item, dict) and item.get("timeout"):
            return DispatchOutcome(outcome=DispatchOutcomeType.TIMEOUT)

        if isinstance(item, dict) and (item.get("ratelimit") or item.get("ratelimit_always")):
            retry_count = int(job.retry_count) if job is not None else 0
            cooldown = max(1, int(item.get("cooldown", 1)))
            still_limited = bool(item.get("ratelimit_always")) or retry_count < int(item.get("ratelimit_until", 1))
            if still_limited:
                return DispatchOutcome(
                    outcome=DispatchOutcomeType.REQUEUED,
                    should_requeue=True,
                    requeue_cooldown_seconds=cooldown,
                    exhausted_outcome=DispatchOutcomeType.REQUEUE_EXHAUSTED,
                )
            # ratelimit_until exhausted → fall through to success

        if isinstance(item, dict) and item.get("sleep") is not None:
            sleep_s = float(item.get("sleep") or 0)
        else:
            sleep_s = random.uniform(DUMMY_DEFAULT_SLEEP_MIN_SECONDS, DUMMY_DEFAULT_SLEEP_MAX_SECONDS)
        if sleep_s > 0:
            time.sleep(sleep_s)
        logger.info("DummyTask done work_item=%s sleep=%.2f", self.work_item_id(item), sleep_s)
        return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS)
