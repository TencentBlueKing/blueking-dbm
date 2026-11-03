# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Single-lane DispatchQueue for background queries against the name service.

The name service rate-limits callers to 20 QPS. This queue runs at most one job
at a time across all workers, and every task on it MUST call
``NAMESERVICE_CALL_GATE.acquire()`` before each name service request. Together
that keeps this lane at or below ``NAMESERVICE_CALL_QPS`` whatever tasks share it.

Only bind tasks that spend the name service budget. Tasks calling another
downstream belong on their own queue; here they would serialize behind
name service work for nothing.
"""
import threading
import time
from dataclasses import dataclass
from typing import ClassVar

from django.core.exceptions import ValidationError

from backend.db_periodic_task.dispatch.config import DispatchQueueConfig
from backend.db_periodic_task.dispatch.queue import DispatchQueue

NAMESERVICE_NAMESPACE: str = "nameservice"
# Name service allows 20 QPS; keep headroom for ticket flows that call it outside this lane.
NAMESERVICE_CALL_QPS = 15
# The QPS gate is process-local, so it only bounds the whole lane while one job runs at a time.
NAMESERVICE_MAX_RESERVED = 1


class CallIntervalGate:
    """Process-wide gate that spaces consecutive calls at least 1/qps seconds apart."""

    def __init__(self, qps: int):
        self.min_interval = 1.0 / qps
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._next_allowed > now:
                time.sleep(self._next_allowed - now)
                now = self._next_allowed
            self._next_allowed = now + self.min_interval


NAMESERVICE_CALL_GATE = CallIntervalGate(NAMESERVICE_CALL_QPS)


@dataclass
class NameserviceQueueConfig(DispatchQueueConfig):
    """``max_reserved`` is pinned to one; only ``max_admitted_jobs`` is tunable."""

    namespace: ClassVar[str] = NAMESERVICE_NAMESPACE
    max_reserved: int = NAMESERVICE_MAX_RESERVED

    @classmethod
    def from_raw(cls, raw: dict):
        config = super().from_raw(raw)
        config.max_reserved = NAMESERVICE_MAX_RESERVED
        return config

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        super().validate_raw(raw)
        max_reserved = (raw or {}).get("max_reserved", NAMESERVICE_MAX_RESERVED)
        if max_reserved != NAMESERVICE_MAX_RESERVED:
            raise ValidationError(
                {"config": f"max_reserved is fixed to {NAMESERVICE_MAX_RESERVED} on the {NAMESERVICE_NAMESPACE} queue"}
            )


class NameserviceQueue(DispatchQueue):
    config_cls = NameserviceQueueConfig


__all__ = (
    "NAMESERVICE_NAMESPACE",
    "NAMESERVICE_CALL_QPS",
    "NAMESERVICE_CALL_GATE",
    "CallIntervalGate",
    "NameserviceQueueConfig",
    "NameserviceQueue",
)
