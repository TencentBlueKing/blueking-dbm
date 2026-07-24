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

# Unit tests for enqueue-time priority/spread helpers and submit plumbing.
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.db_periodic_task.dispatch.scheduling import at_front, resolve_ready_at, spread


class TestSchedulingHelpers:
    def test_resolve_ready_at_none_float_callable(self):
        assert resolve_ready_at(None, 0, "x") is None
        assert resolve_ready_at(123.0, 5, "x") == 123.0
        assert resolve_ready_at(lambda index, item: 100.0 + index, 3, "x") == 103.0

    def test_at_front_is_earlier_than_base(self):
        assert at_front(60, base=1000.0) == 940.0
        # negative offset is clamped to 0 (never schedules into the future here)
        assert at_front(-10, base=1000.0) == 1000.0

    def test_spread_is_monotonic_and_within_window(self):
        schedule = spread(window_seconds=100.0, base=0.0)
        values = [resolve_ready_at(schedule, i, None, count=5) for i in range(5)]
        assert values == sorted(values)
        assert values[0] == 0.0
        assert all(0.0 <= v < 100.0 for v in values)


class TestSubmitExecuteAt:
    @staticmethod
    def _task():
        from backend.db_periodic_task.dispatch.base import DispatchTask
        from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        class _Task(DispatchTask):
            task_key = "test.ready_at"
            namespace = "test"

            def execute(self, item, *, job=None, overrides=None):
                return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS)

            def build_job(self, item, *, overrides=None, ready_at=None, config=None):
                return DispatchQueue.new_job(
                    task_key=self.task_key,
                    work_item_id=str(item),
                    work_item_data={"value": item},
                    ready_at=ready_at,
                )

        return _Task()

    def _capture_jobs(self, task, items, **submit_kwargs):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus, QueueAdmission
        from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        captured = []

        def _fake_enqueue_jobs(**kwargs):
            captured.extend(kwargs["jobs"])
            return [EnqueueStatus.ACCEPTED] * len(kwargs["jobs"])

        with patch.object(
            DispatchQueue, "load_config", return_value=DispatchQueueConfig(max_admitted_jobs=1000)
        ), patch.object(QueueAdmission, "enqueue_jobs", side_effect=_fake_enqueue_jobs):
            task.submit(items, **submit_kwargs)
        return captured

    def test_scalar_ready_at_applied_to_all(self):
        task = self._task()
        jobs = self._capture_jobs(task, [1, 2, 3], ready_at=555.0)
        assert [j.ready_at for j in jobs] == [555.0, 555.0, 555.0]

    def test_callable_ready_at_uses_global_index_across_chunks(self):
        task = self._task()
        # 26 items -> two admission chunks (25 + 1); index must stay global.
        jobs = self._capture_jobs(task, list(range(26)), ready_at=lambda index, item: float(index))
        assert [j.ready_at for j in jobs] == [float(i) for i in range(26)]

    def test_spread_binds_total_count_across_chunks(self):
        task = self._task()
        jobs = self._capture_jobs(task, list(range(26)), ready_at=spread(260.0, base=0.0))
        assert [j.ready_at for j in jobs] == [float(i * 10) for i in range(26)]

    def test_spread_delay_is_added_before_queue_wait_ttl(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus, QueueAdmission
        from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        script = MagicMock(return_value=[EnqueueStatus.ACCEPTED] * 3)
        with patch.object(
            DispatchQueue, "load_config", return_value=DispatchQueueConfig(max_admitted_jobs=1000)
        ), patch.object(QueueAdmission, "_enqueue_script", script), patch(
            "backend.db_periodic_task.dispatch.admission.time.time",
            return_value=100.0,
        ):
            self._task().submit([1, 2, 3], ready_at=spread(30.0, base=100.0))

        args = script.call_args.kwargs["args"]
        snapshots = [json.loads(args[offset + 2]) for offset in (7, 11, 15)]
        assert [snapshot["ready_at"] for snapshot in snapshots] == [100.0, 110.0, 120.0]
        assert [snapshot["wait_deadline_at"] for snapshot in snapshots] == [86500.0, 86510.0, 86520.0]
        assert [args[offset + 3] for offset in (7, 11, 15)] == [86400, 86410, 86420]

    def test_callable_is_fully_resolved_before_enqueue(self):
        from backend.db_periodic_task.dispatch.admission import QueueAdmission

        def schedule(index, _item):
            if index == 25:
                raise RuntimeError("bad item")
            return float(index)

        task = self._task()
        with patch.object(QueueAdmission, "enqueue_jobs") as enqueue_jobs, pytest.raises(
            RuntimeError, match="bad item"
        ):
            task.submit(list(range(26)), ready_at=schedule)
        enqueue_jobs.assert_not_called()

    @pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_timestamp_is_rejected_before_enqueue(self, timestamp):
        from backend.db_periodic_task.dispatch.admission import QueueAdmission

        task = self._task()
        with patch.object(QueueAdmission, "enqueue_jobs") as enqueue_jobs, pytest.raises(
            ValueError, match="finite timestamps"
        ):
            task.submit([1], ready_at=timestamp)
        enqueue_jobs.assert_not_called()

    def test_default_ready_at_is_now(self):
        import time as _time

        task = self._task()
        with patch("backend.db_periodic_task.dispatch.queue.time.time", return_value=42.0):
            jobs = self._capture_jobs(task, [1])
        assert jobs[0].ready_at == 42.0
        assert isinstance(_time.time(), float)

    def test_idempotence_mode_override_controls_dedupe_flag(self):
        from backend.db_periodic_task.dispatch.admission import EnqueueStatus, QueueAdmission
        from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
        from backend.db_periodic_task.dispatch.queue import DispatchQueue

        task = self._task()
        dedupe_flags = []

        def _fake_enqueue_jobs(**kwargs):
            dedupe_flags.append(kwargs["dedupe_enqueue"])
            return [EnqueueStatus.ACCEPTED] * len(kwargs["jobs"])

        with patch.object(
            DispatchQueue, "load_config", return_value=DispatchQueueConfig(max_admitted_jobs=1000)
        ), patch.object(QueueAdmission, "enqueue_jobs", side_effect=_fake_enqueue_jobs):
            task.submit([1], config={"idempotence_mode": "none"})
            task.submit([2])

        assert dedupe_flags == [False, True]
