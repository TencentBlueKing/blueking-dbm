# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Producer-side admission control for the dispatch queue layer.

``pause_queue_pump`` stops the pump from dispatching already-admitted work; it
does not stop producers from enqueuing more. ``pause_queue_producer`` closes a
separate per-namespace gate that the admission Lua checks atomically: while the
gate key exists, ``submit`` returns ``enqueue_producer_paused`` and nothing is
written to the queue. The pump keeps draining, so already-admitted work still
runs to completion.

Both controls are independent: pause either, neither, or both.
"""

import logging
import math
from typing import Optional

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.lua import RELEASE_LOCK_LUA, compile_script, eval_script
from backend.db_periodic_task.dispatch.metrics import decode_text
from backend.db_periodic_task.dispatch.queue import KEY_PRODUCER_GATE_PREFIX

logger = logging.getLogger("root")

PRODUCER_PAUSE_OWNER = "dispatch:producer_paused"

_release_lock_script = compile_script(RELEASE_LOCK_LUA)


def producer_gate_key(namespace: str) -> str:
    """The producer gate key for one namespace (``dispatch:{ns}:producer_gate``)."""
    return KEY_PRODUCER_GATE_PREFIX.format(ns=namespace or "")


def pause_queue_producer(namespace: str, *, seconds: Optional[float] = None, alias: Optional[str] = None) -> dict:
    """Close the per-namespace producer gate so ``submit`` returns ``enqueue_producer_paused``.

    ``seconds=None`` keeps the gate closed until ``resume_queue_producer`` (no
    Redis TTL). Otherwise it auto-expires after ``ceil(seconds)`` (≥1).
    ``alias`` pins the Redis shard explicitly (used by remap so the gate lands
    on the old shard even while the route row is about to flip).
    """
    ns = namespace or ""
    if not ns:
        raise ValueError("namespace is required to pause a queue producer")
    key = producer_gate_key(ns)
    client = routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)
    if seconds is None:
        client.set(key, PRODUCER_PAUSE_OWNER)
        logger.warning("dispatch: producer gate[%s]: paused until resume", ns)
        return {"namespace": ns, "paused": True, "ttl_seconds": None}
    if float(seconds) <= 0:
        raise ValueError("seconds must be positive; use seconds=None to pause until resume")
    ttl = max(1, int(math.ceil(float(seconds))))
    client.set(key, PRODUCER_PAUSE_OWNER, ex=ttl)
    logger.warning("dispatch: producer gate[%s]: paused for %ss", ns, ttl)
    return {"namespace": ns, "paused": True, "ttl_seconds": ttl}


def resume_queue_producer(namespace: str, *, alias: Optional[str] = None) -> bool:
    """Open the per-namespace producer gate. Returns whether a gate key was removed."""
    ns = namespace or ""
    if not ns:
        raise ValueError("namespace is required to resume a queue producer")
    client = routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)
    removed = bool(
        eval_script(
            _release_lock_script,
            client=client,
            keys=[producer_gate_key(ns)],
            args=[PRODUCER_PAUSE_OWNER],
        )
    )
    if removed:
        logger.warning("dispatch: producer gate[%s]: resumed", ns)
    return removed


def inspect_queue_producer_gate(namespace: str, *, alias: Optional[str] = None) -> dict:
    """Inspect who holds ``dispatch:{ns}:producer_gate``.

    Returns::

        {
            "namespace": "...",
            "key": "dispatch:{ns}:producer_gate",
            "held": bool,
            "owner": str | None,          # raw Redis value
            "state": "free" | "paused",
            "ttl_seconds": int | None,    # -1 = no expiry; None = missing
        }
    """
    ns = namespace or ""
    key = producer_gate_key(ns)
    empty = {
        "namespace": ns,
        "key": key,
        "held": False,
        "owner": None,
        "state": "free",
        "ttl_seconds": None,
    }
    if not ns:
        return empty
    try:
        raw = (routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)).get(key)
    except Exception:
        return empty
    if raw is None:
        return empty
    owner = decode_text(raw)
    try:
        ttl = int((routing.conn_for_alias(alias) if alias else routing.conn_for_namespace(ns)).ttl(key))
    except Exception:
        ttl = None
    else:
        # redis: -2 = key missing (race)
        if ttl == -2:
            return empty
    # ``pause_queue_producer`` is the only writer of this key, so any present
    # value means the gate is closed.
    return {
        "namespace": ns,
        "key": key,
        "held": True,
        "owner": owner,
        "state": "paused",
        "ttl_seconds": ttl,
    }


def is_queue_producer_paused(namespace: str, *, alias: Optional[str] = None) -> bool:
    """Whether the namespace producer gate is currently closed by a pause marker."""
    return inspect_queue_producer_gate(namespace, alias=alias)["state"] == "paused"


def queue_producer_pause_ttl(namespace: str, *, alias: Optional[str] = None) -> Optional[int]:
    """Remaining producer-gate pause TTL in seconds.

    ``None`` when not paused. ``-1`` when paused with no expiry (until resume).
    """
    info = inspect_queue_producer_gate(namespace, alias=alias)
    if info["state"] != "paused":
        return None
    return info["ttl_seconds"]
