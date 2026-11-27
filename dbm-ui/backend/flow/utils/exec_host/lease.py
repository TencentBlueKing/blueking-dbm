# -*- coding: utf-8 -*-
"""ExecHost 任务引用。并发复用时，最后一个引用释放后才允许回收。"""

from django.db import transaction
from django.utils.translation import gettext as _

DTS_ROOT_ID_TAG = "dts_root_id"
DTS_ROOT_IDS_TAG = "dts_root_ids"


def root_ids_from_tags(tags) -> list:
    """合并 dts_root_ids 与旧的单个 dts_root_id，去重并保持顺序。"""
    tags = tags or {}
    ids = []
    raw = tags.get(DTS_ROOT_IDS_TAG)
    if isinstance(raw, (list, tuple)):
        items = raw
    elif isinstance(raw, str) and raw.strip():
        items = [raw]
    else:
        items = []
    for item in items:
        root_id = str(item or "").strip()
        if root_id and root_id not in ids:
            ids.append(root_id)
    single = str(tags.get(DTS_ROOT_ID_TAG) or "").strip()
    if single and single not in ids:
        ids.append(single)
    return ids


def tags_after_acquire(tags, root_id: str) -> dict:
    root_id = str(root_id or "").strip()
    if not root_id:
        raise ValueError("root_id is empty")
    copied = dict(tags or {})
    ids = root_ids_from_tags(copied)
    if root_id not in ids:
        ids.append(root_id)
    copied[DTS_ROOT_IDS_TAG] = ids
    copied[DTS_ROOT_ID_TAG] = root_id
    return copied


def tags_after_release(tags, root_id: str):
    """返回 (new_tags, remaining_root_ids)。"""
    root_id = str(root_id or "").strip()
    copied = dict(tags or {})
    remaining = [item for item in root_ids_from_tags(copied) if item != root_id]
    copied[DTS_ROOT_IDS_TAG] = remaining
    if str(copied.get(DTS_ROOT_ID_TAG) or "") == root_id:
        copied[DTS_ROOT_ID_TAG] = remaining[-1] if remaining else ""
    return copied, remaining


@transaction.atomic
def acquire_exec_host_ref(exec_host_id: int, root_id: str):
    from backend.exec_host.models import ExecHost, ExecHostStatus

    job = ExecHost.objects.select_for_update().get(id=int(exec_host_id))
    if job.status == ExecHostStatus.DESTROYED.value:
        raise Exception(_("执行机 id={} 已销毁").format(exec_host_id))
    job.tags = tags_after_acquire(job.tags, root_id)
    job.save(update_fields=["tags", "update_at"])
    return job


@transaction.atomic
def release_exec_host_ref(exec_host_id: int, root_id: str, recycle_hosts: bool = False, updater: str = "") -> str:
    """去掉本流程引用。没有其它引用且 recycle_hosts 时，在同一把行锁里回收。

    返回 held / kept / destroyed / recycled。
    """
    from backend.exec_host.api.decommission import decommission
    from backend.exec_host.models import ExecHost, ExecHostStatus

    job = ExecHost.objects.select_for_update().get(id=int(exec_host_id))
    tags, remaining = tags_after_release(job.tags, root_id)
    job.tags = tags
    job.save(update_fields=["tags", "update_at"])
    if remaining:
        return "held"
    if not recycle_hosts:
        return "kept"
    if job.status == ExecHostStatus.DESTROYED.value:
        return "destroyed"
    decommission(exec_host_id=int(exec_host_id), recycle_hosts=True, updater=updater)
    return "recycled"
