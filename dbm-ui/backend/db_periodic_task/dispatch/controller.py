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

import logging
import math
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.metrics import AIMD_TICK_COUNTER_NAMES, DispatchMetrics, tick_id
from backend.db_periodic_task.dispatch.queue import DispatchQueue

logger = logging.getLogger("root")

MULTIPLICATIVE_DECREASE_FACTOR = 0.5
CONTROLLER_STATE_TTL_SECONDS = 10 * 60
KEY_CONTROLLER_PREFIX = "dispatch:{ns}:controller"


class AimdAction(str, Enum):
    """What AIMD did to the congestion window this tick."""

    INCREASE = "increase"
    DECREASE = "decrease"
    HOLD = "hold"
    COLD_START = "cold_start"

    def __str__(self) -> str:
        return self.value


def _decode_mapping(raw: dict) -> dict[str, str]:
    return {
        key.decode()
        if isinstance(key, bytes)
        else str(key): (value.decode() if isinstance(value, bytes) else str(value))
        for key, value in raw.items()
    }


def _additive_increase_step(max_reserved: int) -> int:
    """AIMD additive-increase step: 5% of configured queue concurrency."""
    return max(1, int(max_reserved) // 20)


def _cold_start_window(max_reserved: int) -> int:
    """Initial congestion window: 10% of configured queue concurrency."""
    return max(1, int(max_reserved) // 10)


@dataclass
class PumpControlDecision:
    namespace: str
    tick_id: int
    effective_budget: int
    congestion_window: int
    available_slots: int
    previous_published: int = 0
    previous_ready_peeked: int = 0
    previous_congestion: int = 0
    aimd_action: AimdAction = AimdAction.HOLD
    # ``reserved_count()`` was unreadable (or ``decide`` raised), so the slot
    # arithmetic below ran on an assumed-zero reservation count.
    reserved_count_unknown: bool = False


class PumpController:
    """Select a bounded queue budget from free slots and a congestion-window AIMD."""

    @staticmethod
    def _state_key(namespace: str) -> str:
        return KEY_CONTROLLER_PREFIX.format(ns=namespace)

    @classmethod
    def decide(
        cls,
        queue_cls: type[DispatchQueue],
        config: DispatchQueueConfig,
        *,
        current_tick_id: Optional[int] = None,
        state: Optional[dict[str, Any]] = None,
    ) -> PumpControlDecision:
        """Pick this tick's budget for ``queue_cls``.

        ``state`` lets a caller that already read the controller hash hand it in
        rather than paying a second ``HGETALL`` of the same key in the same tick.
        """
        current_tick_id = tick_id() if current_tick_id is None else int(current_tick_id)
        namespace = queue_cls.namespace
        reserved = queue_cls.reserved_count()
        reserved_count_unknown = reserved < 0
        if reserved_count_unknown:
            reserved = 0
        max_reserved = int(config.max_reserved)
        available_slots = max(0, max_reserved - reserved)
        if available_slots <= 0:
            decision = PumpControlDecision(
                namespace=namespace,
                tick_id=current_tick_id,
                effective_budget=0,
                congestion_window=0,
                available_slots=available_slots,
                aimd_action=AimdAction.HOLD,
                reserved_count_unknown=reserved_count_unknown,
            )
            cls._persist(decision)
            return decision

        increase_step = _additive_increase_step(max_reserved)
        cold_window = _cold_start_window(max_reserved)
        try:
            if state is None:
                state = _decode_mapping(routing.conn_for_namespace(namespace).hgetall(cls._state_key(namespace)) or {})
            previous = DispatchMetrics.queue_tick_counts(
                namespace,
                current_tick_id - 1,
                names=AIMD_TICK_COUNTER_NAMES,
            )
            last_tick_id = int(state.get("tick_id", -1))
            stale = last_tick_id < current_tick_id - 2
            previous_published = int(previous.get("published", 0))
            previous_ready_peeked = int(previous.get("ready_peeked", 0))
            previous_congestion = int(previous.get("congestion", 0))
            if not state or stale:
                congestion_window = cold_window
                decision = PumpControlDecision(
                    namespace=namespace,
                    tick_id=current_tick_id,
                    effective_budget=min(available_slots, congestion_window),
                    congestion_window=congestion_window,
                    available_slots=available_slots,
                    previous_published=previous_published,
                    previous_ready_peeked=previous_ready_peeked,
                    previous_congestion=previous_congestion,
                    aimd_action=AimdAction.COLD_START,
                    reserved_count_unknown=reserved_count_unknown,
                )
            else:
                decision = cls._warm_decision(
                    namespace,
                    current_tick_id,
                    available_slots,
                    max_reserved,
                    increase_step,
                    cold_window,
                    state,
                    previous,
                    reserved_count_unknown,
                )
        except Exception as exc:
            logger.warning("dispatch controller[%s]: fallback to AIMD cold start: %s", namespace, exc)
            congestion_window = cold_window
            decision = PumpControlDecision(
                namespace=namespace,
                tick_id=current_tick_id,
                effective_budget=min(available_slots, congestion_window),
                congestion_window=congestion_window,
                available_slots=available_slots,
                aimd_action=AimdAction.COLD_START,
                reserved_count_unknown=True,
            )
        cls._persist(decision)
        return decision

    @classmethod
    def _warm_decision(
        cls,
        namespace: str,
        current_tick_id: int,
        available_slots: int,
        max_reserved: int,
        increase_step: int,
        cold_window: int,
        state: dict[str, str],
        previous: dict[str, int],
        reserved_count_unknown: bool,
    ) -> PumpControlDecision:
        previous_congestion_window = int(state.get("congestion_window", 0) or 0)
        previous_effective_budget = int(state.get("effective_budget", 0) or 0)
        previous_published = int(previous.get("published", 0))
        previous_ready_peeked = int(previous.get("ready_peeked", 0))
        previous_congestion = int(previous.get("congestion", 0))

        congestion_window = previous_congestion_window if previous_congestion_window > 0 else cold_window
        if previous_congestion > 0:
            congestion_window = max(1, math.floor(congestion_window * MULTIPLICATIVE_DECREASE_FACTOR))
            aimd_action = AimdAction.DECREASE
        elif (
            previous_effective_budget > 0
            # Grow only when cwnd itself was the binding constraint and the whole
            # window was published with demand to spare. When available_slots
            # binds instead, cwnd holds — possibly long-term at the cold-start
            # value. That conservatism is deliberate: we accept a slower ramp
            # after sustained pressure rather than over-admit into a downstream
            # that is still draining.
            and previous_effective_budget == previous_congestion_window
            and previous_published >= previous_effective_budget
            and previous_ready_peeked >= previous_effective_budget
        ):
            congestion_window = min(max_reserved, congestion_window + increase_step)
            aimd_action = AimdAction.INCREASE
        else:
            aimd_action = AimdAction.HOLD

        return PumpControlDecision(
            namespace=namespace,
            tick_id=current_tick_id,
            effective_budget=min(available_slots, congestion_window),
            congestion_window=congestion_window,
            available_slots=available_slots,
            previous_published=previous_published,
            previous_ready_peeked=previous_ready_peeked,
            previous_congestion=previous_congestion,
            aimd_action=aimd_action,
            reserved_count_unknown=reserved_count_unknown,
        )

    @classmethod
    def _persist(cls, decision: PumpControlDecision) -> None:
        try:
            mapping = {
                name: int(value) if isinstance(value, bool) else str(value) if isinstance(value, Enum) else value
                for name, value in asdict(decision).items()
            }
            mapping["updated_at"] = time.time()
            pipe = routing.conn_for_namespace(decision.namespace).pipeline(transaction=False)
            pipe.hset(cls._state_key(decision.namespace), mapping=mapping)
            pipe.expire(cls._state_key(decision.namespace), CONTROLLER_STATE_TTL_SECONDS)
            pipe.execute()
        except Exception as exc:
            logger.debug("dispatch controller[%s]: state write failed: %s", decision.namespace, exc)

    @classmethod
    def read_state(cls, namespace: str) -> dict[str, Any]:
        try:
            state: dict[str, Any] = _decode_mapping(
                routing.conn_for_namespace(namespace).hgetall(cls._state_key(namespace)) or {}
            )
            for name in (
                "tick_id",
                "effective_budget",
                "congestion_window",
                "available_slots",
                "previous_published",
                "previous_ready_peeked",
                "previous_congestion",
            ):
                if name in state:
                    state[name] = int(state[name])
            if "updated_at" in state:
                state["updated_at"] = float(state["updated_at"])
            if "reserved_count_unknown" in state:
                state["reserved_count_unknown"] = bool(int(state["reserved_count_unknown"]))
            return state
        except Exception:
            return {}
