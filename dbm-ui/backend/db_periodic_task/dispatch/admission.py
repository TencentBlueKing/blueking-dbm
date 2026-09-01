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

from backend.db_periodic_task.dispatch.config import DISPATCH_LUA_BATCH_SIZE
from backend.db_periodic_task.dispatch.job import DispatchJob, compute_wait_deadline
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.metrics import DispatchMetrics
from backend.db_periodic_task.dispatch.queue import TASK_COUNTS_TTL_SECONDS

logger = logging.getLogger("root")

ENQUEUE_JOBS_LUA = """
local pending = KEYS[1]
local reserved = KEYS[2]
local task_outcomes = KEYS[3]
local queue_events = KEYS[4]
local task_counts = KEYS[5]
local producer_gate = KEYS[6]
local metrics_started_at = KEYS[7]
local max_admitted = tonumber(ARGV[1])
local check_dedupe = tonumber(ARGV[2])
local task_key = ARGV[3]
local task_metrics_ttl = tonumber(ARGV[4])
local metrics_started_timestamp = ARGV[5]
local task_counts_ttl = tonumber(ARGV[6])
local job_count = tonumber(ARGV[7])

local admitted = redis.call('ZCARD', pending) + redis.call('ZCARD', reserved)
local accepted_count = 0
local metric_counts = {}
local statuses = {}
-- Producer gate: one EXISTS per admission batch, atomic with the writes below.
local producer_paused = (redis.call('EXISTS', producer_gate) == 1)

local function finish(index, status, metric_name)
    statuses[index] = status
    metric_counts[metric_name] = (metric_counts[metric_name] or 0) + 1
    return status
end

for index = 1, job_count do
    local key_offset = 7 + ((index - 1) * 2)
    local arg_offset = 7 + ((index - 1) * 4)
    local job_record = KEYS[key_offset + 1]
    local dedupe_key = KEYS[key_offset + 2]
    local job_id = ARGV[arg_offset + 1]
    local score = tonumber(ARGV[arg_offset + 2])
    local job_snapshot = ARGV[arg_offset + 3]
    -- Remaining pending-wait TTL for this job's payload / dedupe key.
    local pending_record_ttl = tonumber(ARGV[arg_offset + 4])
    local decided = false

    -- Closed producer gate rejects everything before dedupe / capacity: a
    -- paused producer must never consume queue slots or dedupe identities.
    if producer_paused then
        finish(index, 5, 'enqueue_producer_paused')
        decided = true
    end

    if not decided and check_dedupe == 1 then
        if redis.call('ZSCORE', pending, job_id) ~= false then
            finish(index, 2, 'enqueue_duplicate')
            decided = true
        elseif redis.call('ZSCORE', reserved, job_id) ~= false then
            finish(index, 2, 'enqueue_duplicate')
            decided = true
        elseif dedupe_key ~= '' and redis.call('EXISTS', dedupe_key) == 1 then
            finish(index, 2, 'enqueue_duplicate')
            decided = true
        end
    end

    if not decided and admitted >= max_admitted then
        finish(index, 3, 'enqueue_capacity_rejected')
        decided = true
    end

    if not decided and check_dedupe == 1 and dedupe_key ~= '' then
        local ok = redis.call('SET', dedupe_key, job_id, 'NX', 'EX', pending_record_ttl)
        if not ok then
            finish(index, 2, 'enqueue_duplicate')
            decided = true
        end
    end

    if not decided then
        redis.call('SET', job_record, job_snapshot, 'EX', pending_record_ttl)
        redis.call('ZADD', pending, score, job_id)
        admitted = admitted + 1
        accepted_count = accepted_count + 1
        finish(index, 1, 'enqueued')
    end
end

if task_key ~= '' and accepted_count > 0 then
    local pending_value = tonumber(redis.call('HINCRBY', task_counts, 'pending:' .. task_key, accepted_count))
    if pending_value <= 0 then
        redis.call('HDEL', task_counts, 'pending:' .. task_key)
    end
    redis.call('EXPIRE', task_counts, task_counts_ttl)
end

local has_metrics = false
for metric_name, amount in pairs(metric_counts) do
    has_metrics = true
    -- Metrics remain fail-open: telemetry corruption must not reject admission.
    redis.pcall('HINCRBY', task_outcomes, metric_name, amount)
    redis.pcall('HINCRBY', queue_events, metric_name, amount)
end
if has_metrics then
    redis.pcall('EXPIRE', task_outcomes, task_metrics_ttl)
    redis.pcall('SET', metrics_started_at, metrics_started_timestamp, 'NX')
end
return statuses
"""


class EnqueueStatus(IntEnum):
    """Per-job admission outcome. No member is 0, so ``if status:`` never
    silently reads one rejection differently from the others."""

    ACCEPTED = 1
    DUPLICATE = 2
    CAPACITY_REJECTED = 3
    DEADLINE_EXPIRED = 4
    PRODUCER_PAUSED = 5
    UNAVAILABLE = 6


class QueueAdmission:
    """Atomically admit jobs under admitted capacity and optional dedupe."""

    _enqueue_script = compile_script(ENQUEUE_JOBS_LUA)

    @classmethod
    def enqueue_jobs(
        cls,
        *,
        queue_cls,
        jobs: list[DispatchJob],
        dedupe_enqueue: bool,
        queue_wait_ttls: list[int],
        max_admitted_jobs: int,
    ) -> list[EnqueueStatus]:
        if not jobs:
            return []
        if len(jobs) != len(queue_wait_ttls):
            raise ValueError("jobs and queue_wait_ttls must have the same length")
        if len(jobs) > DISPATCH_LUA_BATCH_SIZE:
            raise ValueError(f"admission batch cannot exceed {DISPATCH_LUA_BATCH_SIZE} jobs")
        task_keys = {job.task_key for job in jobs}
        if len(task_keys) != 1:
            raise ValueError("all jobs in an admission batch must share one task_key")

        statuses: list[EnqueueStatus | None] = [None] * len(jobs)
        prepared: list[tuple[int, DispatchJob, int]] = []
        now = time.time()
        for index, (job, queue_wait_ttl) in enumerate(zip(jobs, queue_wait_ttls)):
            deadline, pending_record_ttl = compute_wait_deadline(
                now, job.ready_at, queue_wait_ttl, job.wait_deadline_at
            )
            if pending_record_ttl is None:
                # Existing deadline already expired: nothing left of the wait
                # budget. Distinct from CAPACITY_REJECTED so producers holding
                # cursors on admission failure do not misread an expired job
                # (which must never be retried) as a full queue.
                statuses[index] = EnqueueStatus.DEADLINE_EXPIRED
                continue
            job.wait_deadline_at = deadline
            prepared.append((index, job, pending_record_ttl))

        if prepared:
            task_key = jobs[0].task_key
            (
                task_outcomes,
                queue_events,
                metrics_started_at,
                task_metrics_ttl,
                metrics_started_timestamp,
            ) = DispatchMetrics.enqueue_counter_spec(
                queue_cls.namespace,
                task_key,
            )
            keys = [
                queue_cls.pending_key(),
                queue_cls.reserved_key(),
                task_outcomes,
                queue_events,
                queue_cls.task_counts_key(),
                queue_cls.producer_gate_key(),
                metrics_started_at,
            ]
            args = [
                max(1, int(max_admitted_jobs)),
                1 if dedupe_enqueue else 0,
                task_key or "",
                task_metrics_ttl,
                metrics_started_timestamp,
                TASK_COUNTS_TTL_SECONDS,
                len(prepared),
            ]
            for _index, job, pending_record_ttl in prepared:
                dedupe_key = (
                    queue_cls.dedupe_key(job.task_key, job.work_item_id)
                    if dedupe_enqueue and job.task_key and job.work_item_id
                    else ""
                )
                keys.extend([queue_cls.job_key(job.job_id), dedupe_key])
                args.extend(
                    [
                        job.job_id,
                        float(job.ready_at),
                        json.dumps(job.to_dict(), ensure_ascii=False),
                        pending_record_ttl,
                    ]
                )
            try:
                results = eval_script(cls._enqueue_script, client=queue_cls.conn(), keys=keys, args=args)
                if len(prepared) == 1 and not isinstance(results, (list, tuple)):
                    results = [results]
                for (index, _job, _ttl), result in zip(prepared, results):
                    statuses[index] = EnqueueStatus(int(result))
            except Exception:
                for index, _job, _ttl in prepared:
                    statuses[index] = EnqueueStatus.UNAVAILABLE

        resolved = [EnqueueStatus.UNAVAILABLE if status is None else status for status in statuses]
        unavailable = sum(status == EnqueueStatus.UNAVAILABLE for status in resolved)
        if unavailable:
            logger.warning(
                "dispatch: batch enqueue unavailable namespace=%s unavailable=%d total=%d",
                queue_cls.namespace,
                unavailable,
                len(jobs),
            )
        return resolved
