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
# Smoke tests that execute the dispatch Lua scripts against the real Redis
# configured for the test environment (same convention as other suites that
# use ``django.core.cache`` / ``RedisConn`` unpatched).
#
# The mock-based unit tests assert call shapes; these verify actual script
# behavior: enqueue capacity/dedupe, reserve/finalize/requeue membership and
# counter moves, atomic purge decrements (A1), and namespace-scoped dedupe
# cleanup on orphan discard (A2).
#
# Multi-shard coverage uses the same Redis process with isolated logical DBs
# (CI: broker=/0, default+dispatch=/1, so this suite claims /11 and /12) to
# exercise real ``get_redis_connection`` alias routing and drop-mode remap.
# ``test_routing.py`` / ``test_remap.py`` stay mock-based for control flow.
#
# All keys live under smoke-specific namespaces and are deleted before and
# after each test; nothing touches production-looking dispatch keys.
import copy
import json
import time
from unittest.mock import patch
from urllib.parse import urlsplit, urlunsplit

import pytest
from django.conf import settings
from django.test import override_settings
from django_redis import get_redis_connection

from backend.db_periodic_task.dispatch import lifecycle
from backend.db_periodic_task.dispatch.admission import EnqueueStatus, QueueAdmission
from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.job import DispatchJob, build_job_id
from backend.db_periodic_task.dispatch.queue import DISPATCH_QUEUE_REGISTRY, TASK_COUNTS_TTL_SECONDS, DispatchQueue
from backend.db_periodic_task.dispatch.reaper import OrphanReaper
from backend.db_periodic_task.dispatch.reservation import QueueReservation, ReservationStatus

TASK_KEY = "smoke.task"
NAMESPACE = "smoke"
NAMESPACE_TWO = "smoke2"
# Dedicated namespace for the multi-DB remap smoke so it never collides with
# the single-shard ``live_redis`` keys even if a cleanup path fails.
NAMESPACE_SHARD = "smokeshard"

# Key patterns this suite may create; cleaned before/after every test. The
# normalized layout puts every namespace key under ``dispatch:{ns}:*``.
_KEY_PATTERNS = [
    f"dispatch:{NAMESPACE}:*",
    f"dispatch:{NAMESPACE_TWO}:*",
    f"dispatch:{NAMESPACE_SHARD}:*",
]

# Logical DBs reserved for multi-shard smoke (CI redis image defaults to 0-15).
_SHARD_DB_0 = 11
_SHARD_DB_1 = 12
_SHARD_ALIASES = ["dispatch_0", "dispatch_1"]


def _redis_url_with_db(url: str, db: int) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{db}", parts.query, parts.fragment))


def _redis_cache(location: str) -> dict:
    """Mirror ``config.default._redis_cache`` so CACHES aliases stay consistent."""
    return {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": location,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "REDIS_CLIENT_CLASS": "redis.client.StrictRedis",
            "REDIS_CLIENT_KWARGS": {"decode_responses": True},
            "SERIALIZER": "backend.utils.redis.JSONSerializer",
            "MAX_ENTRIES": 100000,
            "CULL_FREQUENCY": 10,
        },
    }


def _delete_test_keys() -> None:
    from backend.db_periodic_task.dispatch import routing

    client = routing.conn_for_namespace(NAMESPACE)
    for pattern in _KEY_PATTERNS:
        keys = list(client.scan_iter(match=pattern, count=500))
        if keys:
            client.delete(*keys)


def _ns_key_count(client, namespace: str) -> int:
    return sum(1 for _ in client.scan_iter(match=f"dispatch:{namespace}:*", count=500))


def _make_queue_class(namespace: str) -> type[DispatchQueue]:
    config_cls = type(f"SmokeQueueConfig:{namespace}", (DispatchQueueConfig,), {"namespace": namespace})
    return type(f"SmokeQueue:{namespace}", (DispatchQueue,), {"config_cls": config_cls})


def _job(work_item_id: str, *, namespace: str = NAMESPACE, ready_at=None) -> DispatchJob:
    return DispatchJob(
        job_id=build_job_id(TASK_KEY, work_item_id),
        task_key=TASK_KEY,
        namespace=namespace,
        work_item_id=work_item_id,
        created_at=time.time(),
        ready_at=ready_at or time.time(),
    )


def _enqueue(queue_cls, jobs, *, max_admitted_jobs=10):
    return QueueAdmission.enqueue_jobs(
        queue_cls=queue_cls,
        jobs=jobs,
        dedupe_enqueue=True,
        queue_wait_ttls=[300] * len(jobs),
        max_admitted_jobs=max_admitted_jobs,
    )


def _reserve(queue_cls, jobs, *, max_reserved=2, tick_budget=10):
    return QueueReservation.reserve_jobs(
        jobs,
        DispatchQueueConfig(max_reserved=max_reserved),
        queue_cls=queue_cls,
        reserved_record_ttls=[300] * len(jobs),
        tick_id=100,
        tick_budget=tick_budget,
    )


@pytest.fixture
def live_redis(django_db_blocker):
    """Real Redis with smoke-namespace cleanup and queue-registry isolation."""
    from backend.db_periodic_task.dispatch import routing

    saved_registry = dict(DISPATCH_QUEUE_REGISTRY)
    DISPATCH_QUEUE_REGISTRY.clear()
    with django_db_blocker.unblock():
        routing.reset_route_cache()
        _delete_test_keys()
        # Pre-assign route rows so every Redis op resolves without a DB hit.
        for ns in (NAMESPACE, NAMESPACE_TWO):
            routing.assign_route(ns)
        with patch.object(DispatchQueue, "ensure_queues_loaded"):
            yield routing.conn_for_namespace(NAMESPACE)
        _delete_test_keys()
        routing.reset_route_cache()
        from backend.db_periodic_task.models import DispatchQueueRoute

        DispatchQueueRoute.objects.filter(namespace__in=(NAMESPACE, NAMESPACE_TWO)).delete()
    DISPATCH_QUEUE_REGISTRY.clear()
    DISPATCH_QUEUE_REGISTRY.update(saved_registry)


@pytest.fixture
def multi_shard_redis(django_db_blocker):
    """Two dispatch aliases backed by Redis logical DBs 11/12 on the CI host.

    Exercises real ``get_redis_connection`` fan-out without needing a second
    Redis container. Convergence sleeps are patched out by individual tests.
    """
    from backend.db_periodic_task.dispatch import routing
    from backend.db_periodic_task.models import DispatchQueueRoute

    base_url = settings.CACHES["default"]["LOCATION"]
    caches = copy.deepcopy(settings.CACHES)
    caches["dispatch_0"] = _redis_cache(_redis_url_with_db(base_url, _SHARD_DB_0))
    caches["dispatch_1"] = _redis_cache(_redis_url_with_db(base_url, _SHARD_DB_1))

    saved_registry = dict(DISPATCH_QUEUE_REGISTRY)
    DISPATCH_QUEUE_REGISTRY.clear()
    with override_settings(CACHES=caches, DISPATCH_REDIS_ALIASES=list(_SHARD_ALIASES)):
        # Drop any cached django-redis clients so LOCATION overrides take effect.
        from django.core.cache import caches as django_caches

        django_caches.close_all()

        shard0 = get_redis_connection("dispatch_0")
        shard1 = get_redis_connection("dispatch_1")
        shard0.flushdb()
        shard1.flushdb()

        with django_db_blocker.unblock():
            routing.reset_route_cache()
            DispatchQueueRoute.objects.filter(namespace=NAMESPACE_SHARD).delete()
            DispatchQueueRoute.objects.create(
                namespace=NAMESPACE_SHARD,
                redis_alias="dispatch_0",
                creator="tester",
                updater="tester",
            )
            routing.reset_route_cache()
            with patch.object(DispatchQueue, "ensure_queues_loaded"):
                yield {
                    "dispatch_0": shard0,
                    "dispatch_1": shard1,
                    "aliases": list(_SHARD_ALIASES),
                }
            shard0.flushdb()
            shard1.flushdb()
            routing.reset_route_cache()
            DispatchQueueRoute.objects.filter(namespace=NAMESPACE_SHARD).delete()

    DISPATCH_QUEUE_REGISTRY.clear()
    DISPATCH_QUEUE_REGISTRY.update(saved_registry)


class TestEnqueueLua:
    def test_same_work_item_second_enqueue_is_duplicate(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)

        assert _enqueue(queue_cls, [_job("item-1")]) == [EnqueueStatus.ACCEPTED]
        assert _enqueue(queue_cls, [_job("item-1")]) == [EnqueueStatus.DUPLICATE]

        assert live_redis.zcard(queue_cls.pending_key()) == 1
        assert live_redis.exists(queue_cls.dedupe_key(TASK_KEY, "item-1")) == 1
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "1"

    def test_capacity_rejects_beyond_max_admitted(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)

        statuses = _enqueue(queue_cls, [_job("a"), _job("b"), _job("c")], max_admitted_jobs=2)

        assert statuses == [EnqueueStatus.ACCEPTED, EnqueueStatus.ACCEPTED, EnqueueStatus.CAPACITY_REJECTED]
        assert live_redis.zcard(queue_cls.pending_key()) == 2
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "2"


class TestProducerGateLua:
    def test_closed_gate_rejects_all_without_writing_anything(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        # Close the producer gate before enqueuing.
        live_redis.set(queue_cls.producer_gate_key(), "dispatch:producer_paused")

        statuses = _enqueue(queue_cls, [_job("a"), _job("b")])

        assert statuses == [EnqueueStatus.PRODUCER_PAUSED, EnqueueStatus.PRODUCER_PAUSED]
        # Nothing written: no pending member, no task_counts counter, no dedupe.
        assert live_redis.zcard(queue_cls.pending_key()) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {}
        assert live_redis.exists(queue_cls.dedupe_key(TASK_KEY, "a")) == 0

    def test_closed_gate_beats_dedupe_and_capacity(self, live_redis):
        """A closed gate must win over dedupe/duplicate and capacity outcomes."""
        queue_cls = _make_queue_class(NAMESPACE)
        # Occupied slot + existing dedupe identity for the same work item.
        _enqueue(queue_cls, [_job("a")])
        live_redis.set(queue_cls.producer_gate_key(), "dispatch:producer_paused")

        # Same work_item_id again: gate closes before dedupe is even consulted.
        statuses = _enqueue(queue_cls, [_job("a")], max_admitted_jobs=0)

        assert statuses == [EnqueueStatus.PRODUCER_PAUSED]
        assert live_redis.zcard(queue_cls.pending_key()) == 1  # unchanged from the first enqueue
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "1"

    def test_open_gate_allows_enqueue(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)

        assert _enqueue(queue_cls, [_job("a")]) == [EnqueueStatus.ACCEPTED]
        assert live_redis.zcard(queue_cls.pending_key()) == 1


class TestReserveLua:
    def test_reserve_moves_pending_to_reserved_with_counts(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        jobs = [_job("a"), _job("b"), _job("c")]
        _enqueue(queue_cls, jobs)

        statuses = _reserve(queue_cls, jobs, max_reserved=2)

        assert statuses == [
            ReservationStatus.RESERVED,
            ReservationStatus.RESERVED,
            ReservationStatus.CAPACITY_FULL,
        ]
        assert live_redis.zcard(queue_cls.pending_key()) == 1
        assert live_redis.zcard(queue_cls.reserved_key()) == 2
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {
            f"pending:{TASK_KEY}": "1",
            f"reserved:{TASK_KEY}": "2",
        }

    def test_tick_budget_is_reported_apart_from_capacity(self, live_redis):
        """A spent tick budget and a full queue must not share one status code:
        the first clears on the next tick, the second needs more capacity."""
        queue_cls = _make_queue_class(NAMESPACE)
        jobs = [_job("a"), _job("b")]
        _enqueue(queue_cls, jobs)

        statuses = _reserve(queue_cls, jobs, max_reserved=100, tick_budget=1)

        assert statuses == [ReservationStatus.RESERVED, ReservationStatus.TICK_BUDGET_EXHAUSTED]
        assert live_redis.zcard(queue_cls.pending_key()) == 1

    def test_reserve_missing_job_is_noop(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)

        assert _reserve(queue_cls, [_job("ghost")]) == [ReservationStatus.MISSING]
        assert live_redis.zcard(queue_cls.reserved_key()) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {}


class TestFinalizeLua:
    def test_finalize_clears_reserved_payload_dedupe_and_count(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        job = _job("a")
        _enqueue(queue_cls, [job])
        _reserve(queue_cls, [job])

        removed = lifecycle.QueueLifecycle.finalize_job(
            queue_cls=queue_cls,
            job_id=job.job_id,
            task_key=TASK_KEY,
            work_item_id="a",
            task_counts_ttl=TASK_COUNTS_TTL_SECONDS,
        )

        assert removed == 1
        assert live_redis.zcard(queue_cls.reserved_key()) == 0
        assert live_redis.exists(queue_cls.job_key(job.job_id)) == 0
        assert live_redis.exists(queue_cls.dedupe_key(TASK_KEY, "a")) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {}


class TestRequeueLua:
    def test_requeue_moves_reserved_back_to_pending(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        job = _job("a")
        _enqueue(queue_cls, [job])
        _reserve(queue_cls, [job])

        removed = lifecycle.QueueLifecycle._eval_requeue(
            queue_cls=queue_cls,
            job_id=job.job_id,
            job_snapshot=json.dumps(job.to_dict(), ensure_ascii=False),
            queue_wait_ttl=300,
            score=time.time(),
            task_key=TASK_KEY,
            task_counts_ttl=TASK_COUNTS_TTL_SECONDS,
        )

        assert removed == 1
        assert live_redis.zcard(queue_cls.pending_key()) == 1
        assert live_redis.zcard(queue_cls.reserved_key()) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {f"pending:{TASK_KEY}": "1"}

    def test_requeue_after_finalize_does_not_revive(self, live_redis):
        """P2-9: requeue must never resurrect a job the reap/finalize already cleaned."""
        queue_cls = _make_queue_class(NAMESPACE)
        job = _job("a")
        _enqueue(queue_cls, [job])
        _reserve(queue_cls, [job])
        # The job is cleaned up while the worker is still executing (finalize or
        # orphan reap): reserved member, payload and dedupe are all gone.
        lifecycle.QueueLifecycle.finalize_job(
            queue_cls=queue_cls,
            job_id=job.job_id,
            task_key=TASK_KEY,
            work_item_id="a",
            task_counts_ttl=TASK_COUNTS_TTL_SECONDS,
        )

        removed = lifecycle.QueueLifecycle._eval_requeue(
            queue_cls=queue_cls,
            job_id=job.job_id,
            job_snapshot=json.dumps(job.to_dict(), ensure_ascii=False),
            queue_wait_ttl=300,
            score=time.time(),
            task_key=TASK_KEY,
            task_counts_ttl=TASK_COUNTS_TTL_SECONDS,
        )

        # No zombie: no payload write, no pending ZADD, no counter move.
        assert removed == 0
        assert live_redis.zcard(queue_cls.pending_key()) == 0
        assert live_redis.zcard(queue_cls.reserved_key()) == 0
        assert live_redis.exists(queue_cls.job_key(job.job_id)) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {}


class TestPurgeMemberLua:
    def test_repeated_purge_does_not_double_decrement(self, live_redis):
        """A1: reap must decrement only what it actually removed, atomically."""
        queue_cls = _make_queue_class(NAMESPACE)
        jobs = [_job("a"), _job("b")]
        _enqueue(queue_cls, jobs)

        assert OrphanReaper.purge_job(queue_cls, jobs[0].job_id, task_key=TASK_KEY) == (1, 0)
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "1"

        # A second reap of the same member (concurrent ZSCAN race) is a no-op.
        assert OrphanReaper.purge_job(queue_cls, jobs[0].job_id, task_key=TASK_KEY) == (0, 0)
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "1"

    def test_purge_reserved_member_after_reserve(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        job = _job("a")
        _enqueue(queue_cls, [job])
        _reserve(queue_cls, [job])

        assert OrphanReaper.purge_job(queue_cls, job.job_id, task_key=TASK_KEY) == (0, 1)
        assert live_redis.zcard(queue_cls.reserved_key()) == 0
        assert live_redis.hgetall(queue_cls.task_counts_key()) == {}

    def test_purge_without_task_key_touches_no_counters(self, live_redis):
        queue_cls = _make_queue_class(NAMESPACE)
        job = _job("a")
        _enqueue(queue_cls, [job])

        assert OrphanReaper.purge_job(queue_cls, job.job_id) == (1, 0)
        # Unknown task attribution: counters stay for the drift rebuild to own.
        assert live_redis.hget(queue_cls.task_counts_key(), f"pending:{TASK_KEY}") == "1"


class TestDiscardOrphanedJobScoping:
    def test_unknown_namespace_deletes_dedupe_only_where_member_lived(self, live_redis):
        """A2: orphan discard must not break another queue's live dedupe key."""
        queue_cls = _make_queue_class(NAMESPACE)
        other_queue_cls = _make_queue_class(NAMESPACE_TWO)
        job = _job("item-1")
        _enqueue(queue_cls, [job])
        # Another queue happens to use the same task_key + work_item_id pair.
        live_redis.set(other_queue_cls.dedupe_key(TASK_KEY, "item-1"), "other-job", ex=300)
        # Payload TTL expires -> the job becomes an orphan.
        live_redis.delete(queue_cls.job_key(job.job_id))

        # Invoke via the owning queue class so outcome metrics stay smoke-scoped.
        assert OrphanReaper.discard_orphaned_job(queue_cls, job.job_id, task_key=TASK_KEY, work_item_id="item-1")

        assert live_redis.zcard(queue_cls.pending_key()) == 0
        assert live_redis.exists(queue_cls.dedupe_key(TASK_KEY, "item-1")) == 0
        assert live_redis.get(other_queue_cls.dedupe_key(TASK_KEY, "item-1")) == "other-job"

    def test_unknown_namespace_without_member_keeps_dedupe_for_ttl(self, live_redis):
        """A2: when no queue claims the member, dedupe keys are left to TTL."""
        queue_cls = _make_queue_class(NAMESPACE)
        live_redis.set(queue_cls.dedupe_key(TASK_KEY, "item-1"), "live-job", ex=300)

        assert OrphanReaper.discard_orphaned_job(
            queue_cls,
            build_job_id(TASK_KEY, "item-1"),
            task_key=TASK_KEY,
            work_item_id="item-1",
        )

        assert live_redis.get(queue_cls.dedupe_key(TASK_KEY, "item-1")) == "live-job"


class TestMultiShardRemap:
    """Real multi-alias I/O via Redis logical DBs (not mock clients).

    ``transaction=True`` is required so ``DispatchQueueRoute.save``'s
    ``on_commit`` route-cache invalidation actually runs (plain ``django_db``
    wraps the test in a non-committing transaction).
    """

    @pytest.mark.django_db(transaction=True)
    def test_enqueue_lands_on_routed_shard_only(self, multi_shard_redis):
        from backend.db_periodic_task.dispatch import routing

        queue_cls = _make_queue_class(NAMESPACE_SHARD)
        shard0 = multi_shard_redis["dispatch_0"]
        shard1 = multi_shard_redis["dispatch_1"]

        assert routing.resolve_alias(NAMESPACE_SHARD) == "dispatch_0"
        assert _enqueue(queue_cls, [_job("a", namespace=NAMESPACE_SHARD)]) == [EnqueueStatus.ACCEPTED]

        assert shard0.zcard(queue_cls.pending_key()) == 1
        assert _ns_key_count(shard0, NAMESPACE_SHARD) >= 1
        assert _ns_key_count(shard1, NAMESPACE_SHARD) == 0

    @pytest.mark.django_db(transaction=True)
    def test_drop_remap_sweeps_old_shard_and_writes_land_on_new(self, multi_shard_redis):
        from backend.db_periodic_task.dispatch import remap, routing
        from backend.db_periodic_task.models import DispatchQueueRoute

        queue_cls = _make_queue_class(NAMESPACE_SHARD)
        shard0 = multi_shard_redis["dispatch_0"]
        shard1 = multi_shard_redis["dispatch_1"]

        assert _enqueue(queue_cls, [_job("before", namespace=NAMESPACE_SHARD)]) == [EnqueueStatus.ACCEPTED]
        assert shard0.zcard(queue_cls.pending_key()) == 1
        assert shard1.zcard(queue_cls.pending_key()) == 0

        # Skip the 2×90s convergence sleeps; Redis I/O and sweeps stay real.
        with patch.object(remap, "_wait_convergence_window"):
            result = remap.remap_namespace(NAMESPACE_SHARD, "dispatch_1", mode="drop", dry_run=False)

        assert result["moved"] is True
        assert result["from_alias"] == "dispatch_0"
        assert result["to_alias"] == "dispatch_1"
        assert result["first_sweep"]["deleted"] >= 1
        assert DispatchQueueRoute.objects.get(namespace=NAMESPACE_SHARD).redis_alias == "dispatch_1"
        assert routing.resolve_alias(NAMESPACE_SHARD) == "dispatch_1"

        # Old-shard namespace keys (including pause/producer gates) are gone.
        assert _ns_key_count(shard0, NAMESPACE_SHARD) == 0
        # Drop-mode does not transfer pending jobs; new writes go to the new shard.
        assert _enqueue(queue_cls, [_job("after", namespace=NAMESPACE_SHARD)]) == [EnqueueStatus.ACCEPTED]
        assert shard1.zcard(queue_cls.pending_key()) == 1
        assert shard0.zcard(queue_cls.pending_key()) == 0
        assert routing.conn_for_namespace(NAMESPACE_SHARD).connection_pool.connection_kwargs["db"] == _SHARD_DB_1
