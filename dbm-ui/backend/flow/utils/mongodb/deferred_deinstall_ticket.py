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
from collections import OrderedDict
from typing import List, Optional, Union

from django.db import transaction
from django.utils.translation import gettext as _

from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket

logger = logging.getLogger("flow")

# 与 ticket.builders.common.base.fetch_cluster_ids 的键一致。延迟下架单里不能再留下这些键。
_CLUSTER_LOCK_KEYS = {
    "cluster_id",
    "cluster_ids",
    "source_cluster_id",
    "source_cluster_ids",
    "target_cluster_id",
    "src_cluster",
    "dst_cluster",
    "dst_cluster_list",
    "source_cluster",
    "source_clusters",
    "target_cluster",
    "target_clusters",
    "cluster_id_list",
}


def _format_deferred_targets(infos: list) -> str:
    """单据备注里的下架目标：按 IP 去重（延迟下架针对整机，不写端口）。"""
    ips: OrderedDict = OrderedDict()
    for info in infos or []:
        ip = info.get("ip") or ""
        if ip:
            ips[ip] = None
    return ";".join(ips.keys())


def _unlock_running_for_deferred(running_ticket: Ticket, infos: list) -> None:
    """
    替换/自愈单仍 RUNNING 时出延迟下架会撞集群互斥；
    先对**正在跑的单**操作记录解锁 MONGODB_DEFERRED_DEINSTALL。
    """
    unlock_types = [TicketType.MONGODB_DEFERRED_DEINSTALL.value]
    cluster_ids: List[int] = []
    for info in infos or []:
        cid = info.get("cluster_id")
        if cid:
            cluster_ids.append(int(cid))
    qs = ClusterOperateRecord.objects.filter(ticket_id=running_ticket.id)
    if cluster_ids:
        qs = qs.filter(cluster_id__in=cluster_ids)
    for record in qs:
        record.unlock_ticket_type_operations(unlock_types)
        logger.info(
            "deferred deinstall unlock cluster=%s for %s on running=%s",
            record.cluster_id,
            unlock_types,
            running_ticket.id,
        )


def _resolve_relate_ticket(running_ticket: Ticket) -> Ticket:
    """
    关联展示挂到 PRE：AUTOFIX/RELOAD 与延迟下架都作为 PRE 的子单，避免 PRE→AUTOFIX→DEFERRED 递归链。
    查不到 Core/PRE 时回退挂到 running 单。
    """
    from backend.db_services.mongodb.autofix.models import MongoAutofixCore

    core = MongoAutofixCore.objects.filter(ticket_id=running_ticket.id).order_by("-id").first()
    if not core or not core.pre_ticket_id or core.pre_ticket_id <= 0:
        return running_ticket
    try:
        return Ticket.objects.get(id=core.pre_ticket_id)
    except Ticket.DoesNotExist:
        logger.warning(
            "deferred deinstall pre ticket missing id=%s, relate to running=%s",
            core.pre_ticket_id,
            running_ticket.id,
        )
        return running_ticket


def _resolve_autofix_core_id(running_ticket: Optional[Ticket]) -> int:
    """从运行中的替换/自愈单或 PRE 反查 MongoAutofixCore.id。"""
    if running_ticket is None:
        return 0
    from backend.db_services.mongodb.autofix.models import MongoAutofixCore

    core = MongoAutofixCore.objects.filter(ticket_id=running_ticket.id).order_by("-id").first()
    if core:
        return core.id
    core = MongoAutofixCore.objects.filter(pre_ticket_id=running_ticket.id).order_by("-id").first()
    return core.id if core else 0


def _info_is_mongod(info: dict) -> bool:
    raw = info.get("instance_type") or info.get("role") or "mongod"
    if isinstance(raw, list):
        raw = raw[0] if raw else "mongod"
    return str(raw).lower() not in ("mongos",)


def _strip_cluster_lock_keys(obj) -> None:
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in _CLUSTER_LOCK_KEYS:
                obj.pop(key, None)
            else:
                _strip_cluster_lock_keys(obj[key])
    elif isinstance(obj, list):
        for item in obj:
            _strip_cluster_lock_keys(item)


def _snapshot_deferred_runtime(infos: list) -> None:
    """摘 meta 之前记下副本集其余节点，供稍后物理卸载核对 rs.conf、取密码（不落盘明文密码）。"""
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    ak.payload = {}
    for info in infos:
        if not _info_is_mongod(info):
            continue
        cloud = info.get("bk_cloud_id", 0)
        ak.payload["bk_cloud_id"] = cloud
        if "replica_set_peers" not in info:
            try:
                info["replica_set_peers"] = ak._deferred_replica_set_peers(info)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "snapshot deferred replica peers fail ip=%s port=%s", info.get("ip"), info.get("port")
                )
                info["replica_set_peers"] = []


def _detach_deferred_machine(ip: str, bk_cloud_id) -> Optional[dict]:
    """删掉这台机器的实例、副本集/分片元数据和 Machine 行，不回收 CC 主机。"""
    if not ip:
        return None
    from backend.db_meta.models import Machine, ProxyInstance, StorageInstance

    machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if machine is None:
        logger.info("deferred detach skip, machine already gone ip=%s bk_cloud_id=%s", ip, bk_cloud_id)
        return None
    snapshot = {
        "ip": machine.ip,
        "bk_host_id": machine.bk_host_id,
        "bk_biz_id": machine.bk_biz_id,
        "bk_cloud_id": machine.bk_cloud_id,
        "cluster_type": machine.cluster_type,
    }
    with transaction.atomic():
        for obj in list(StorageInstance.objects.filter(machine=machine)):
            obj.cluster.clear()
            obj.bind_entry.clear()
            obj.proxyinstance_set.clear()
            obj.delete()
        for obj in list(ProxyInstance.objects.filter(machine=machine)):
            obj.cluster.clear()
            obj.bind_entry.clear()
            obj.storageinstance.clear()
            obj.delete()
        machine.delete()
    logger.info("deferred detach machine meta ip=%s bk_host_id=%s", ip, snapshot["bk_host_id"])
    return snapshot


def _prepare_deferred_infos(infos: list):
    """建单前摘掉 meta，并去掉会占集群锁的 cluster_id。返回 (infos, old_nodes)。"""
    prepared = [dict(item) for item in infos or []]
    _snapshot_deferred_runtime(prepared)
    snapshots = {}
    old_nodes = []
    seen = set()
    for info in prepared:
        info["force_physical"] = True
        cid = info.get("cluster_id") or ((info.get("cluster_ids") or [None])[0])
        if cid and not info.get("origin_cluster_id"):
            info["origin_cluster_id"] = int(cid)
        key = (info.get("ip"), info.get("bk_cloud_id"))
        if key not in snapshots:
            snapshots[key] = _detach_deferred_machine(info.get("ip"), info.get("bk_cloud_id"))
        snap = snapshots[key] or info.get("recycle_host")
        if not snap or not snap.get("bk_host_id"):
            continue
        info["recycle_host"] = {
            "ip": snap.get("ip") or info.get("ip"),
            "bk_host_id": snap["bk_host_id"],
            "bk_biz_id": snap.get("bk_biz_id"),
            "bk_cloud_id": snap.get("bk_cloud_id", info.get("bk_cloud_id")),
            "cluster_type": snap.get("cluster_type") or "",
        }
        if key not in seen:
            seen.add(key)
            old_nodes.append(
                {
                    "ip": info["recycle_host"]["ip"],
                    "bk_biz_id": info["recycle_host"]["bk_biz_id"],
                    "bk_host_id": info["recycle_host"]["bk_host_id"],
                    "bk_cloud_id": info["recycle_host"]["bk_cloud_id"],
                }
            )
    _strip_cluster_lock_keys(prepared)
    return prepared, old_nodes


def _iter_ticket_host_dicts(details: dict):
    for host in details.get("recycle_hosts") or []:
        if isinstance(host, dict):
            yield host
    old_nodes = details.get("old_nodes")
    if isinstance(old_nodes, dict):
        for nodes in old_nodes.values():
            for host in nodes or []:
                if isinstance(host, dict):
                    yield host
    infos = details.get("infos")
    info_items = infos if isinstance(infos, list) else []
    if isinstance(infos, dict):
        for items in infos.values():
            if isinstance(items, list):
                info_items.extend(items)
    for item in info_items:
        if not isinstance(item, dict):
            continue
        if item.get("ip") and item.get("bk_host_id"):
            yield item
        item_old = item.get("old_nodes")
        if isinstance(item_old, dict):
            for nodes in item_old.values():
                for host in nodes or []:
                    if isinstance(host, dict):
                        yield host
        for role_key in ("mongodb", "mongo_config", "mongos", "mongod_list", "mongos_list"):
            for host in item.get(role_key) or []:
                if isinstance(host, dict):
                    yield host


def _supplement_detached_from_running_ticket(
    infos: list, old_nodes: list, running_ticket: Optional[Ticket], bk_biz_id: int
) -> None:
    """Machine 已在前面节点删除时，从父单详情兜底补齐 recycle_host 与 old_nodes。"""
    details = getattr(running_ticket, "details", None)
    if not isinstance(details, dict):
        return
    by_ip = {}
    for cand in _iter_ticket_host_dicts(details):
        ip = cand.get("ip")
        host_id = cand.get("bk_host_id")
        if ip and host_id and ip not in by_ip:
            by_ip[ip] = cand
    if not by_ip:
        return
    seen = {(node.get("ip"), node.get("bk_cloud_id")) for node in old_nodes if isinstance(node, dict)}
    default_cluster_type = details.get("cluster_type") or ""
    default_biz_id = getattr(running_ticket, "bk_biz_id", None) or bk_biz_id
    for info in infos:
        if not isinstance(info, dict):
            continue
        ip = info.get("ip")
        cloud = info.get("bk_cloud_id", 0)
        snap = info.get("recycle_host") or {}
        if not snap.get("bk_host_id") and ip in by_ip:
            cand = by_ip[ip]
            snap = {
                "ip": ip,
                "bk_host_id": int(cand["bk_host_id"]),
                "bk_biz_id": int(cand.get("bk_biz_id") or default_biz_id or 0),
                "bk_cloud_id": int(cand.get("bk_cloud_id", cloud) or 0),
                "cluster_type": cand.get("cluster_type") or default_cluster_type,
            }
            info["recycle_host"] = snap
        key = (ip, cloud)
        if snap.get("bk_host_id") and key not in seen:
            seen.add(key)
            old_nodes.append(
                {
                    "ip": snap["ip"],
                    "bk_biz_id": snap["bk_biz_id"],
                    "bk_host_id": snap["bk_host_id"],
                    "bk_cloud_id": snap["bk_cloud_id"],
                }
            )


def _drop_deferred_from_running_recycle_hosts(running_ticket: Ticket, infos: list, old_nodes: list) -> None:
    """已转交延迟下架单的旧机从父单 recycle_hosts 摘除，避免父单结束时提前触发 RECYCLE_OLD_HOST。"""
    details = getattr(running_ticket, "details", None)
    if not isinstance(details, dict):
        return
    recycle_hosts = details.get("recycle_hosts")
    if not isinstance(recycle_hosts, list) or not recycle_hosts:
        return
    deferred_host_ids = {
        int(node["bk_host_id"]) for node in (old_nodes or []) if isinstance(node, dict) and node.get("bk_host_id")
    }
    deferred_ips = {info.get("ip") for info in (infos or []) if isinstance(info, dict) and info.get("ip")} | {
        node.get("ip") for node in (old_nodes or []) if isinstance(node, dict) and node.get("ip")
    }
    for info in infos or []:
        if not isinstance(info, dict):
            continue
        recycle_host = info.get("recycle_host") or {}
        if recycle_host.get("bk_host_id"):
            deferred_host_ids.add(int(recycle_host["bk_host_id"]))
    remaining = [
        host
        for host in recycle_hosts
        if not (
            isinstance(host, dict)
            and (
                (host.get("bk_host_id") and int(host["bk_host_id"]) in deferred_host_ids)
                or (host.get("ip") and host.get("ip") in deferred_ips)
            )
        )
    ]
    if len(remaining) != len(recycle_hosts):
        details["recycle_hosts"] = remaining
        running_ticket.details = details
        running_ticket.save(update_fields=["details", "update_at"])
        logger.info(
            "deferred deinstall removed %s host(s) from running ticket=%s recycle_hosts",
            len(recycle_hosts) - len(remaining),
            running_ticket.id,
        )


def deferred_deinstall_ticket(
    infos: list,
    creator: str,
    bk_biz_id: int,
    parent_ticket: Optional[Union[int, Ticket]] = None,
    poll_interval_sec: int = 300,
    max_wait_hours: int = 168,
) -> Ticket:
    """
    创建 MongoDB 延迟下架单据。

    parent_ticket: 当前正在执行的替换/自愈单（用于互斥解锁）；关联展示优先挂到其对应 PRE。
    """
    from backend.db_services.mongodb.autofix.remark import autofix_core_tag

    with transaction.atomic():
        running_ticket = parent_ticket
        if running_ticket is not None:
            running_ticket_id = running_ticket if isinstance(running_ticket, int) else running_ticket.id
            running_ticket = Ticket.objects.select_for_update().get(id=running_ticket_id)
            _unlock_running_for_deferred(running_ticket, infos)

        infos, old_nodes = _prepare_deferred_infos(infos)
        if running_ticket is not None:
            _supplement_detached_from_running_ticket(infos, old_nodes, running_ticket, bk_biz_id)
            _drop_deferred_from_running_recycle_hosts(running_ticket, infos, old_nodes)
        details = {
            "infos": infos,
            "old_nodes": {"instance": old_nodes},
            "poll_interval_sec": poll_interval_sec,
            "max_wait_hours": max_wait_hours,
        }
        _strip_cluster_lock_keys(details)
        targets = _format_deferred_targets(infos) or ((infos[0].get("ip") if infos else "") or "unknown")
        core_tag = autofix_core_tag(_resolve_autofix_core_id(running_ticket))
        remark = _("自动发起-延迟下架-{}{}".format(targets, core_tag))
        relate_ticket = None
        if running_ticket is not None:
            relate_ticket = _resolve_relate_ticket(running_ticket)
            # 备注只挂关联根单（优先 PRE），自愈# 已能串起整条链路
            remark = _("自动发起-延迟下架-{}{}-来自单据#{}".format(targets, core_tag, relate_ticket.id))

        ticket = Ticket.create_ticket(
            ticket_type=TicketType.MONGODB_DEFERRED_DEINSTALL.value,
            creator=creator,
            bk_biz_id=bk_biz_id,
            remark=remark,
            details=details,
            auto_execute=False,
        )
        if relate_ticket is not None:
            relate_ticket.add_related_ticket(ticket, done=True)
            logger.info(
                "deferred deinstall related ticket=%s under relate=%s (running=%s)",
                ticket.id,
                relate_ticket.id,
                running_ticket.id,
            )

        def _start_deferred_flow():
            from backend.ticket.flow_manager.manager import TicketFlowManager

            try:
                TicketFlowManager(ticket=ticket).run_next_flow()
            except Exception:  # noqa: BLE001
                logger.exception("start deferred deinstall flow fail ticket=%s", ticket.id)

        transaction.on_commit(_start_deferred_flow)
        return ticket
