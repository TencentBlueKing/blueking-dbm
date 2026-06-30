# -*- coding: utf-8 -*-
"""
Redis list storage for conf-check candidate cluster IDs.

Candidates are RPUSH'd in sorted order; each pipeline batch act reads a fixed
slice via LRANGE using batch_num. TTL is renewed at each batch start; the list
is deleted when the last batch completes.
"""
import logging
from typing import List

from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")

REDIS_CONF_CHECK_CANDIDATES_KEY = "dbm:redis_conf_check:candidates:{root_id}"
REDIS_CONF_CHECK_CANDIDATES_TTL = 3600  # seconds; renewed at each batch _execute


def _parse_cluster_id(raw) -> int:
    if isinstance(raw, bytes):
        return int(raw.decode())
    return int(raw)


def push_candidate_cluster_ids(key: str, cluster_ids: List[int], ttl: int = REDIS_CONF_CHECK_CANDIDATES_TTL) -> int:
    """Replace the candidate list with sorted unique cluster IDs and set TTL."""
    sorted_ids = sorted(set(cluster_ids))
    if sorted_ids:
        # Idempotent: clear any stale list before push (e.g. accidental root_id reuse).
        RedisConn.delete(key)
        RedisConn.rpush(key, *sorted_ids)
    RedisConn.expire(key, ttl)
    return len(sorted_ids)


def slice_candidate_cluster_ids(key: str, batch_num: int, batch_size: int) -> List[int]:
    """Return cluster IDs for batch_num (1-based) via LRANGE index slice."""
    if batch_num < 1 or batch_size < 1:
        return []
    start = (batch_num - 1) * batch_size
    end = start + batch_size - 1
    try:
        raw_items = RedisConn.lrange(key, start, end) or []
    except Exception as e:
        logger.error("conf_check LRANGE failed for key=%s batch_num=%s: %s", key, batch_num, e)
        return []
    return [_parse_cluster_id(item) for item in raw_items]


def renew_candidates_key_ttl(key: str, ttl: int = REDIS_CONF_CHECK_CANDIDATES_TTL) -> None:
    RedisConn.expire(key, ttl)


def count_candidate_cluster_ids(key: str) -> int:
    try:
        return int(RedisConn.llen(key) or 0)
    except Exception as e:
        logger.error("conf_check LLEN failed for key=%s: %s", key, e)
        return 0


def delete_candidates_key(key: str) -> None:
    try:
        RedisConn.delete(key)
    except Exception as e:
        logger.warning("conf_check DELETE failed for key=%s: %s", key, e)
