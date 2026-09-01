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
from dataclasses import replace
from enum import IntEnum

from backend.db_periodic_task.dispatch.config import (
    DISPATCH_LUA_BATCH_SIZE,
    PUMP_INTERVAL_SECONDS,
    DispatchQueueConfig,
)
from backend.db_periodic_task.dispatch.job import DispatchJob
from backend.db_periodic_task.dispatch.lua import compile_script, eval_script
from backend.db_periodic_task.dispatch.queue import TASK_COUNTS_TTL_SECONDS, DispatchQueue

logger = logging.getLogger("root")

TICK_COUNTER_TTL_SECONDS = PUMP_INTERVAL_SECONDS * 6

RESERVE_JOB_LUA = """
local pending = KEYS[1]
local reserved = KEYS[2]
local tick_counter = KEYS[3]
local task_counts = KEYS[4]
local now = tonumber(ARGV[1])
local max_reserved = tonumber(ARGV[2])
local tick_budget = tonumber(ARGV[3])
local counter_ttl = tonumber(ARGV[4])
local job_count = tonumber(ARGV[5])
local task_counts_ttl = tonumber(ARGV[6])

-- Slots currently held by reserved jobs, and how many this call newly promoted.
local reserved_count = tonumber(redis.call('ZCARD', reserved))
local used = tonumber(redis.call('GET', tick_counter) or '0')
local newly_reserved = 0
local statuses = {}

for index = 1, job_count do
    local key_offset = 4 + ((index - 1) * 2)
    local arg_offset = 6 + ((index - 1) * 4)
    local job_record = KEYS[key_offset + 1]
    local dedupe_key = KEYS[key_offset + 2]
    local job_id = ARGV[arg_offset + 1]
    local job_snapshot = ARGV[arg_offset + 2]
    -- Execution timeout + margin: how long this reservation may hold a slot.
    local reserved_record_ttl = tonumber(ARGV[arg_offset + 3])
    local task_key = ARGV[arg_offset + 4]

    if redis.call('ZSCORE', pending, job_id) == false then
        statuses[index] = 2
    elseif reserved_count >= max_reserved then
        statuses[index] = 3
    elseif used >= tick_budget then
        statuses[index] = 4
    else
        redis.call('ZREM', pending, job_id)
        redis.call('ZADD', reserved, now, job_id)
        redis.call('SET', job_record, job_snapshot, 'EX', reserved_record_ttl)
        if dedupe_key ~= '' then
            redis.call('EXPIRE', dedupe_key, reserved_record_ttl)
        end
        if task_key ~= '' then
            local pending_field = 'pending:' .. task_key
            local pending_value = tonumber(redis.call('HINCRBY', task_counts, pending_field, -1))
            if pending_value <= 0 then
                redis.call('HDEL', task_counts, pending_field)
            end
            local reserved_field = 'reserved:' .. task_key
            local reserved_value = tonumber(redis.call('HINCRBY', task_counts, reserved_field, 1))
            if reserved_value <= 0 then
                redis.call('HDEL', task_counts, reserved_field)
            end
            redis.call('EXPIRE', task_counts, task_counts_ttl)
        end
        reserved_count = reserved_count + 1
        used = used + 1
        newly_reserved = newly_reserved + 1
        statuses[index] = 1
    end
end

if newly_reserved > 0 then
    redis.call('SET', tick_counter, used, 'EX', counter_ttl)
end
return statuses
"""


class ReservationStatus(IntEnum):
    """Per-job reservation outcome. No member is 0, so ``if status:`` cannot
    read one rejection differently from the others.

    ``CAPACITY_FULL`` and ``TICK_BUDGET_EXHAUSTED`` are healthy backpressure and
    the job stays pending for a later tick. ``UNAVAILABLE`` means the EVAL never
    ran, so nothing is known about the job and the queue may be broken.
    """

    RESERVED = 1
    MISSING = 2
    CAPACITY_FULL = 3
    TICK_BUDGET_EXHAUSTED = 4
    UNAVAILABLE = 5


#: Reservation refused for lack of room, not for lack of a working Redis.
BACKPRESSURE_STATUSES = frozenset(
    {ReservationStatus.CAPACITY_FULL, ReservationStatus.TICK_BUDGET_EXHAUSTED},
)


class QueueReservation:
    """Atomically reserve earliest-ready jobs under queue reserved and tick ceilings."""

    _reserve_script = compile_script(RESERVE_JOB_LUA)

    @classmethod
    def reserve_jobs(
        cls,
        jobs: list[DispatchJob],
        config: DispatchQueueConfig,
        *,
        queue_cls: type[DispatchQueue],
        reserved_record_ttls: list[int],
        tick_id: int,
        tick_budget: int,
    ) -> list[ReservationStatus]:
        if not jobs:
            return []
        if len(jobs) != len(reserved_record_ttls):
            raise ValueError("jobs and reserved_record_ttls must have the same length")
        if len(jobs) > DISPATCH_LUA_BATCH_SIZE:
            raise ValueError(f"reservation chunk cannot exceed {DISPATCH_LUA_BATCH_SIZE} jobs")

        keys = [
            queue_cls.pending_key(),
            queue_cls.reserved_key(),
            queue_cls.tick_counter_key(tick_id),
            queue_cls.task_counts_key(),
        ]
        args = [
            time.time(),
            max(1, int(config.max_reserved)),
            max(1, int(tick_budget)),
            TICK_COUNTER_TTL_SECONDS,
            len(jobs),
            TASK_COUNTS_TTL_SECONDS,
        ]
        for job, reserved_record_ttl in zip(jobs, reserved_record_ttls):
            reserved_job = replace(job, wait_deadline_at=0.0)
            keys.extend(
                [
                    queue_cls.job_key(job.job_id),
                    queue_cls.dedupe_key(job.task_key, job.work_item_id) if job.task_key and job.work_item_id else "",
                ]
            )
            args.extend(
                [
                    job.job_id,
                    json.dumps(reserved_job.to_dict(), ensure_ascii=False),
                    max(1, int(reserved_record_ttl)),
                    job.task_key or "",
                ]
            )
        try:
            results = eval_script(cls._reserve_script, client=queue_cls.conn(), keys=keys, args=args)
        except Exception as exc:
            logger.warning(
                "dispatch: reserve_jobs failed namespace=%s count=%d: %s",
                queue_cls.namespace,
                len(jobs),
                exc,
            )
            return [ReservationStatus.UNAVAILABLE] * len(jobs)
        return [ReservationStatus(int(result)) for result in results]
