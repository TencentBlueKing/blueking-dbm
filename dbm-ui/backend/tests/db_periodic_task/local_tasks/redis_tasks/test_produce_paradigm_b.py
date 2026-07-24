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
# Unit tests for the paradigm-B redis agent-check producer (priority daily + rotation top-up).
import importlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="module")
def task_mod(django_db_setup, django_db_blocker):
    # local_tasks import registers periodic tasks / touches DB; load under the blocker.
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.task")


class _Cfg:
    enabled = True
    priority_execute_lead_seconds = 300
    produce_low_watermark = 200
    produce_target_pending = 500
    produce_spread_window_seconds = 0


def _make_fake_task_cls(
    mod,
    *,
    pending_count,
    submit_recorder,
    enabled=True,
    queue_pending=0,
    queue_reserved=0,
    max_admitted_jobs=2000,
    submit_outcomes=None,
):
    def _outcome(outcome_type):
        outcome = MagicMock()
        outcome.outcome = outcome_type
        return outcome

    class _FakeQueue:
        @classmethod
        def load_config(cls):
            return SimpleNamespace(max_admitted_jobs=max_admitted_jobs)

        @classmethod
        def pending_count(cls):
            return queue_pending

        @classmethod
        def reserved_count(cls):
            return queue_reserved

    class _FakeTask:
        task_key = "test.paradigm_b"
        subtype = None
        queue_cls = _FakeQueue

        def __init__(self):
            self.config = _Cfg()
            self.config.enabled = enabled

        @property
        def pending_count(self):
            return pending_count

        def submit(self, items, *, ready_at=None):
            items = list(items)
            submit_recorder.append((items, ready_at))
            call_index = len(submit_recorder) - 1
            outcome_types = (
                submit_outcomes[call_index]
                if submit_outcomes is not None
                else [mod.DispatchOutcomeType.ENQUEUED] * len(items)
            )
            return [_outcome(outcome_type) for outcome_type in outcome_types]

    return _FakeTask


def test_both_lanes_when_priority_due_and_below_watermark(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=0, submit_recorder=submits)

    selector = MagicMock()
    selector.select_priority.return_value = [{"cluster_id": 1, "cluster_domain": "a.db"}]
    selector.select_rotation.return_value = (
        [{"cluster_id": 2, "cluster_domain": "b.db"}, {"cluster_id": 3, "cluster_domain": "c.db"}],
        42,
    )
    redis = MagicMock()
    redis.set.return_value = True  # priority pass claim succeeds
    redis.get.return_value = 0  # rotation cursor starts at 0

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        enqueued = mod._produce_redis_agent_check(fake_cls)

    assert enqueued == 3
    assert len(submits) == 2

    # Lane 1 (priority) runs first and jumps the queue with an early ready_at.
    prio_items, prio_ready_at = submits[0]
    assert [i["cluster_id"] for i in prio_items] == [1]
    assert isinstance(prio_ready_at, float)

    # Lane 2 (rotation) submits the top-up batch; no spread window -> ready_at None.
    rot_items, rot_ready_at = submits[1]
    assert [i["cluster_id"] for i in rot_items] == [2, 3]
    assert rot_ready_at is None

    # rotation budget = target - pending = 500 - 0
    selector.select_priority.assert_called_once_with(limit=mod._PRIORITY_MANIFEST_MAX)
    selector.select_rotation.assert_called_once_with(cursor=0, limit=500)
    # Atomic claim (SET NX) + cursor advanced
    redis.set.assert_any_call(
        mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b"),
        "1",
        nx=True,
        ex=mod._PRIORITY_PASS_TTL_SECONDS,
    )
    redis.set.assert_any_call(mod._ROTATION_CURSOR_KEY.format(task_key="test.paradigm_b"), 42)
    # The 1-item manifest was fully consumed in this beat: manifest + priority
    # cursor are cleared, but the daily pass stays claimed.
    redis.delete.assert_any_call(mod._PRIORITY_MANIFEST_KEY.format(task_key="test.paradigm_b"))
    redis.delete.assert_any_call(mod._PRIORITY_CURSOR_KEY.format(task_key="test.paradigm_b"))
    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == priority_key for call in redis.delete.call_args_list)


def test_no_lanes_when_priority_done_and_above_watermark(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=500, submit_recorder=submits)  # >= low_watermark

    selector = MagicMock()
    redis = MagicMock()
    redis.set.return_value = False  # priority pass already claimed today

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        enqueued = mod._produce_redis_agent_check(fake_cls)

    assert enqueued == 0
    assert submits == []
    selector.select_priority.assert_not_called()
    selector.select_rotation.assert_not_called()


def test_disabled_task_produces_nothing(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=0, submit_recorder=submits, enabled=False)

    selector = MagicMock()
    redis = MagicMock()
    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 0
    assert submits == []
    redis.set.assert_not_called()


def test_shared_queue_saturation_skips_both_selectors(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=0,
        submit_recorder=submits,
        queue_pending=1900,
        queue_reserved=100,
    )
    selector = MagicMock()

    with patch.object(mod, "RedisClusterSelector", return_value=selector):
        assert mod._produce_redis_agent_check(fake_cls) == 0

    selector.select_priority.assert_not_called()
    selector.select_rotation.assert_not_called()
    assert submits == []


def test_priority_failure_does_not_mark_daily_pass(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=500, submit_recorder=submits)
    selector = MagicMock()
    selector.select_priority.side_effect = RuntimeError("monitor unavailable")
    redis = MagicMock()
    redis.set.return_value = True  # claim succeeds, then released on failure

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 0

    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")
    redis.delete.assert_called_with(priority_key)


def test_rotation_cursor_is_retained_on_capacity_rejection(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=0,
        submit_recorder=submits,
        submit_outcomes=[[mod.DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED]],
    )
    selector = MagicMock()
    selector.select_rotation.return_value = ([{"cluster_id": 2, "cluster_domain": "b.db"}], 42)
    redis = MagicMock()
    redis.set.return_value = False  # priority already claimed
    redis.get.return_value = 0

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 0

    cursor_key = mod._ROTATION_CURSOR_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == cursor_key for call in redis.set.call_args_list)


def test_rotation_cursor_is_retained_on_producer_rejection(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=0,
        submit_recorder=submits,
        submit_outcomes=[[mod.DispatchOutcomeType.ENQUEUE_PRODUCER_PAUSED]],
    )
    selector = MagicMock()
    selector.select_rotation.return_value = ([{"cluster_id": 2, "cluster_domain": "b.db"}], 42)
    redis = MagicMock()
    redis.set.return_value = False  # priority already claimed
    redis.get.return_value = 0

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 0

    cursor_key = mod._ROTATION_CURSOR_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == cursor_key for call in redis.set.call_args_list)


def test_priority_filter_failure_holds_pass_and_skips_rotation(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=0, submit_recorder=submits)
    selector = MagicMock()
    selector.select_priority.return_value = [{"cluster_id": 1, "cluster_domain": "a.db"}]
    redis = MagicMock()
    redis.set.return_value = True  # claim succeeds, then released on filter failure

    def _boom(items):
        raise RuntimeError("dbconfig 500")

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls, filter_candidates=_boom) == 0

    assert submits == []
    selector.select_rotation.assert_not_called()
    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")
    redis.delete.assert_called_with(priority_key)


def test_rotation_filter_failure_holds_cursor(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(mod, pending_count=0, submit_recorder=submits)
    selector = MagicMock()
    selector.select_rotation.return_value = ([{"cluster_id": 2, "cluster_domain": "b.db"}], 42)
    redis = MagicMock()
    redis.set.return_value = False  # priority pass already claimed today
    redis.get.return_value = 0

    def _boom(items):
        raise RuntimeError("dbconfig 500")

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls, filter_candidates=_boom) == 0

    assert submits == []
    cursor_key = mod._ROTATION_CURSOR_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == cursor_key for call in redis.set.call_args_list)


def test_priority_limit_uses_remaining_shared_capacity(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=0,
        submit_recorder=submits,
        queue_pending=8,
        queue_reserved=1,
        max_admitted_jobs=10,
    )
    selector = MagicMock()
    selector.select_priority.return_value = [{"cluster_id": 1, "cluster_domain": "a.db"}]
    redis = MagicMock()
    redis.set.return_value = True
    redis.get.return_value = None  # no stored manifest/cursors yet

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 1

    selector.select_priority.assert_called_once_with(limit=mod._PRIORITY_MANIFEST_MAX)
    selector.select_rotation.assert_not_called()


def test_priority_manifest_consumed_across_beats(task_mod):
    mod = task_mod
    submits = []
    # available = 6 - 3 - 1 = 2; the 3-item manifest spans two beats.
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=500,  # at/above watermark: rotation lane skipped
        submit_recorder=submits,
        queue_pending=3,
        queue_reserved=1,
        max_admitted_jobs=6,
    )
    selector = MagicMock()
    manifest = [
        {"cluster_id": 1, "cluster_domain": "a.db"},
        {"cluster_id": 2, "cluster_domain": "b.db"},
        {"cluster_id": 3, "cluster_domain": "c.db"},
    ]
    selector.select_priority.return_value = manifest
    manifest_key = mod._PRIORITY_MANIFEST_KEY.format(task_key="test.paradigm_b")
    cursor_key = mod._PRIORITY_CURSOR_KEY.format(task_key="test.paradigm_b")
    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")

    redis = MagicMock()
    redis.set.return_value = True  # pass claim succeeds

    # Beat 1: no stored manifest -> select full list, persist, consume first 2.
    redis.get.return_value = None
    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        enqueued = mod._produce_redis_agent_check(fake_cls)
    assert enqueued == 2
    assert len(submits) == 1
    assert [i["cluster_id"] for i in submits[0][0]] == [1, 2]
    selector.select_priority.assert_called_once_with(limit=mod._PRIORITY_MANIFEST_MAX)
    redis.set.assert_any_call(
        manifest_key,
        json.dumps(manifest, ensure_ascii=False),
        ex=mod._PRIORITY_PASS_TTL_SECONDS,
    )
    redis.set.assert_any_call(cursor_key, 2, ex=mod._PRIORITY_PASS_TTL_SECONDS)
    redis.delete.assert_not_called()

    # Beat 2: manifest + cursor present -> consume the tail, then clear both.
    redis.reset_mock()
    redis.set.return_value = True
    redis.get.side_effect = lambda key: {
        manifest_key: json.dumps(manifest, ensure_ascii=False).encode(),
        cursor_key: b"2",
    }.get(key)
    selector.reset_mock()
    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        enqueued = mod._produce_redis_agent_check(fake_cls)
    assert enqueued == 1
    assert len(submits) == 2
    assert [i["cluster_id"] for i in submits[1][0]] == [3]
    # No re-query of the alarm API: the stored manifest is reused.
    selector.select_priority.assert_not_called()
    # Manifest fully consumed: cleared, daily pass kept.
    redis.delete.assert_any_call(manifest_key)
    redis.delete.assert_any_call(cursor_key)
    assert not any(call.args and call.args[0] == priority_key for call in redis.delete.call_args_list)


def test_priority_manifest_cursor_held_on_capacity_rejection(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=500,
        submit_recorder=submits,
        queue_pending=3,
        queue_reserved=1,
        max_admitted_jobs=6,
        submit_outcomes=[[mod.DispatchOutcomeType.ENQUEUE_CAPACITY_REJECTED, mod.DispatchOutcomeType.ENQUEUED]],
    )
    selector = MagicMock()
    selector.select_priority.return_value = [
        {"cluster_id": 1, "cluster_domain": "a.db"},
        {"cluster_id": 2, "cluster_domain": "b.db"},
    ]
    redis = MagicMock()
    redis.set.return_value = True
    redis.get.return_value = None  # build the manifest this beat

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 1

    # Retryable enqueue failure: the cursor must not advance past the initial 0,
    # the manifest must stay, and the pass must stay claimed so the next beat
    # retries the same window.
    cursor_key = mod._PRIORITY_CURSOR_KEY.format(task_key="test.paradigm_b")
    manifest_key = mod._PRIORITY_MANIFEST_KEY.format(task_key="test.paradigm_b")
    cursor_writes = [call for call in redis.set.call_args_list if call.args and call.args[0] == cursor_key]
    assert len(cursor_writes) == 1
    assert cursor_writes[0].args[1] == 0  # only the initial cursor reset, never advanced
    assert not any(call.args and call.args[0] == manifest_key for call in redis.delete.call_args_list)
    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == priority_key for call in redis.delete.call_args_list)


def test_priority_manifest_cursor_held_on_producer_rejection(task_mod):
    mod = task_mod
    submits = []
    fake_cls = _make_fake_task_cls(
        mod,
        pending_count=500,
        submit_recorder=submits,
        queue_pending=0,
        queue_reserved=0,
        max_admitted_jobs=6,
        submit_outcomes=[
            [
                mod.DispatchOutcomeType.ENQUEUE_PRODUCER_PAUSED,
                mod.DispatchOutcomeType.ENQUEUE_PRODUCER_PAUSED,
            ]
        ],
    )
    selector = MagicMock()
    selector.select_priority.return_value = [
        {"cluster_id": 1, "cluster_domain": "a.db"},
        {"cluster_id": 2, "cluster_domain": "b.db"},
    ]
    redis = MagicMock()
    redis.set.return_value = True
    redis.get.return_value = None  # build the manifest this beat

    with patch.object(mod, "RedisClusterSelector", return_value=selector), patch.object(mod, "RedisConn", redis):
        assert mod._produce_redis_agent_check(fake_cls) == 0

    # Producer gate closed: nothing enqueued, cursor/manifest/pass must hold so
    # the same alarm window is retried after resume (not silently dropped today).
    cursor_key = mod._PRIORITY_CURSOR_KEY.format(task_key="test.paradigm_b")
    manifest_key = mod._PRIORITY_MANIFEST_KEY.format(task_key="test.paradigm_b")
    cursor_writes = [call for call in redis.set.call_args_list if call.args and call.args[0] == cursor_key]
    assert len(cursor_writes) == 1
    assert cursor_writes[0].args[1] == 0
    assert not any(call.args and call.args[0] == manifest_key for call in redis.delete.call_args_list)
    priority_key = mod._PRIORITY_PASS_KEY.format(task_key="test.paradigm_b")
    assert not any(call.args and call.args[0] == priority_key for call in redis.delete.call_args_list)
