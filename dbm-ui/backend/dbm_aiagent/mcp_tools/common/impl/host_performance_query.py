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
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceRole, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNotSupportClusterTypeException
from backend.dbm_aiagent.utils import query_host_performance_for_machine
from backend.ticket.constants import InstanceType

logger = logging.getLogger("root")

# 与 mysql cluster_runtime_variables 一致：/data、/data1 等数据盘挂载点前缀
_DATA_MOUNT_PREFIX_RE = re.compile(r"^(/data[0-9]*)(/|$)")
_SHOW_DATADIR_SQL = "SHOW GLOBAL VARIABLES WHERE Variable_name = 'datadir'"


def collect_machine_ids_for_cluster(cluster: Cluster, instance_roles: Optional[List[str]]) -> List[int]:
    """
    收集集群关联的去重 Machine 主键（bk_host_id，与 Storage/Proxy 上 machine_id 一致），可选按实例角色过滤。

    Storage 使用 StorageInstance.instance_role；Proxy 使用 InstanceType.PROXY.value（"proxy"）作为过滤标记。
    """
    roles = instance_roles or []
    role_set: Optional[Set[str]] = set(roles) if roles else None
    proxy_marker = InstanceType.PROXY.value
    machine_ids: Set[int] = set()

    if not role_set:
        machine_ids.update(StorageInstance.objects.filter(cluster=cluster).values_list("machine_id", flat=True))
        machine_ids.update(ProxyInstance.objects.filter(cluster=cluster).values_list("machine_id", flat=True))
    else:
        storage_roles = [r for r in role_set if r != proxy_marker]
        if storage_roles:
            machine_ids.update(
                StorageInstance.objects.filter(cluster=cluster, instance_role__in=storage_roles).values_list(
                    "machine_id", flat=True
                )
            )
        if proxy_marker in role_set:
            machine_ids.update(ProxyInstance.objects.filter(cluster=cluster).values_list("machine_id", flat=True))

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
    machines = list(Machine.objects.filter(bk_host_id__in=machine_ids).order_by("bk_host_id"))
    roles_map = collect_instance_roles_by_machine_id(cluster, machine_ids)
    hosts = []
    for m in machines:
        row = query_host_performance_for_machine(m)
        row["instance_roles"] = roles_map.get(m.pk, [])
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


def _datadir_mount_fields(datadir_value: str) -> Dict[str, str]:
    """由 datadir 推导 data_dir_mount（/data、/data1 等）。"""
    raw = (datadir_value or "").strip()
    if not raw:
        return {"datadir": "", "data_dir_mount": ""}
    mount_match = _DATA_MOUNT_PREFIX_RE.match(os.path.normpath(raw))
    return {"datadir": raw, "data_dir_mount": mount_match.group(1) if mount_match else ""}


def _query_inst_datadir(bk_cloud_id: int, address: str) -> Dict[str, str]:
    """DRS 查询实例 datadir，失败时返回空字段并打 warning。"""
    empty = {"datadir": "", "data_dir_mount": ""}
    try:
        raw_drs_res = DRSApi.v2_mysql_rpc(
            {"addresses": [address], "cmds": [_SHOW_DATADIR_SQL], "bk_cloud_id": bk_cloud_id}
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning(_("查询实例 {} datadir 失败: {}").format(address, str(exc)))
        return empty

    if not raw_drs_res:
        logger.warning(_("查询实例 {} datadir 无 DRS 返回").format(address))
        return empty

    address_res = raw_drs_res[0]
    if address_res.get("error_msg"):
        logger.warning(_("查询实例 {} datadir DRS 错误: {}").format(address, address_res["error_msg"]))
        return empty
    cmd_res = (address_res.get("cmd_results") or [{}])[0]
    if cmd_res.get("error_msg"):
        logger.warning(_("查询实例 {} datadir SQL 错误: {}").format(address, cmd_res["error_msg"]))
        return empty

    datadir = ""
    for row in cmd_res.get("table_data") or []:
        if (row.get("Variable_name") or "").lower() == "datadir":
            datadir = (row.get("Value") or "").strip()
            break
    return _datadir_mount_fields(datadir)


def _match_disk_by_mount(disks: List[Dict[str, Any]], data_dir_mount: str) -> Optional[Dict[str, Any]]:
    """按 data_dir_mount 精确匹配 disks[].mount_point。"""
    if not data_dir_mount:
        return None
    for disk in disks:
        if disk.get("mount_point") == data_dir_mount:
            return disk
    return None


def _flatten_host_base(ref_role: str, perf: Dict[str, Any]) -> Dict[str, Any]:
    """将 machine / host_baseline 平铺为单层 dict（不含磁盘与 instance_count）。"""
    machine_sum = perf.get("machine") or {}
    host_bl = perf.get("host_baseline") or {}
    return {
        "ref_role": ref_role,
        "ip": machine_sum.get("ip"),
        "bk_cloud_id": machine_sum.get("bk_cloud_id"),
        "bk_svr_device_cls_name": machine_sum.get("bk_svr_device_cls_name") or "",
        "device_class": host_bl.get("device_class"),
        "cpu_model": host_bl.get("cpu_model"),
        "cpu_frequency_ghz": host_bl.get("cpu_frequency_ghz"),
        "network_card_speed": host_bl.get("network_card_speed"),
        "vcpu": host_bl.get("vcpu"),
        "memory_gb": host_bl.get("memory_gb"),
        "network_pps_w": host_bl.get("network_pps_w"),
        "intranet_bandwidth_gbps": host_bl.get("intranet_bandwidth_gbps"),
        "queue_count": host_bl.get("queue_count"),
    }


def _flatten_storage_row(
    machine: Machine,
    ref_role: str,
    perf: Dict[str, Any],
    datadir_meta: Dict[str, str],
    matched_disk: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """存储代表机：主机基线平铺 + instance_count + datadir 匹配磁盘基线。"""
    disk_meta = matched_disk or {}
    disk_bl = disk_meta.get("baseline") or {}
    row = _flatten_host_base(ref_role, perf)
    row.update(
        {
            "instance_count": StorageInstance.objects.filter(machine=machine).count(),
            "datadir": datadir_meta.get("datadir") or "",
            "data_dir_mount": datadir_meta.get("data_dir_mount") or "",
            "mount_point": disk_meta.get("mount_point"),
            "disk_type": disk_meta.get("disk_type"),
            "size": disk_meta.get("size"),
            "disk_name": disk_bl.get("disk_name"),
            "capacity_gb": disk_bl.get("capacity_gb"),
            "performance_iops": disk_bl.get("performance_iops"),
            "performance_throughput_mbps": disk_bl.get("performance_throughput_mbps"),
            "random_read_iops": disk_bl.get("random_read_iops"),
            "sequential_write_throughput_mbps": disk_bl.get("sequential_write_throughput_mbps"),
            "write_latency_ms": disk_bl.get("write_latency_ms"),
        }
    )
    return row


def _spider_host_row(machine: Machine, ref_role: str) -> Dict[str, Any]:
    """Spider 代表机平铺结果：仅 machine + host_baseline。"""
    return _flatten_host_base(ref_role, query_host_performance_for_machine(machine))


def _storage_host_row(inst: StorageInstance, ref_role: str) -> Dict[str, Any]:
    """
    存储代表机平铺结果：按实例 datadir 匹配数据盘，展开主机/基线/磁盘字段。
    """
    machine = inst.machine
    datadir_meta = _query_inst_datadir(machine.bk_cloud_id, inst.ip_port)
    perf = query_host_performance_for_machine(machine)
    matched_disk = _match_disk_by_mount(perf.get("disks") or [], datadir_meta.get("data_dir_mount") or "")
    if datadir_meta.get("data_dir_mount") and matched_disk is None:
        logger.warning(
            _("实例 {} data_dir_mount={} 未匹配到主机磁盘挂载点").format(inst.ip_port, datadir_meta.get("data_dir_mount"))
        )
    return _flatten_storage_row(machine, ref_role, perf, datadir_meta, matched_disk)


def _pick_tendbha_storage(cluster: Cluster) -> Optional[StorageInstance]:
    """TenDBHA：取首台 backend_master 实例。"""
    return (
        StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.BACKEND_MASTER)
        .select_related("machine")
        .order_by("machine_id")
        .first()
    )


def _pick_single_storage(cluster: Cluster) -> Optional[StorageInstance]:
    """TenDBSingle：取首台 orphan 实例。"""
    return (
        StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ORPHAN)
        .select_related("machine")
        .order_by("machine_id")
        .first()
    )


def _pick_tc_spider(cluster: Cluster) -> Optional[Machine]:
    """TenDBCluster：取首台 spider_master 所在机器。"""
    proxy = (
        cluster.proxyinstance_set.select_related("machine", "tendbclusterspiderext")
        .filter(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER)
        .order_by("machine_id")
        .first()
    )
    return proxy.machine if proxy else None


def _pick_tc_storage(cluster: Cluster) -> Tuple[Optional[StorageInstance], Optional[int]]:
    """TenDBCluster：最小 shard_id 分片的 remote_master（ejector）实例。"""
    shard = (
        cluster.tendbclusterstorageset_set.select_related("storage_instance_tuple__ejector__machine")
        .order_by("shard_id")
        .first()
    )
    if not shard:
        return None, None
    return shard.storage_instance_tuple.ejector, shard.shard_id


def _ref_storage_only_result(
    base: Dict[str, Any],
    inst: Optional[StorageInstance],
    ref_role: str,
) -> Dict[str, Any]:
    """TenDBHA / TenDBSingle：仅 storage_host，无 spider。"""
    return {
        **base,
        "ref_shard_id": None,
        "spider_host": None,
        "storage_host": (_storage_host_row(inst, ref_role) if inst else None),
    }


def query_cluster_ref_host_perf(cluster: Cluster) -> Dict[str, Any]:
    """
    查询集群参考主机硬件与基线性能（每类一台代表机）。

    TenDBHA：仅 storage_host=backend_master；spider_host=null。
    TenDBSingle：仅 storage_host=orphan；spider_host=null。
    TenDBCluster：spider_host=一台 spider_master；storage_host=首分片 remote_master。
    spider_host / storage_host 均为平铺字段；storage_host 另含 instance_count、
    datadir/data_dir_mount 及按 datadir 匹配的数据盘基线。
    """
    base = {
        "cluster_id": cluster.id,
        "immute_domain": cluster.immute_domain,
        "cluster_type": cluster.cluster_type,
    }

    if cluster.cluster_type == ClusterType.TenDBHA:
        return _ref_storage_only_result(base, _pick_tendbha_storage(cluster), InstanceRole.BACKEND_MASTER.value)

    if cluster.cluster_type == ClusterType.TenDBSingle:
        return _ref_storage_only_result(base, _pick_single_storage(cluster), InstanceRole.ORPHAN.value)

    if cluster.cluster_type == ClusterType.TenDBCluster:
        spider_machine = _pick_tc_spider(cluster)
        storage_inst, shard_id = _pick_tc_storage(cluster)
        if storage_inst is None:
            logger.warning(_("TenDBCluster 集群 {} 无分片存储集，storage_host 为空").format(cluster.id))
        return {
            **base,
            "ref_shard_id": shard_id,
            "spider_host": (
                _spider_host_row(spider_machine, TenDBClusterSpiderRole.SPIDER_MASTER.value)
                if spider_machine
                else None
            ),
            "storage_host": (
                _storage_host_row(storage_inst, InstanceRole.REMOTE_MASTER.value) if storage_inst else None
            ),
        }

    raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster.cluster_type)
