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
import time
from typing import Optional

from django.db import transaction

from backend.db_periodic_task.dispatch import routing
from backend.db_periodic_task.dispatch.producer import pause_queue_producer
from backend.db_periodic_task.dispatch.pump import pause_queue_pump

"""Drop-mode namespace remap between Redis shards.

``sweep_namespace`` reclaims one namespace's keys with a ``scan_iter`` glob
(``dispatch:{ns}:*``) and batched ``UNLINK``; ``dispatch:registered`` has no
namespace segment so it can never match.

``remap_namespace`` flips one route row and then waits two full
memo-plus-route-cache windows. The first wait covers stale-route convergence
even if cache invalidation fails; the second is a defensive verification pass
that warns on late keys (direct evidence of late writes or a broken
convergence assumption). The pump is paused on the old shard and the producer
gate closed there too, so producers resolving the stale route during
convergence get ``enqueue_producer_paused`` instead of enqueueing into a
namespace whose keys the sweeps will drop.
"""

logger = logging.getLogger("root")

SWEEP_BATCH_SIZE = 500


def _convergence_window_seconds() -> int:
    """Stale-route ceiling after a route row update."""
    return routing.ROUTE_MEMO_TTL_SECONDS + routing.ROUTE_CACHE_TTL_SECONDS


def sweep_namespace(alias: str, namespace: str, *, dry_run: bool = True) -> dict:
    """Scan and batched-UNLINK one namespace's keys on ``alias``.

    Returns ``{alias, namespace, matched, deleted, batches, dry_run}``.
    In dry-run mode only keys are counted; nothing is deleted.
    """
    routing.validate_namespace(namespace)
    client = routing.conn_for_alias(alias)
    pattern = f"dispatch:{namespace}:*"
    matched = 0
    deleted = 0
    batches = 0
    batch: list[str] = []
    for key in client.scan_iter(match=pattern, count=SWEEP_BATCH_SIZE):
        matched += 1
        if dry_run:
            continue
        batch.append(key)
        if len(batch) >= SWEEP_BATCH_SIZE:
            client.unlink(*batch)
            deleted += len(batch)
            batches += 1
            batch = []
    if not dry_run and batch:
        client.unlink(*batch)
        deleted += len(batch)
        batches += 1
    return {
        "alias": alias,
        "namespace": namespace,
        "matched": matched,
        "deleted": deleted,
        "batches": batches,
        "dry_run": dry_run,
    }


def _wait_convergence_window() -> None:
    time.sleep(_convergence_window_seconds())


def remap_namespace(
    namespace: str,
    alias: str,
    *,
    mode: str = "drop",
    dry_run: bool = True,
    pause_seconds: Optional[float] = None,
) -> dict:
    """Move one namespace to ``alias`` with drop-mode convergence sweeps.

    ``mode`` is a seam for a future ``"transfer"``; only ``"drop"`` is
    implemented today. ``dry_run=True`` validates and previews the plan without
    pausing, mutating the route row, or sweeping.

    Success needs no resume: the pause key lives on the old shard and is
    removed by the first sweep, while pumps check the lock on the new shard.
    Callers that abort before the route flip should ``resume_queue_pump``
    against the old alias themselves.
    """
    routing.validate_namespace(namespace)
    if mode != "drop":
        raise ValueError(f"mode={mode!r} is not supported (only 'drop')")
    aliases = routing.dispatch_aliases()
    if not aliases:
        raise routing.DispatchRoutingError("no dispatch Redis aliases configured")
    if alias not in aliases:
        raise ValueError(f"target alias {alias!r} is not in DISPATCH_REDIS_ALIASES: {', '.join(aliases)}")

    from backend.db_periodic_task.models import DispatchQueueRoute

    # TODO(kevn): Serialize remaps per namespace before this read.
    # Concurrent drop-mode remaps may briefly route writes through an
    # intermediate target that neither invocation subsequently sweeps.
    route = DispatchQueueRoute.objects.filter(namespace=namespace).first()
    if route is None:
        raise routing.DispatchRoutingError(f"no route row for namespace {namespace!r}")
    old_alias = route.redis_alias
    result = {
        "namespace": namespace,
        "from_alias": old_alias,
        "to_alias": alias,
        "mode": mode,
        "dry_run": dry_run,
        "moved": old_alias != alias,
        "convergence_window_seconds": _convergence_window_seconds(),
    }
    if old_alias == alias:
        result.update({"first_sweep": None, "second_sweep": None})
        return result
    if dry_run:
        result.update(
            {
                "first_sweep": sweep_namespace(old_alias, namespace, dry_run=True),
                "second_sweep": None,
            }
        )
        return result

    # Pin the pause to the OLD shard: after the route row flips,
    # pause_queue_pump would resolve to the new shard and miss its target.
    # TODO(kevn): Either require an indefinite pause here or reject
    # pause_seconds shorter than the convergence window; otherwise stale
    # resolvers can resume writes to the old shard before the first sweep.
    pause_queue_pump(namespace, seconds=pause_seconds, alias=old_alias)
    # Close the producer gate on the OLD shard too; the first sweep removes it
    # after convergence, so the gate opens automatically on the new shard.
    pause_queue_producer(namespace, seconds=pause_seconds, alias=old_alias)
    # TODO(kevn): If either pause or route.save() fails before the
    # route flip commits, restore both old-shard gates (or return explicit
    # operator recovery instructions) instead of leaving an indefinite pause.
    with transaction.atomic():
        route.redis_alias = alias
        route.updater = "system"
        # instance.save() (never QuerySet.update()) keeps full_clean() and the
        # on-commit route-cache invalidation from the model.
        route.save()

    _wait_convergence_window()
    first_sweep = sweep_namespace(old_alias, namespace, dry_run=False)
    _wait_convergence_window()
    second_sweep = sweep_namespace(old_alias, namespace, dry_run=False)
    late_keys = second_sweep.get("matched", 0)
    if late_keys:
        logger.error(
            "dispatch remap: late keys after second convergence window "
            "namespace=%s from_alias=%s to_alias=%s matched=%d deleted=%d",
            namespace,
            old_alias,
            alias,
            second_sweep.get("matched", 0),
            second_sweep.get("deleted", 0),
        )
    else:
        logger.info(
            "dispatch remap: remap complete namespace=%s from_alias=%s to_alias=%s "
            "first_deleted=%d second_deleted=%d",
            namespace,
            old_alias,
            alias,
            first_sweep.get("deleted", 0),
            second_sweep.get("deleted", 0),
        )
    result.update({"first_sweep": first_sweep, "second_sweep": second_sweep})
    return result
