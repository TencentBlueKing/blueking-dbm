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

from __future__ import annotations

import logging
import re
import time
from collections import Counter

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django_redis import get_redis_connection
from redis import Redis

from backend.db_periodic_task.dispatch.job import resolve_task_key_from_job_id

"""Namespace -> Redis alias routing for the dispatch queue layer.

Every namespace-scoped dispatch key travels together on one Redis instance
(``dispatch:{ns}:*``); only ``dispatch:registered`` stays on the default
Redis. The mapping is persisted in ``DispatchQueueRoute`` (MySQL) so it
survives a Redis flush, and is assigned once per namespace (never rewritten
incrementally) so growing the pool never reshuffles live data.

Hot paths resolve through a short in-process memo layered on a Django-cache
copy of the whole route map, so a Redis op costs neither a DB nor a cache
round trip. Resolution fails closed: when the map cannot be loaded and the
memo has no prior value, ``DispatchRoutingError`` is raised instead of
guessing a shard.
"""

logger = logging.getLogger("root")

# Remap convergence bounds: a process can refresh its in-process memo from a
# stale whole-map cache just before that cache expires, so the stale-route
# ceiling is memo TTL + route-cache TTL after the route row update.
ROUTE_MEMO_TTL_SECONDS = 30
ROUTE_CACHE_TTL_SECONDS = 60

_ROUTE_CACHE_KEY = "dispatch:routes"

# ``dispatch:{ns}:*`` is used as a scan_iter glob, so rejecting ``:`` alone is
# not enough: glob metacharacters must also be banned, and the two non-namespace
# prefixes on default Redis are reserved to avoid confusion.
_NAMESPACE_PATTERN = re.compile(r"^[a-z0-9_-]+$")
_RESERVED_NAMESPACES = frozenset({"registered", "config"})

# In-process memo: namespace -> (alias, monotonic expiry). A stale entry keeps
# serving the last known alias when a refresh fails; it is only a guess-free
# fallback to a mapping this process already successfully used.
_memo: dict[str, tuple[str, float]] = {}


class DispatchRoutingError(Exception):
    """Raised when a namespace's Redis shard cannot be resolved safely."""


def validate_namespace(namespace: str) -> None:
    """Validate the namespace charset and reserved-name rules."""
    if not isinstance(namespace, str) or not _NAMESPACE_PATTERN.match(namespace):
        raise ValidationError({"namespace": f"must match [a-z0-9_-]+, got {namespace!r}"})
    if namespace in _RESERVED_NAMESPACES:
        raise ValidationError({"namespace": f"{namespace!r} is reserved"})


def dispatch_aliases() -> list[str]:
    """The configured dispatch Redis pool, in pool order."""
    return list(getattr(settings, "DISPATCH_REDIS_ALIASES", None) or [])


def _get_routes() -> dict[str, str]:
    """Load the whole namespace -> alias map (Django cache over MySQL)."""
    try:
        cached = cache.get(_ROUTE_CACHE_KEY)
        if isinstance(cached, dict):
            return dict(cached)
    except Exception as exc:
        logger.warning("dispatch routing: route cache.get failed: %s", exc)

    from backend.db_periodic_task.models import DispatchQueueRoute

    try:
        routes = dict(DispatchQueueRoute.objects.values_list("namespace", "redis_alias"))
    except Exception as exc:
        logger.error("dispatch routing: route map load failed: %s", exc)
        raise DispatchRoutingError("route map unavailable") from exc
    try:
        cache.set(_ROUTE_CACHE_KEY, routes, ROUTE_CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("dispatch routing: route cache.set failed: %s", exc)
    return routes


def invalidate_route(namespace: str) -> None:
    """Drop one namespace's memo entry and the whole-map cache."""
    _memo.pop(namespace, None)
    try:
        cache.delete(_ROUTE_CACHE_KEY)
    except Exception as exc:
        logger.warning("dispatch routing: route cache.delete failed: %s", exc)


def reset_route_cache() -> None:
    """Clear the in-process memo and the whole-map cache (tests / bootstrap)."""
    _memo.clear()
    try:
        cache.delete(_ROUTE_CACHE_KEY)
    except Exception as exc:
        logger.warning("dispatch routing: route cache.reset failed: %s", exc)


def assign_route(namespace: str) -> str:
    """Assign-once least-loaded routing for one namespace.

    Picks the alias currently owning the fewest namespaces (tie-break by pool
    order) and ``get_or_create``s the row. The unique constraint makes
    concurrent workers race-safe: the loser reads the winner's value. Existing
    rows are never rewritten, so growing the pool cannot reshuffle live data.
    """
    validate_namespace(namespace)
    aliases = dispatch_aliases()
    if not aliases:
        raise DispatchRoutingError("no dispatch Redis aliases configured")
    routes = _get_routes()
    # TODO(kevn): Serialize the least-loaded calculation with route
    # creation when concurrent callers assign different namespaces.
    # get_or_create() only resolves races for the same namespace, so a cold
    # start can temporarily concentrate several new namespaces on one alias.
    counts = Counter(route for ns, route in routes.items() if route in aliases)
    alias = min(aliases, key=lambda candidate: (counts.get(candidate, 0), aliases.index(candidate)))

    from backend.db_periodic_task.models import DispatchQueueRoute

    try:
        route, created = DispatchQueueRoute.objects.get_or_create(
            namespace=namespace,
            defaults={"redis_alias": alias, "creator": "system", "updater": "system"},
        )
    except Exception as exc:
        logger.error("dispatch routing: assign_route failed namespace=%s: %s", namespace, exc)
        raise DispatchRoutingError(f"cannot assign route for namespace {namespace!r}") from exc
    if created:
        # get_or_create commits immediately (autocommit): invalidate the memo
        # and the whole-map cache so callers see the new row right away.
        invalidate_route(namespace)
    return route.redis_alias


def resolve_alias(namespace: str) -> str:
    """Resolve the persisted alias for ``namespace``, lazily assigning on miss.

    Accepts any namespace string (not just registry members): the abstract
    base queue and ephemeral cleanup queues need a shard even when their
    owning module is gone.
    """
    ns = namespace or ""
    aliases = dispatch_aliases()
    try:
        routes = _get_routes()
        alias = routes.get(ns)
        if alias is not None:
            if alias in aliases:
                return alias
            raise DispatchRoutingError(f"namespace {ns!r} routes to dropped alias {alias!r}")
        return assign_route(ns)
    except DispatchRoutingError:
        raise
    except Exception as exc:
        logger.error("dispatch routing: resolve_alias failed namespace=%s: %s", ns, exc)
        raise DispatchRoutingError(f"cannot resolve Redis alias for namespace {ns!r}") from exc


def conn_for_alias(alias: str) -> Redis[str]:
    """The django_redis connection for one dispatch pool alias."""
    return get_redis_connection(alias)


def conn_for_namespace(namespace: str) -> Redis[str]:
    """The Redis connection owning one namespace's dispatch keys."""
    ns = namespace or ""
    now = time.monotonic()
    memoized = _memo.get(ns)
    if memoized is not None and memoized[1] > now:
        return conn_for_alias(memoized[0])
    try:
        alias = resolve_alias(ns)
    except DispatchRoutingError:
        if memoized is not None:
            # Refresh failed: keep serving the last known alias. This is a
            # fail-closed fallback to a mapping this process already used,
            # never a guess at a shard.
            logger.warning(
                "dispatch routing: refresh failed namespace=%s; serving stale alias=%s",
                ns,
                memoized[0],
            )
            return conn_for_alias(memoized[0])
        raise
    _memo[ns] = (alias, now + ROUTE_MEMO_TTL_SECONDS)
    return conn_for_alias(alias)


def global_conn() -> Redis[str]:
    """The default Redis connection — ``dispatch:registered`` only."""
    return get_redis_connection("default")


def namespace_for_job_id(job_id: str) -> str:
    """Longest-prefix namespace resolution for a worker-side ``job_id``."""
    from backend.db_periodic_task.dispatch.queue import DispatchQueue
    from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

    DispatchQueue.ensure_queues_loaded()
    task_key = resolve_task_key_from_job_id(job_id, list(DISPATCH_REGISTRY))
    if not task_key:
        return ""
    task_cls = DISPATCH_REGISTRY.get(task_key)
    if task_cls is None:
        return ""
    return task_cls.namespace or ""


def candidate_namespaces() -> set[str]:
    """Registered queue namespaces plus every persisted route namespace.

    Used by the worker-side fan-out fallback for unregistered task keys: the
    payload key is namespace-bound, so finding it requires probing each
    candidate namespace's shard.
    """
    from backend.db_periodic_task.dispatch.queue import DispatchQueue
    from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

    DispatchQueue.ensure_queues_loaded()
    namespaces = {queue_cls.namespace for queue_cls in DispatchQueue.registered_queues() if queue_cls.namespace}
    namespaces.update(getattr(task_cls, "namespace", "") or "" for task_cls in DISPATCH_REGISTRY.values())
    try:
        from backend.db_periodic_task.models import DispatchQueueRoute

        namespaces.update(DispatchQueueRoute.objects.values_list("namespace", flat=True))
    except Exception as exc:
        logger.warning("dispatch routing: route-table namespace read failed: %s", exc)
    return {ns for ns in namespaces if ns}


def bootstrap_routes() -> int:
    """Pre-assign routes for the whole registry (management command / startup).

    Deliberately NOT hooked into ``ensure_queues_loaded()``: that method is
    re-entrant through module imports and would write DB rows mid-import,
    breaking ``migrate`` / ``collectstatic`` before migration 0016 exists.
    """
    from backend.db_periodic_task.dispatch.queue import DispatchQueue
    from backend.db_periodic_task.dispatch.registry import DISPATCH_REGISTRY

    DispatchQueue.ensure_queues_loaded()
    namespaces = {queue_cls.namespace for queue_cls in DispatchQueue.registered_queues() if queue_cls.namespace}
    namespaces.update(getattr(task_cls, "namespace", "") or "" for task_cls in DISPATCH_REGISTRY.values())
    assigned = 0
    for ns in sorted(namespaces):
        resolve_alias(ns)
        assigned += 1
    return assigned
