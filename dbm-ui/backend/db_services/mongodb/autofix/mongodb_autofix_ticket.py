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

import datetime
import logging
from typing import Optional, Union

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core import notify
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.autofix import ctl as autofix_ctl
from backend.db_services.mongodb.autofix.enums import (
    MONGO_AUTOFIX_ACTIVE_STATUSES,
    MongoAutofixConfirmResult,
    MongoAutofixStatus,
)
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.db_services.mongodb.autofix.remark import autofix_core_tag
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.db_services.redis.autofix.enums import AutofixStatus
from backend.db_services.redis.autofix.models import RedisAutofixCore
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

logger = logging.getLogger("root")

# PRE 判定为整机替换的确认结果。同组里这些 Core 才并进同一张替换单。
REPLACE_CONFIRM_RESULTS = frozenset(
    {
        MongoAutofixConfirmResult.DISK_RO.value,
        MongoAutofixConfirmResult.MACHINE_DEAD.value,
        MongoAutofixConfirmResult.DISK_DEAD.value,
    }
)
_UNTRIAGED_STATUS = frozenset({MongoAutofixStatus.DETECTED.value, MongoAutofixStatus.PRE_RUNNING.value})
# 同组未分诊 Core 超过该时间不再挡住替换单开工；挂起的替换单也按此时间兜底启动
GROUP_WAIT_MINUTES = 30


def _apply_followup_approval_flags(details: dict) -> dict:
    """按 ctl followup_need_approval 写入 ITSM / 人工确认（默认需要审批）。"""
    need = autofix_ctl.is_followup_need_approval()
    details["need_itsm"] = need
    details["need_manual_confirm"] = need
    return details


def _autofix_followup_remark(prefix: str, core: MongoAutofixCore) -> str:
    """自愈后续单备注：前缀 + 域名 + 自愈#id + 可选来自 PRE 单据。"""
    base = "{}-{}{}".format(prefix, core.immute_domain, autofix_core_tag(core.id))
    if core.pre_ticket_id and core.pre_ticket_id > 0:
        return _("{}-来自单据#{}".format(base, core.pre_ticket_id))
    return _(base)


def mongos_get_resource_spec(cluster_id: int, mongos_list: list) -> dict:
    """获取申请机器规格信息，mongos申请机器，判断如果一半机器在同一园区，则排除该园区，否则任意园区"""

    include_or_exclue = True
    sub_zone_ids = []
    # 获取mongos的机器
    all_mongos = Cluster.objects.get(id=cluster_id).proxyinstance_set.all()
    # 获取健康mongos机器在园区的比重 {sub_zone_id: number}
    health_mongos_number = len(all_mongos) - len(mongos_list)  # 所有健康mongos的数量
    health_mongos_sub_zone = {}  # 健康mongos在每个园区的数量
    for mongos in all_mongos:
        if mongos.machine.ip in [host["ip"] for host in mongos_list]:
            continue
        if not health_mongos_sub_zone.get(str(mongos.machine.bk_sub_zone_id)):
            health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] = 0
        health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] += 1
    #  健康mongos在每个园区的机器数量占所有健康mongos的数量的百分比
    if health_mongos_number > 0:
        mongos_sub_zone_percent = {
            sub_zone: num / health_mongos_number for sub_zone, num in health_mongos_sub_zone.items()
        }
        for sub_zone, sub_zone_percent in mongos_sub_zone_percent.items():
            if sub_zone_percent >= 0.5:
                include_or_exclue = False
                sub_zone_ids.append(int(sub_zone))
                break

    resource_spec = {}
    for host in mongos_list:
        effective_sub_zone_ids = [z for z in sub_zone_ids if z]
        effective_include = include_or_exclue if effective_sub_zone_ids else True
        resource_spec.update(
            {
                host["ip"]: {
                    "spec_id": host["spec_id"],
                    "count": 1,
                    "spec_config": host["spec_config"],
                    "location_spec": {
                        "city": host["city"],
                        "sub_zone_ids": effective_sub_zone_ids,
                        "include_or_exclue": effective_include,
                    },
                    "labels": host.get("labels") or [],
                    "label_names": host.get("label_names") or [],
                }
            }
        )
    return resource_spec


def mongod_get_resource_spec(cluster_id: int, mongod_list: list) -> dict:
    """获取申请机器规格信息：优先同城；健康存储实例若某园区占比 >=50% 则排除该园区。"""

    include_or_exclue = True
    sub_zone_ids = []
    all_mongod = Cluster.objects.get(id=cluster_id).storageinstance_set.select_related("machine").all()
    fault_ips = {host["ip"] for host in mongod_list}
    health_mongod_sub_zone = {}
    health_mongod_number = 0
    for inst in all_mongod:
        if inst.machine.ip in fault_ips:
            continue
        health_mongod_number += 1
        zone_key = str(inst.machine.bk_sub_zone_id)
        health_mongod_sub_zone[zone_key] = health_mongod_sub_zone.get(zone_key, 0) + 1

    if health_mongod_number > 0:
        mongod_sub_zone_percent = {
            sub_zone: num / health_mongod_number for sub_zone, num in health_mongod_sub_zone.items()
        }
        for sub_zone, sub_zone_percent in mongod_sub_zone_percent.items():
            if sub_zone_percent >= 0.5:
                include_or_exclue = False
                sub_zone_ids.append(int(sub_zone))
                break

    resource_spec = {}
    for host in mongod_list:
        # 园区 id 为 0/空 表示未打园区，排除无意义且会导致本地资源池申请不到机
        effective_sub_zone_ids = [z for z in sub_zone_ids if z]
        effective_include = include_or_exclue if effective_sub_zone_ids else True
        resource_spec[host["ip"]] = {
            "spec_id": host["spec_id"],
            "count": 1,
            "spec_config": host["spec_config"],
            "location_spec": {
                "city": host["city"],
                "sub_zone_ids": effective_sub_zone_ids,
                "include_or_exclue": effective_include,
            },
            # 与部署/替换单据一致：有标签的资源池必须带 labels，否则只会匹配无标签主机
            "labels": host.get("labels") or [],
            "label_names": host.get("label_names") or [],
        }
    return resource_spec


def is_mongos_core(core: MongoAutofixCore) -> bool:
    """MongoAutofixCore 是否为 mongos 故障（DBHA / PRE 共用）。"""
    for fm in getattr(core, "fault_machines", None) or []:
        if not isinstance(fm, dict):
            continue
        machine_type = str(fm.get("machine_type") or fm.get("instance_type") or "").lower()
        if machine_type == MachineType.MONGOS.value:
            return True
    return any(str(role).lower() == MachineType.MONGOS.value for role in (getattr(core, "roles", None) or []))


def _shard_names_by_host(cluster_id: int, host_ids: set) -> dict:
    """一次查出多台机器各自的全部分片名。"""
    host_ids = {int(hid) for hid in host_ids if hid}
    if not cluster_id or not host_ids:
        return {}
    insts = list(
        StorageInstance.objects.filter(cluster__id=cluster_id, machine__bk_host_id__in=host_ids)
        .select_related("machine")
        .only("id", "machine__bk_host_id")
    )
    if not insts:
        return {hid: frozenset() for hid in host_ids}
    _, mapping = MongoDBListRetrieveResource.query_storage_shard(Q(id__in=[inst.id for inst in insts]))
    by_host = {hid: set() for hid in host_ids}
    for inst in insts:
        name = mapping.get(inst.id) or ""
        if name:
            by_host[inst.machine.bk_host_id].add(name)
    return {hid: frozenset(names) for hid, names in by_host.items()}


def _format_shard_group(kind: str, cluster_id: int, shards) -> str:
    return f"{kind}:{cluster_id}:{','.join(sorted(shards))}"


def _parse_shards_from_group(affinity_group: str) -> set:
    if affinity_group.count(":") < 2:
        return set()
    rest = affinity_group.split(":", 2)[2]
    if not rest:
        return set()
    return {name for name in rest.split(",") if name}


def _group_kind_for_machine_type(machine_type: str) -> str:
    if machine_type == MachineType.MONOG_CONFIG.value:
        return "config"
    return "shard"


def _core_machine_type(core: MongoAutofixCore) -> str:
    for item in getattr(core, "fault_machines", None) or []:
        if isinstance(item, dict) and item.get("machine_type"):
            return item["machine_type"]
    if is_mongos_core(core):
        return MachineType.MONGOS.value
    if core.bk_host_id:
        machine = Machine.objects.filter(bk_host_id=core.bk_host_id).only("machine_type").first()
        if machine:
            return machine.machine_type
    return ""


def _merge_connected_shard_groups(items: list) -> dict:
    """
    items: [(key, frozenset shards), ...]
    分片集合有交集（含经第三方连通）的归为一组，返回 key -> 连通块内全部 shards。
    """
    parent = {item[0]: item[0] for item in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, (key_a, shards_a) in enumerate(items):
        for key_b, shards_b in items[i + 1 :]:
            if shards_a & shards_b:
                union(key_a, key_b)
    components = {}
    for key, shards in items:
        root = find(key)
        components.setdefault(root, set()).update(shards)
    return {key: frozenset(components[find(key)]) for key, _ in items}


def affinity_group_for_machine(cluster: Cluster, machine_type: str, bk_host_id: int, shards=None) -> str:
    """反亲和组：mongos/副本集按集群；分片 mongodb/config 按该机全部分片（可传入已查好的 shards）。"""
    cid = cluster.id
    if machine_type == MachineType.MONGOS.value:
        return f"mongos:{cid}"
    if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
        return f"replicaset:{cid}"
    if shards is None:
        shards = _shard_names_by_host(cid, {bk_host_id}).get(bk_host_id or 0, frozenset())
    kind = _group_kind_for_machine_type(machine_type)
    return _format_shard_group(kind, cid, shards)


def collect_mongo_groups(*host_lists) -> list:
    """从故障机列表收集互斥分组。任一主机缺组或分组残缺时返回空列表，回退集群互斥。"""
    from backend.ticket.mongo_operate_group import expand_mongo_group

    groups = set()
    for hosts in host_lists:
        for host in hosts or []:
            if not isinstance(host, dict):
                return []
            expanded = expand_mongo_group(host.get("affinity_group"))
            if not expanded:
                return []
            groups.update(expanded)
    return sorted(groups)


def stamp_mongo_group(details: dict, core: MongoAutofixCore) -> None:
    """给自愈后续单打上本组，供集群互斥按组放行。mongos 不查库。"""
    from backend.ticket.mongo_operate_group import expand_mongo_group

    if _core_machine_type(core) == MachineType.MONGOS.value:
        details["mongo_groups"] = ["mongos:{}".format(core.cluster_id)]
        return
    group = affinity_group_for_core(core)
    expanded = expand_mongo_group(group)
    if expanded:
        details["mongo_groups"] = expanded


def affinity_group_for_core(core: MongoAutofixCore, cluster=None, shards_by_host=None) -> str:
    machine_type = _core_machine_type(core)
    if cluster is None:
        cluster = Cluster.objects.filter(id=core.cluster_id).first()
    if cluster is None:
        kind = "mongos" if machine_type == MachineType.MONGOS.value else "shard"
        return f"{kind}:{core.cluster_id}:"
    shards = None
    if shards_by_host is not None and core.bk_host_id:
        shards = shards_by_host.get(core.bk_host_id, frozenset())
    return affinity_group_for_machine(cluster, machine_type, core.bk_host_id or 0, shards=shards)


def ensure_affinity_groups(cluster_id: int, mongos_list: list, mongod_list: list) -> None:
    """给故障机重算 affinity_group。并单后必须重算，避免第一台留在旧的单分片键上。"""
    if not cluster_id:
        return
    cluster = Cluster.objects.filter(id=cluster_id).first()
    if cluster is None:
        return
    for host in mongos_list or []:
        host["affinity_group"] = f"mongos:{cluster.id}"
    mongod_list = mongod_list or []
    if not mongod_list:
        return
    if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
        for host in mongod_list:
            host["affinity_group"] = f"replicaset:{cluster.id}"
        return
    host_ids = {host.get("bk_host_id") for host in mongod_list if host.get("bk_host_id")}
    shards_by_host = _shard_names_by_host(cluster.id, host_ids)
    by_kind = {"shard": [], "config": []}
    for idx, host in enumerate(mongod_list):
        machine_type = host.get("instance_type") or host.get("machine_type") or ""
        kind = _group_kind_for_machine_type(machine_type)
        shards = shards_by_host.get(host.get("bk_host_id") or 0, frozenset())
        by_kind[kind].append((idx, shards))
    for kind, items in by_kind.items():
        if not items:
            continue
        merged = _merge_connected_shard_groups([(idx, shards) for idx, shards in items])
        for idx, _shards in items:
            mongod_list[idx]["affinity_group"] = _format_shard_group(kind, cluster.id, merged[idx])


def machine_as_current_host(machine) -> dict:
    return {
        "ip": machine.ip,
        "bk_host_id": machine.bk_host_id,
        "sub_zone": machine.bk_sub_zone or "0",
        "sub_zone_id": str(machine.bk_sub_zone_id or 0),
        "rack_id": str(machine.bk_rack_id or 0),
    }


def survivor_current_hosts(cluster: Cluster, affinity_group: str, fault_host_ids: set) -> list:
    """同组里排除本次故障机后，仍然留在集群中的机器。多分片组只取这些分片上的存活机。"""
    shards = _parse_shards_from_group(affinity_group)
    if affinity_group.startswith("mongos:"):
        insts = list(ProxyInstance.objects.select_related("machine").filter(cluster=cluster))
    else:
        insts = list(StorageInstance.objects.select_related("machine").filter(cluster=cluster))
        if affinity_group.startswith("config:"):
            insts = [inst for inst in insts if inst.machine.machine_type == MachineType.MONOG_CONFIG.value]
        elif affinity_group.startswith("shard:"):
            insts = [inst for inst in insts if inst.machine.machine_type == MachineType.MONGODB.value]
        if shards and insts and affinity_group.startswith(("shard:", "config:")):
            _, mapping = MongoDBListRetrieveResource.query_storage_shard(Q(id__in=[inst.id for inst in insts]))
            insts = [inst for inst in insts if mapping.get(inst.id) in shards]
    machines = {}
    for inst in insts:
        machine = inst.machine
        if machine.bk_host_id in fault_host_ids:
            continue
        machines[machine.bk_host_id] = machine
    return [machine_as_current_host(machine) for machine in machines.values()]


def build_mongos_list_from_core(core: MongoAutofixCore) -> list:
    """从 MongoAutofixCore 组装 mongos_list（供 MONGODB_AUTOFIX 申请资源）。"""
    return build_mongod_list_from_core(core)


def _lookup_autofix_instance(core: MongoAutofixCore, port: int):
    """优先 StorageInstance，mongos 回退 ProxyInstance。"""

    def _query(model):
        inst = (
            model.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__ip=core.ip, port=port)
            .first()
        )
        if inst is None and core.bk_host_id:
            inst = (
                model.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id=core.bk_host_id, port=port)
                .first()
            )
        return inst

    return _query(StorageInstance) or _query(ProxyInstance)


def build_mongod_list_from_core(core: MongoAutofixCore) -> list:
    """从 MongoAutofixCore 组装 mongod_list（供 MONGODB_AUTOFIX 申请资源）。"""
    machine = None
    if core.bk_host_id:
        machine = Machine.objects.filter(bk_host_id=core.bk_host_id).first()
    if not machine:
        machine = Machine.objects.filter(ip=core.ip, bk_biz_id=core.bk_biz_id).first()
    if not machine:
        raise Machine.DoesNotExist(f"machine not found for autofix core ip={core.ip} host_id={core.bk_host_id}")

    city = core.bk_city
    try:
        if machine.bk_city_id and machine.bk_city and machine.bk_city.logical_city:
            city = machine.bk_city.logical_city.name
    except Exception:  # noqa: BLE001
        pass

    # 资源标签来自环境变量；正式默认空，本地冒烟在 local.env 配 cyc
    return [
        {
            "ip": machine.ip,
            "spec_id": machine.spec_id,
            "spec_config": machine.spec_config,
            "city": city,
            "cluster_type": core.cluster_type,
            "bk_host_id": machine.bk_host_id,
            "bk_sub_zone": machine.bk_sub_zone,
            "bk_sub_zone_id": machine.bk_sub_zone_id,
            "instance_type": machine.machine_type,
            "labels": list(env.MONGODB_AUTOFIX_RESOURCE_LABELS or []),
            "label_names": list(env.MONGODB_AUTOFIX_RESOURCE_LABEL_NAMES or []),
            "affinity_group": affinity_group_for_core(core),
        }
    ]


def create_mongo_reload_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """从 Core 组装并创建 MONGODB_INSTANCE_RELOAD 单据。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    # 整机多端口：MACHINE；单端口且能解析 instance_id：INSTANCE
    if len(ports) == 1:
        storage = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__ip=core.ip, port=ports[0])
            .first()
        )
        if core.bk_host_id:
            storage = storage or (
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id=core.bk_host_id, port=ports[0])
                .first()
            )
        if storage:
            cluster = storage.cluster.first()
            details = {
                "force": True,
                "target_select_mode": OperaObjType.INSTANCE.value,
                "infos": [
                    {
                        "cluster_id": cluster.id if cluster else core.cluster_id,
                        "bk_host_id": storage.machine.bk_host_id,
                        "ip": storage.machine.ip,
                        "instance_id": storage.id,
                        "port": storage.port,
                        "role": storage.machine_type,
                    }
                ],
            }
        else:
            details = {
                "force": True,
                "target_select_mode": OperaObjType.MACHINE.value,
                "infos": [{"bk_host_id": core.bk_host_id, "ip": core.ip, "ports": ports}],
            }
    else:
        details = {
            "force": True,
            "target_select_mode": OperaObjType.MACHINE.value,
            "infos": [{"bk_host_id": core.bk_host_id, "ip": core.ip, "ports": ports}],
        }

    # 自愈 RELOAD：是否审批由 ctl followup_need_approval 控制（默认 on）
    _apply_followup_approval_flags(details)
    stamp_mongo_group(details, core)

    remark = _autofix_followup_remark(_("自动发起-自愈修复重启"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_INSTANCE_RELOAD.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def create_mongo_ensure_start_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """从 Core 组装并创建 MONGODB_INSTANCE_ENSURE_START（已监听则跳过，不强制 stop）。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    if not ports:
        logger.error("create_mongo_ensure_start_ticket: empty ports core=%s", core.id)
        return None

    infos = []
    for port in ports:
        inst = _lookup_autofix_instance(core, port)
        if not inst:
            logger.error(
                "create_mongo_ensure_start_ticket: instance missing ip=%s port=%s core=%s",
                core.ip,
                port,
                core.id,
            )
            return None
        cluster = inst.cluster.first()
        infos.append(
            {
                "cluster_id": cluster.id if cluster else core.cluster_id,
                "bk_host_id": inst.machine.bk_host_id,
                "ip": inst.machine.ip,
                "instance_id": inst.id,
                "port": inst.port,
                "role": inst.machine_type,
                "bk_cloud_id": inst.machine.bk_cloud_id,
                "db_version": cluster.major_version if cluster else "",
            }
        )

    details = {"infos": infos}
    _apply_followup_approval_flags(details)
    stamp_mongo_group(details, core)
    remark = _autofix_followup_remark(_("自动发起-自愈进程拉起"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_INSTANCE_ENSURE_START.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def create_mongo_fix_status_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """从 Core 组装并创建 MONGODB_INSTANCE_FIX_STATUS（探测成功后修元数据状态，不重启）。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    if not ports:
        logger.error("create_mongo_fix_status_ticket: empty ports core=%s", core.id)
        return None

    infos = []
    for port in ports:
        inst = _lookup_autofix_instance(core, port)
        if not inst:
            logger.error(
                "create_mongo_fix_status_ticket: instance missing ip=%s port=%s core=%s",
                core.ip,
                port,
                core.id,
            )
            return None
        cluster = inst.cluster.first()
        cluster_id = cluster.id if cluster else core.cluster_id
        master_domain = (cluster.immute_domain if cluster else None) or core.immute_domain
        infos.append(
            {
                "ip": inst.machine.ip,
                "port": inst.port,
                "bk_cloud_id": inst.machine.bk_cloud_id,
                "dry_run": False,
                "cluster_id": cluster_id,
                "instance_address": f"{inst.machine.ip}:{inst.port}",
                "master_domain": master_domain,
            }
        )

    details = {
        "infos": infos,
    }
    # 自愈 FIX_STATUS：是否审批由 ctl followup_need_approval 控制（默认 on）
    _apply_followup_approval_flags(details)
    stamp_mongo_group(details, core)

    remark = _autofix_followup_remark(_("自动发起-自愈状态修复"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_INSTANCE_FIX_STATUS.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def create_mongo_manual_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """PRE auth_error / gse_inconclusive：创建显式人工处理单，便于跟踪结案。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    infos = [
        {
            "autofix_core_id": core.id,
            "ip": core.ip,
            "bk_host_id": core.bk_host_id,
            "bk_cloud_id": core.bk_cloud_id,
            "cluster_id": core.cluster_id,
            "cluster_ids": core.cluster_ids or [core.cluster_id],
            "ports": ports,
            "port": ports[0] if ports else None,
            "immute_domain": core.immute_domain,
            "confirm_result": core.confirm_result or "",
            "reason": core.confirm_result or "",
        }
    ]
    details = {"infos": infos}
    _apply_followup_approval_flags(details)
    stamp_mongo_group(details, core)
    remark = _autofix_followup_remark(_("自动发起-自愈人工处理"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_AUTOFIX_MANUAL.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def _extend_hosts(base: list, extra: list) -> None:
    seen = {host.get("ip") for host in base}
    for host in extra:
        ip = host.get("ip")
        if ip and ip not in seen:
            base.append(host)
            seen.add(ip)


def _core_needs_replace_slot(core: MongoAutofixCore, current_id: int) -> bool:
    """当前 Core 一定占位。其它 Core 仅在已确认替换且还没有替换单时并入。"""
    if core.id == current_id:
        return True
    if (core.confirm_result or "") not in REPLACE_CONFIRM_RESULTS:
        return False
    return not core.ticket_id or core.ticket_id <= 0


def _core_is_untriaged(core: MongoAutofixCore) -> bool:
    """未分诊且仍在等待窗口内。超过 GROUP_WAIT_MINUTES 不再挡住替换单。"""
    if core.deal_status not in _UNTRIAGED_STATUS:
        return False
    if (core.confirm_result or "") in REPLACE_CONFIRM_RESULTS:
        return False
    update_at = getattr(core, "update_at", None)
    if update_at is None:
        return True
    if timezone.is_naive(update_at):
        update_at = timezone.make_aware(update_at)
    return timezone.now() - update_at <= datetime.timedelta(minutes=GROUP_WAIT_MINUTES)


def _resource_flow(ticket: Ticket):
    return ticket.flows.filter(flow_type=FlowType.RESOURCE_BATCH_APPLY.value).first()


def _resource_pending(ticket: Ticket) -> bool:
    flow = _resource_flow(ticket)
    if not flow or (flow.details or {}).get("resource_apply_status"):
        return False
    return flow.status == TicketFlowStatus.PENDING.value


def _same_group_cores(core: MongoAutofixCore) -> list:
    """同反亲和组活跃 Core。分片机器按分片集合连通块归并，避免一台多 shard 被拆开。"""
    locked = list(
        MongoAutofixCore.objects.select_for_update()
        .filter(
            bk_biz_id=core.bk_biz_id,
            cluster_id=core.cluster_id,
            deal_status__in=MONGO_AUTOFIX_ACTIVE_STATUSES,
        )
        .order_by("id")
    )
    cluster = Cluster.objects.filter(id=core.cluster_id).first()
    if cluster is None:
        group = affinity_group_for_core(core)
        return [item for item in locked if affinity_group_for_core(item) == group], group

    if cluster.cluster_type == ClusterType.MongoReplicaSet.value or is_mongos_core(core):
        group = affinity_group_for_core(core, cluster=cluster)
        return [item for item in locked if affinity_group_for_core(item, cluster=cluster) == group], group

    host_ids = {item.bk_host_id for item in locked if item.bk_host_id}
    shards_by_host = _shard_names_by_host(cluster.id, host_ids)
    typed = []
    for item in locked:
        machine_type = _core_machine_type(item)
        kind = _group_kind_for_machine_type(machine_type)
        shards = shards_by_host.get(item.bk_host_id or 0, frozenset())
        typed.append((item, kind, shards))
    current_type = _core_machine_type(core)
    current_kind = _group_kind_for_machine_type(current_type)
    same_kind = [(item, shards) for item, kind, shards in typed if kind == current_kind]
    if not same_kind:
        group = affinity_group_for_core(core, cluster=cluster, shards_by_host=shards_by_host)
        return [core], group
    merged = _merge_connected_shard_groups([(item.id, shards) for item, shards in same_kind])
    component_shards = merged.get(core.id, shards_by_host.get(core.bk_host_id or 0, frozenset()))
    group = _format_shard_group(current_kind, cluster.id, component_shards)
    same = [item for item, shards in same_kind if merged.get(item.id) == component_shards]
    return same, group


def _hosts_of_cores(cores: list) -> tuple:
    mongos_list, mongod_list = [], []
    for core in cores:
        if is_mongos_core(core):
            _extend_hosts(mongos_list, build_mongos_list_from_core(core))
        else:
            _extend_hosts(mongod_list, build_mongod_list_from_core(core))
    return mongos_list, mongod_list


def applied_hosts_as_current(ticket: Ticket) -> list:
    """已申请到的新机器，供后续同组申请当作 current_hosts。"""
    inner = ticket.flows.filter(flow_type=FlowType.INNER_FLOW.value).first()
    if not inner:
        return []
    infos = ((inner.details or {}).get("ticket_data") or {}).get("infos") or []
    found, seen = [], set()
    for info in infos:
        hosts = list(info.get("mongos_list") or []) + list(info.get("mongod_list") or [])
        for host in hosts:
            for applied in info.get(host.get("ip")) or []:
                host_id = applied.get("bk_host_id")
                if not host_id or host_id in seen:
                    continue
                seen.add(host_id)
                found.append(
                    {
                        "ip": applied.get("ip"),
                        "bk_host_id": host_id,
                        "sub_zone": applied.get("sub_zone") or "0",
                        "sub_zone_id": str(applied.get("sub_zone_id") or 0),
                        "rack_id": str(applied.get("rack_id") or 0),
                    }
                )
    return found


def _refresh_open_replace_ticket(ticket: Ticket, mongos_list: list, mongod_list: list) -> None:
    """资源申请尚未开始时，把后到的故障机并进同一张单。"""
    from backend.ticket.builders.mongodb.mongo_autofix import MongoDBAutofixResourceParamBuilder

    details = ticket.details
    info = details["infos"][0]
    _extend_hosts(info.setdefault("mongos_list", []), mongos_list)
    _extend_hosts(info.setdefault("mongod_list", []), mongod_list)
    ensure_affinity_groups((info.get("cluster_ids") or [0])[0], info["mongos_list"], info["mongod_list"])
    details["mongo_groups"] = collect_mongo_groups(info["mongos_list"], info["mongod_list"])
    ticket.details = details
    ticket.save(update_fields=["details", "update_at"])

    resource_flow = _resource_flow(ticket)
    if resource_flow:
        resource_flow.details = MongoDBAutofixResourceParamBuilder(ticket).get_params()
        resource_flow.save(update_fields=["details", "update_at"])
    inner = ticket.flows.filter(flow_type=FlowType.INNER_FLOW.value).first()
    if inner:
        inner_details = inner.details
        inner_info = inner_details["ticket_data"]["infos"][0]
        _extend_hosts(inner_info.setdefault("mongos_list", []), mongos_list)
        _extend_hosts(inner_info.setdefault("mongod_list", []), mongod_list)
        ensure_affinity_groups(
            (inner_info.get("cluster_ids") or [0])[0], inner_info["mongos_list"], inner_info["mongod_list"]
        )
        inner.details = inner_details
        inner.save(update_fields=["details", "update_at"])


def _bind_replace_cores(cores: list, ticket: Ticket) -> None:
    for core in cores:
        if core.ticket_id == ticket.id and core.deal_status == MongoAutofixStatus.TICKETED.value:
            continue
        core.ticket_id = ticket.id
        core.deal_status = MongoAutofixStatus.TICKETED.value
        core.save(update_fields=["ticket_id", "deal_status", "update_at"])


def prepare_grouped_replace(core: MongoAutofixCore, mongos_list: list, mongod_list: list) -> dict:
    """同反亲和组并成一张替换单。资源未申请时后到的 Core 挂到该单，不再单独申请。"""
    with transaction.atomic():
        same, group = _same_group_cores(core)
        locked_self = next((item for item in same if item.id == core.id), None)
        if locked_self and locked_self.ticket_id and locked_self.ticket_id > 0:
            ticket = (
                Ticket.objects.select_for_update()
                .filter(id=locked_self.ticket_id, ticket_type=TicketType.MONGODB_AUTOFIX.value)
                .first()
            )
            if ticket:
                return {"ticket": ticket}
        open_tickets = []
        for item in same:
            if item.ticket_id and item.ticket_id > 0 and item.ticket_id not in open_tickets:
                open_tickets.append(item.ticket_id)
        pending_cores = [item for item in same if _core_needs_replace_slot(item, core.id)]
        if all(item.id != core.id for item in pending_cores):
            pending_cores.append(core)
        extra_mongos, extra_mongod = _hosts_of_cores([item for item in pending_cores if item.id != core.id])
        _extend_hosts(mongos_list, extra_mongos)
        _extend_hosts(mongod_list, extra_mongod)
        auto_execute = not any(_core_is_untriaged(item) for item in same if item.id != core.id)
        for ticket_id in open_tickets:
            ticket = (
                Ticket.objects.select_for_update()
                .filter(id=ticket_id, ticket_type=TicketType.MONGODB_AUTOFIX.value)
                .first()
            )
            if not ticket or not _resource_pending(ticket):
                continue
            _refresh_open_replace_ticket(ticket, mongos_list, mongod_list)
            _bind_replace_cores(pending_cores, ticket)
            logger.info("mongodb autofix join replace ticket=%s group=%s", ticket.id, group)
            return {"ticket": ticket}
        prior = []
        for ticket_id in open_tickets:
            ticket = Ticket.objects.filter(id=ticket_id).first()
            if ticket:
                prior.extend(applied_hosts_as_current(ticket))
        return {
            "ticket": None,
            "mongos_list": mongos_list,
            "mongod_list": mongod_list,
            "prior_current_hosts": prior,
            "bind_cores": [item for item in pending_cores if item.id != core.id],
            "auto_execute": auto_execute,
        }


def _claim_pending_replace_ticket(ticket: Ticket) -> bool:
    """资源流仍 PENDING 且未开工时打上 grouped_execute_started，返回是否应启动。"""
    if not ticket or not _resource_pending(ticket):
        return False
    details = ticket.details or {}
    if details.get("grouped_execute_started"):
        return False
    details["grouped_execute_started"] = True
    ticket.details = details
    ticket.save(update_fields=["details", "update_at"])
    return True


def maybe_execute_group_replace(core_id) -> None:
    """同组 PRE 都结束后，启动还挂起的替换单。"""
    if not core_id:
        return
    try:
        core = MongoAutofixCore.objects.filter(id=core_id).first()
        if not core:
            return
        to_start = []
        with transaction.atomic():
            same, group = _same_group_cores(core)
            if any(_core_is_untriaged(item) for item in same):
                logger.info("mongodb autofix replace wait group=%s core=%s", group, core_id)
                return
            ticket_ids = []
            for item in same:
                if item.ticket_id and item.ticket_id > 0 and item.ticket_id not in ticket_ids:
                    ticket_ids.append(item.ticket_id)
            for ticket_id in ticket_ids:
                ticket = (
                    Ticket.objects.select_for_update()
                    .filter(id=ticket_id, ticket_type=TicketType.MONGODB_AUTOFIX.value)
                    .first()
                )
                if _claim_pending_replace_ticket(ticket):
                    to_start.append(ticket)
        from backend.ticket.flow_manager.manager import TicketFlowManager

        for ticket in to_start:
            logger.info("mongodb autofix start grouped replace ticket=%s", ticket.id)
            TicketFlowManager(ticket).run_next_flow()
    except Exception:  # noqa: BLE001
        logger.exception("mongodb autofix start grouped replace fail core=%s", core_id)


def start_hung_grouped_replace_tickets(older_than_minutes: int = GROUP_WAIT_MINUTES) -> int:
    """
    周期兜底：资源流仍 PENDING、未置 grouped_execute_started、且创建超过 N 分钟的替换单，主动开工。
    """
    from backend.ticket.flow_manager.manager import TicketFlowManager

    cutoff = timezone.now() - datetime.timedelta(minutes=older_than_minutes)
    candidates = list(
        Ticket.objects.filter(
            ticket_type=TicketType.MONGODB_AUTOFIX.value,
            create_at__lte=cutoff,
        )
        .order_by("id")
        .only("id", "details", "create_at")[:200]
    )
    started = 0
    for candidate in candidates:
        try:
            to_run = None
            with transaction.atomic():
                ticket = (
                    Ticket.objects.select_for_update()
                    .filter(id=candidate.id, ticket_type=TicketType.MONGODB_AUTOFIX.value)
                    .first()
                )
                if _claim_pending_replace_ticket(ticket):
                    to_run = ticket
            if to_run:
                logger.info("mongodb autofix start hung replace ticket=%s", to_run.id)
                TicketFlowManager(to_run).run_next_flow()
                started += 1
        except Exception:  # noqa: BLE001
            logger.exception("mongodb autofix start hung replace fail ticket=%s", candidate.id)
    return started


def mongo_create_ticket(
    cluster: Union[RedisAutofixCore, MongoAutofixCore],
    cluster_ids: list,
    mongos_list: list,
    mongod_list: list,
):
    """mongodb自愈创建单据。Mongo Core 按反亲和组并单。成功返回 Ticket，规格为空或失败返回 None。"""

    prior_current_hosts = []
    bind_cores = []
    auto_execute = True
    if isinstance(cluster, MongoAutofixCore):
        prepared = prepare_grouped_replace(cluster, mongos_list, mongod_list)
        if prepared.get("ticket"):
            return prepared["ticket"]
        mongos_list = prepared["mongos_list"]
        mongod_list = prepared["mongod_list"]
        prior_current_hosts = prepared["prior_current_hosts"]
        bind_cores = prepared["bind_cores"]
        auto_execute = prepared["auto_execute"]
    if cluster_ids:
        ensure_affinity_groups(cluster_ids[0], mongos_list, mongod_list)

    # 获取dba
    mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.MongoDB.value)
    logger.info("mongodb autofix get dba:{}".format(mongodb_dba))

    # 申请机器规格信息
    resource_spec = {}
    cluster_type = ""

    # 集群类型
    if mongos_list:
        cluster_type = mongos_list[0]["cluster_type"]
        # mongos的资源规格
        mongos_resource_spec = mongos_get_resource_spec(cluster_ids[0], mongos_list)
        logger.info("mongodb autofix mongos resource_spec:{}".format(mongos_resource_spec))
        resource_spec.update(mongos_resource_spec)
    if mongod_list:
        cluster_type = mongod_list[0]["cluster_type"]
        mongod_resource_spec = mongod_get_resource_spec(cluster_ids[0], mongod_list)
        logger.info("mongodb autofix mongod resource_spec:{}".format(mongod_resource_spec))
        resource_spec.update(mongod_resource_spec)

    if not resource_spec:
        return None

    # 单据信息
    details = {
        "ip_source": IpSource.RESOURCE_POOL.value,
        "infos": [
            {
                "cluster_ids": cluster_ids,
                "immute_domain": cluster.immute_domain,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "resource_spec": resource_spec,
                "cluster_type": cluster_type,
                "mongos_list": mongos_list,
                "mongod_list": mongod_list,
                "prior_current_hosts": prior_current_hosts,
            }
        ],
        "mongo_groups": collect_mongo_groups(mongos_list, mongod_list),
    }
    logger.info("mongodb autofix ticket details:{}".format(details))

    core_tag = autofix_core_tag(getattr(cluster, "id", None)) if isinstance(cluster, MongoAutofixCore) else ""
    remark = _("自动发起-自愈任务-{}{}".format(cluster.immute_domain, core_tag))
    pre_ticket_id = getattr(cluster, "pre_ticket_id", None) or 0
    if pre_ticket_id > 0:
        remark = _("自动发起-自愈任务-{}{}-来自单据#{}".format(cluster.immute_domain, core_tag, pre_ticket_id))

    ticket = None
    # 创建单据
    try:
        ticket = Ticket.create_ticket(
            ticket_type=TicketType.MONGODB_AUTOFIX.value,
            creator=mongodb_dba[0],
            bk_biz_id=cluster.bk_biz_id,
            remark=remark,
            details=details,
            auto_execute=auto_execute,
        )

        # 发送自愈消息提醒
        notify.send_msg.apply_async(args=(ticket.id,))
        if isinstance(cluster, MongoAutofixCore):
            cluster.deal_status = MongoAutofixStatus.TICKETED.value
        else:
            cluster.deal_status = AutofixStatus.AF_WFLOW.value
        cluster.status_version = get_random_string(12)
    except Exception as e:
        if isinstance(cluster, MongoAutofixCore):
            cluster.deal_status = MongoAutofixStatus.FAIL.value
        else:
            cluster.deal_status = AutofixStatus.AF_FAIL.value
        cluster.status_version = str(e)
        logger.info("mongodb autofix create ticket fail:{}".format(e))

    # 回写自愈核心表
    if ticket:
        cluster.ticket_id = ticket.id
        if isinstance(cluster, MongoAutofixCore):
            _bind_replace_cores(bind_cores, ticket)
    update_fields = ["ticket_id", "status_version", "deal_status"]
    if not isinstance(cluster, MongoAutofixCore):
        # RedisAutofixCore 历史逻辑用字符串时间
        cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
        update_fields.append("update_at")
    cluster.save(update_fields=update_fields)
    return ticket
