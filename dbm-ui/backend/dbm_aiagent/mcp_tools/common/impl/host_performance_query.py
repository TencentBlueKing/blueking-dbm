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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.utils import query_host_performance_for_machine
from backend.ticket.constants import InstanceType


def collect_machine_ids_for_cluster(cluster: Cluster, instance_roles: Optional[List[str]]) -> List[int]:
    """
    收集集群关联的去重 Machine.id，可选按实例角色过滤。

    Storage 使用 StorageInstance.instance_role；Proxy 使用 InstanceType.PROXY.value（"proxy"）作为过滤标记。
    """
    roles = instance_roles or []
    role_set: Optional[Set[str]] = set(roles) if roles else None
    proxy_marker = InstanceType.PROXY.value
    machine_ids: Set[int] = set()

    if not role_set:
        for inst in StorageInstance.objects.filter(cluster=cluster).select_related("machine"):
            machine_ids.add(inst.machine_id)
        for inst in ProxyInstance.objects.filter(cluster=cluster).select_related("machine"):
            machine_ids.add(inst.machine_id)
    else:
        storage_roles = [r for r in role_set if r != proxy_marker]
        if storage_roles:
            for inst in StorageInstance.objects.filter(
                cluster=cluster, instance_role__in=storage_roles
            ).select_related("machine"):
                machine_ids.add(inst.machine_id)
        if proxy_marker in role_set:
            for inst in ProxyInstance.objects.filter(cluster=cluster).select_related("machine"):
                machine_ids.add(inst.machine_id)

    return sorted(machine_ids)


def collect_instance_roles_by_machine_id(cluster: Cluster, machine_ids: List[int]) -> Dict[int, List[str]]:
    """
    聚合本集群内各 machine_id 对应的实例角色（去重后排序）。

    Storage 取 StorageInstance.instance_role 非空值；存在 ProxyInstance 时增加 proxy（InstanceType.PROXY）。
    """
    if not machine_ids:
        return {}

    proxy_marker = InstanceType.PROXY.value
    roles_by_machine: Dict[int, Set[str]] = defaultdict(set)

    for machine_id, instance_role in StorageInstance.objects.filter(
        cluster=cluster, machine_id__in=machine_ids
    ).values_list("machine_id", "instance_role"):
        if instance_role:
            roles_by_machine[machine_id].add(instance_role)

    for machine_id in (
        ProxyInstance.objects.filter(cluster=cluster, machine_id__in=machine_ids)
        .values_list("machine_id", flat=True)
        .distinct()
    ):
        roles_by_machine[machine_id].add(proxy_marker)

    return {mid: sorted(roles_by_machine.get(mid, set())) for mid in machine_ids}


def query_cluster_hosts_performance(
    cluster: Cluster,
    instance_roles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    查询集群内各主机硬件与基线性能；每台在 query_host_performance 结构基础上附带 instance_roles。
    """
    machine_ids = collect_machine_ids_for_cluster(cluster, instance_roles)
    machines = list(Machine.objects.filter(id__in=machine_ids).order_by("id"))
    roles_map = collect_instance_roles_by_machine_id(cluster, machine_ids)
    hosts = []
    for m in machines:
        row = query_host_performance_for_machine(m)
        row["instance_roles"] = roles_map.get(m.id, [])
        hosts.append(row)
    return {
        "cluster_id": cluster.id,
        "immute_domain": cluster.immute_domain,
        "hosts": hosts,
    }


def query_host_db_instance_ports(*, ip: str, bk_cloud_id: int) -> Dict[str, Any]:
    """
    按 ip + bk_cloud_id 定位 Machine，统计该机上的 StorageInstance 与 ProxyInstance，
    返回实例数量与监听端口列表（升序去重）。
    """
    machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if not machine:
        return {
            "machine": None,
            "instance_count": 0,
            "ports": [],
        }

    storage_ports = list(machine.storageinstance_set.values_list("port", flat=True))
    proxy_ports = list(machine.proxyinstance_set.values_list("port", flat=True))
    instance_count = len(storage_ports) + len(proxy_ports)
    ports_sorted = sorted(set(storage_ports) | set(proxy_ports))

    return {
        "machine": {"ip": machine.ip, "bk_cloud_id": machine.bk_cloud_id},
        "instance_count": instance_count,
        "ports": ports_sorted,
    }
