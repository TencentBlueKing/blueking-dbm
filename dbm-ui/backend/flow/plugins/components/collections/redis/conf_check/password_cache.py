# -*- coding: utf-8 -*-
"""
Process-local TTL cache for redis cluster passwords during conf-check runs.

697 batches may revisit the same cluster; caching avoids repeated get_password calls
within a single pipeline-schedule worker process.

Note: this is module-level state per OS process. Under Celery prefork each worker has
its own cache, so batches scheduled on different workers cannot share entries. That is
acceptable here because conf-check batches run serially on one pipeline and the same
schedule worker usually handles every tick; cross-worker sharing would need Redis
(and careful secret handling). The 30min TTL also limits staleness when idle.
"""
import time
from threading import Lock
from typing import Dict, Optional, Set, Tuple

PASSWORD_CACHE_TTL_SECONDS = 30 * 60

# cluster_id -> (cached_at, passwords, password_error)
_lock = Lock()
_cache: Dict[int, Tuple[float, Dict, Optional[str]]] = {}


def _entry_valid(entry: Tuple[float, Dict, Optional[str]], now: float) -> bool:
    return entry and (now - entry[0]) < PASSWORD_CACHE_TTL_SECONDS


def get_cached_cluster_passwords(cluster_ids: Set[int]) -> Tuple[Dict[int, Dict], Set[int], Dict[int, str]]:
    """Return cached passwords, ids still needing fetch, and cached per-cluster errors."""
    now = time.time()
    hit: Dict[int, Dict] = {}
    missing: Set[int] = set()
    errors: Dict[int, str] = {}
    with _lock:
        for cluster_id in cluster_ids:
            entry = _cache.get(cluster_id)
            if _entry_valid(entry, now):
                hit[cluster_id] = entry[1]
                if entry[2]:
                    errors[cluster_id] = entry[2]
            else:
                missing.add(cluster_id)
    return hit, missing, errors


def put_cached_cluster_passwords(
    passwords: Dict[int, Dict],
    errors: Optional[Dict[int, str]] = None,
) -> None:
    if not passwords and not errors:
        return
    now = time.time()
    errors = errors or {}
    with _lock:
        for cluster_id, password_map in passwords.items():
            _cache[cluster_id] = (now, password_map, errors.get(cluster_id))
        for cluster_id, error in errors.items():
            if cluster_id in passwords:
                continue
            _cache[cluster_id] = (now, {}, error)
