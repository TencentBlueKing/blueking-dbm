import math
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import connection


def parallel_fetch(worker_fn: Callable, all_ids: List[int], chunk_count: int = 10) -> Dict[int, List]:
    if len(all_ids) < chunk_count or connection.in_atomic_block:
        return worker_fn(all_ids)

    def _worker_with_cleanup(ids_chunk):
        try:
            return worker_fn(ids_chunk)
        finally:
            connection.close()

    chunk_size = math.ceil(len(all_ids) / chunk_count)
    chunks = [all_ids[i : i + chunk_size] for i in range(0, len(all_ids), chunk_size)]

    with ThreadPoolExecutor(max_workers=min(len(chunks), chunk_count)) as executor:
        futures = [executor.submit(_worker_with_cleanup, chunk) for chunk in chunks]

    merged = defaultdict(list)
    for future in futures:
        for k, v in future.result().items():
            merged[k].extend(v)
    return merged


def get_from_prefetch(qs):
    """与 .get() 语义一致，但走 prefetch 缓存。"""
    results = list(qs.all())
    if len(results) == 0:
        raise ObjectDoesNotExist(f"{qs.model.__name__} matching query does not exist.")
    if len(results) > 1:
        raise MultipleObjectsReturned(f"get() returned more than one {qs.model.__name__}.")
    return results[0]
