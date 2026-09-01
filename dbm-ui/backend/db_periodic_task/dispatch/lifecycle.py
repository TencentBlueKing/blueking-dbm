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
from enum import IntEnum

from backend.db_periodic_task.dispatch.job import DispatchJob, compute_wait_deadline
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.queue import TASK_COUNTS_TTL_SECONDS

logger = logging.getLogger("root")

FINALIZE_JOB_LUA = """
local removed = redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('DEL', KEYS[1])
if KEYS[3] ~= '' then
    redis.call('DEL', KEYS[3])
end
if removed > 0 and ARGV[2] ~= '' then
    local value = tonumber(redis.call('HINCRBY', KEYS[4], ARGV[2], -1))
    if value <= 0 then
        redis.call('HDEL', KEYS[4], ARGV[2])
    end
    redis.call('EXPIRE', KEYS[4], ARGV[3])
end
return removed
"""

REQUEUE_JOB_LUA = """
local removed = redis.call('ZREM', KEYS[2], ARGV[1])
if removed == 0 then
    -- The job was already finalized or reaped while the worker was executing
    -- (e.g. execution outlived the reserved TTL). Never revive a zombie: no
    -- payload write, no pending ZADD, no counter move.
    return 0
end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
redis.call('ZADD', KEYS[3], ARGV[4], ARGV[1])
if removed > 0 and ARGV[5] ~= '' then
    local reserved_value = tonumber(redis.call('HINCRBY', KEYS[4], ARGV[5], -1))
    if reserved_value <= 0 then
        redis.call('HDEL', KEYS[4], ARGV[5])
    end
    local pending_value = tonumber(redis.call('HINCRBY', KEYS[4], ARGV[6], 1))
    if pending_value <= 0 then
        redis.call('HDEL', KEYS[4], ARGV[6])
    end
    -- ARGV[7] is the TTL of the rebuildable per-task count hash, not the job.
    redis.call('EXPIRE', KEYS[4], ARGV[7])
end
return removed
"""

_finalize_script = compile_script(FINALIZE_JOB_LUA)
_requeue_script = compile_script(REQUEUE_JOB_LUA)


class RequeueResult(IntEnum):
    """Why ``QueueLifecycle.requeue`` did or did not put the job back.

    Only ``REQUEUED`` means the job is pending again and its caller must not
    finalize it. The two failures differ in who owns the job afterwards:
    ``WAIT_BUDGET_SPENT`` means requeue itself discarded it as orphaned, while
    ``SLOT_LOST`` means someone else already finalized or reaped it.
    """

    REQUEUED = 1
    WAIT_BUDGET_SPENT = 2
    SLOT_LOST = 3


class QueueLifecycle:
    """Terminal transitions (finalize / requeue) of one job on one queue.

    All operations bind to a queue class (``queue_cls``) and run as Lua scripts
    so job payload, zset membership, dedupe key, and the derived per-task count
    hash stay consistent under concurrency.
    """

    @classmethod
    def finalize_job(
        cls,
        *,
        queue_cls,
        job_id: str,
        task_key: str = "",
        work_item_id: str = "",
        task_counts_ttl: int = TASK_COUNTS_TTL_SECONDS,
    ) -> int:
        """Atomically delete the job record, its reserved slot, and its dedupe key."""
        try:
            dedupe_key = queue_cls.dedupe_key(task_key, work_item_id) if task_key and work_item_id else ""
            return int(
                eval_script(
                    _finalize_script,
                    client=queue_cls.conn(),
                    keys=[
                        queue_cls.job_key(job_id),
                        queue_cls.reserved_key(),
                        dedupe_key,
                        queue_cls.task_counts_key(),
                    ],
                    args=[
                        job_id,
                        queue_cls.reserved_count_field(task_key) if task_key else "",
                        max(1, int(task_counts_ttl)),
                    ],
                )
                or 0
            )
        except Exception as exc:
            logger.warning("dispatch: finalize_job failed job_id=%s: %s", job_id, exc)
            return 0

    @classmethod
    def _eval_requeue(
        cls,
        *,
        queue_cls,
        job_id: str,
        job_snapshot: str,
        queue_wait_ttl: int,
        score: float,
        task_key: str = "",
        task_counts_ttl: int = TASK_COUNTS_TTL_SECONDS,
    ) -> int:
        """Requeue a job and refresh the rebuildable task-count hash TTL."""
        return int(
            eval_script(
                _requeue_script,
                client=queue_cls.conn(),
                keys=[
                    queue_cls.job_key(job_id),
                    queue_cls.reserved_key(),
                    queue_cls.pending_key(),
                    queue_cls.task_counts_key(),
                ],
                args=[
                    job_id,
                    job_snapshot,
                    max(1, int(queue_wait_ttl)),
                    float(score),
                    queue_cls.reserved_count_field(task_key) if task_key else "",
                    queue_cls.pending_count_field(task_key) if task_key else "",
                    max(1, int(task_counts_ttl)),
                ],
            )
            or 0
        )

    @classmethod
    def requeue(cls, *, queue_cls, job: DispatchJob, ready_at: float, queue_wait_ttl: int) -> RequeueResult:
        """Requeue without extending an existing first-readiness deadline.

        When the job's wait deadline has already expired, the job is discarded
        as orphaned instead.
        """
        try:
            now = time.time()
            deadline, wait_ttl = compute_wait_deadline(now, ready_at, queue_wait_ttl, job.wait_deadline_at)
            if wait_ttl is None:
                # Reservation clears the deadline (reserved is bounded by the
                # execution timeout instead); only an *existing* expired
                # deadline lands here and discards the job.
                from backend.db_periodic_task.dispatch.reaper import OrphanReaper

                OrphanReaper.discard_orphaned_job(
                    queue_cls,
                    job.job_id,
                    task_key=job.task_key,
                    namespace=job.namespace,
                )
                return RequeueResult.WAIT_BUDGET_SPENT
            job.ready_at = ready_at
            job.wait_deadline_at = deadline
            requeued = cls._eval_requeue(
                queue_cls=queue_cls,
                job_id=job.job_id,
                job_snapshot=json.dumps(job.to_dict(), ensure_ascii=False),
                queue_wait_ttl=wait_ttl,
                score=ready_at,
                task_key=job.task_key,
            )
            if not requeued:
                # The job was already removed from reserved (finalized / reaped)
                # while the worker was executing; the caller must not treat this
                # as a successful requeue so its finalize path still runs.
                return RequeueResult.SLOT_LOST
            return RequeueResult.REQUEUED
        except Exception as exc:
            logger.warning("dispatch: requeue failed job_id=%s: %s", job.job_id, exc)
            return RequeueResult.SLOT_LOST
