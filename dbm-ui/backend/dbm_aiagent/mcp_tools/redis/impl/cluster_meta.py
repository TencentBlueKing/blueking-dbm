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
from typing import Dict, List, Optional

from django.db.models import F, Q

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_biz_by_abbr, get_managed_biz


# 解析地址列表为 (ip, port) 元组
def parse_addresses(addresses: List[str]) -> List[tuple]:
    parsed = []
    for addr in addresses:
        parts = addr.strip().split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid instance address format: {addr}, expected 'ip:port'")
        ip, port = parts[0], int(parts[1])
        parsed.append((ip, port))
    return parsed


def list_my_redis_bizs(username: str) -> List[dict]:
    """List Redis bizs managed by the user (manage-only semantics)."""
    return get_managed_biz(username, DBType.Redis, detailed=True)


def list_biz_by_name(biz_name: str) -> List[dict]:
    """List bizs matching name via db_app_abbr (case-insensitive substring)."""
    return get_biz_by_abbr(biz_name, detailed=True)


def redis_list_clusters(bk_biz_id: int, page: int = 1, page_size: int = 30) -> dict:
    qs = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type__in=[
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
            ClusterType.TwemproxyTendisSSDInstance,
            ClusterType.TendisTwemproxyRedisInstance,
            ClusterType.RedisInstance,
        ],
    ).order_by("id")

    total = qs.count()
    offset = (page - 1) * page_size
    clusters = qs[offset : offset + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "clusters": [
            {
                "immute_domain": c.immute_domain,
                "cluster_type": c.cluster_type,
                "alias": c.alias,
                "region": c.region,
            }
            for c in clusters
        ],
    }


def get_machine_stats(all_machine_ids) -> Dict:
    machines = Machine.objects.filter(bk_host_id__in=all_machine_ids).select_related("bk_city")

    # 统计机器分布信息
    machine_distribution = {
        "total_count": len(all_machine_ids),
        "by_sub_zone": defaultdict(int),
        "by_os": defaultdict(int),
        "by_device_class": defaultdict(int),
        "spec_summary": defaultdict(int),
    }

    for machine in machines:
        # 子Zone分布
        if machine.bk_sub_zone:
            machine_distribution["by_sub_zone"][machine.bk_sub_zone] += 1

        # 操作系统分布
        if machine.bk_os_name:
            machine_distribution["by_os"][machine.bk_os_name] += 1

        # 机型分布（来自 spec_config.device_class，格式为列表）
        device_classes = (machine.spec_config or {}).get("device_class") or []
        for dc in device_classes:
            if dc:
                machine_distribution["by_device_class"][dc] += 1

        # 规格统计
        if machine.spec_id:
            machine_distribution["spec_summary"][f"spec_{machine.spec_id}"] += 1

    return machine_distribution


def cluster_basic_overview(immute_domain: str) -> Dict:
    # 基本信息
    try:
        cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)
        return {
            "bk_biz_id": cluster_obj.bk_biz_id,
            "cluster_id": cluster_obj.id,
            "immute_domain": cluster_obj.immute_domain,
            "alias": cluster_obj.alias,
            "cluster_type": cluster_obj.cluster_type,
            "major_version": cluster_obj.major_version,
            "region": cluster_obj.region,
            "disaster_tolerance_level": cluster_obj.disaster_tolerance_level,
            "tags": ["{}:{}".format(tag.key, tag.value) for tag in cluster_obj.tags.all()],
            "cluster_entries": [
                {"entry_type": ce.cluster_entry_type, "entry_addr": ce.entry}
                for ce in ClusterEntry.objects.filter(cluster=cluster_obj)
            ],
        }
    except Cluster.DoesNotExist:
        return {"error": "集群不存在"}


def cluster_proxy_overview(immute_domain: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
    # 查询代理实例
    proxy_instances = (
        ProxyInstance.objects.filter(cluster=cluster_obj)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )

    # 统计代理实例信息
    proxy_stats = {
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": defaultdict(int),
        "machines": set(),
    }

    for instance in proxy_instances:
        proxy_stats["by_status"][instance.status] += 1
        proxy_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            proxy_stats["versions"][instance.version] += 1
        proxy_stats["machines"].add(instance.machine.bk_host_id)

    proxy_machines = get_machine_stats(proxy_stats["machines"])
    stats = {
        "node_count": proxy_instances.count(),
        "by_status": dict(sorted(proxy_stats["by_status"].items())),
        "by_version": dict(sorted(proxy_stats["versions"].items())),
        "by_machine_type": dict(sorted(proxy_stats["by_machine_type"].items())),
        "machine_count": len(proxy_stats["machines"]),
        "by_os": dict(sorted(proxy_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(proxy_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(proxy_machines["by_device_class"].items())),
    }
    return stats


def cluster_redis_overview(immute_domain: str, role: str) -> Dict:
    cluster_obj = Cluster.objects.get(immute_domain=immute_domain)

    # 查询存储实例
    storage_instances = (
        StorageInstance.objects.filter(cluster=cluster_obj, instance_role=role)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )

    # 统计存储实例信息
    storage_stats = {
        "by_role": defaultdict(int),
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": defaultdict(int),
        "machines": set(),
    }

    for instance in storage_instances:
        storage_stats["by_role"][instance.instance_role] += 1
        storage_stats["by_status"][instance.status] += 1
        storage_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            storage_stats["versions"][instance.version] += 1
        storage_stats["machines"].add(instance.machine.bk_host_id)

    storage_machines = get_machine_stats(storage_stats["machines"])
    # 转换为普通字典并排序
    stats = {
        "node_count": storage_instances.count(),
        "by_status": dict(sorted(storage_stats["by_status"].items())),
        "by_version": dict(sorted(storage_stats["versions"].items())),
        "by_machine_type": dict(sorted(storage_stats["by_machine_type"].items())),
        "machine_count": len(storage_stats["machines"]),
        "by_os": dict(sorted(storage_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(storage_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(storage_machines["by_device_class"].items())),
    }
    return stats


def cluster_storage_overiew(immute_domain: str) -> Dict:
    masters = cluster_redis_overview(immute_domain=immute_domain, role="redis_master")
    slaves = cluster_redis_overview(immute_domain=immute_domain, role="redis_slave")

    return {"redis_master": masters, "redis_slave": slaves}


def cluster_proxies(immute_domain: str, hosts: Optional[List[str]] = None, page: int = 1, page_size: int = 20) -> dict:
    """
    集群proxy列表

    Args:
        immute_domain: 集群域名
        hosts: 可选的主机IP列表，用于过滤特定实例。格式: ["ip1", "ip2"]
        page: 页码，从1开始
        page_size: 每页数量

    Returns:
        分页的proxy实例信息
    """
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    proxy_instances = list(c_obj.proxyinstance_set.select_related("machine").order_by("id"))

    # 如果指定了hosts参数，进行过滤
    if hosts:
        proxy_instances = [s for s in proxy_instances if s.machine.ip in hosts]

    total = len(proxy_instances)
    offset = (page - 1) * page_size
    paged = proxy_instances[offset : offset + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "proxies": [
            {
                "address": f"{s.machine.ip}:{s.port}",
                "status": s.status,
                "version": s.version,
                "sub_zone": s.machine.bk_sub_zone,
                "cls_name": s.machine.bk_svr_device_cls_name,
            }
            for s in paged
        ],
    }


def instance_detail(immute_domain: str, addrs: Optional[List[str]] = None) -> List:
    try:
        c_obj = Cluster.objects.get(immute_domain=immute_domain)
    except Cluster.DoesNotExist:
        raise ValueError(f"Cluster {immute_domain} does not exist")

    address_filter = None
    if addrs:
        address_filter = parse_addresses(addrs)

    storage_qs = (
        StorageInstance.objects.filter(cluster=c_obj)
        .select_related("machine", "db_package")
        .prefetch_related("bind_entry")
    )
    if address_filter:
        q = Q()
        for ip, port in address_filter:
            q |= Q(machine__ip=ip, port=port)
        storage_qs = storage_qs.filter(q)

    storage_instances = []
    for inst in storage_qs:
        storage_instances.append(
            {
                "address": f"{inst.machine.ip}:{inst.port}",
                "version": inst.version,
                "status": inst.status,
                "instance_role": inst.instance_role,
                "machine_type": inst.machine_type,
                "cluster_type": inst.cluster_type,
                "sub_zone": inst.machine.bk_sub_zone,
                "cls_name": inst.machine.bk_svr_device_cls_name,
                "bind_entries": [{"id": entry.id, "entry": entry.entry} for entry in inst.bind_entry.all()],
            }
        )

    proxy_instances = []
    proxy_qs = (
        ProxyInstance.objects.filter(cluster=c_obj)
        .select_related("machine", "db_package")
        .prefetch_related("bind_entry", "storageinstance", "storageinstance__machine")
    )
    if address_filter:

        q = Q()
        for ip, port in address_filter:
            q |= Q(machine__ip=ip, port=port)
        proxy_qs = proxy_qs.filter(q)
    for inst in proxy_qs:
        proxy_instances.append(
            {
                "address": f"{inst.machine.ip}:{inst.port}",
                "version": inst.version,
                "status": inst.status,
                "instance_role": inst.machine_type,
                "machine_type": inst.access_layer,
                "cluster_type": inst.cluster_type,
                "sub_zone": inst.machine.bk_sub_zone,
                "cls_name": inst.machine.bk_svr_device_cls_name,
                "bind_entries": [{"id": entry.id, "entry": entry.entry} for entry in inst.bind_entry.all()],
            }
        )

    return storage_instances + proxy_instances


def get_cluster_storage_tuples(
    immute_domain: str,
    instance_addresses: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, list]:
    """查询集群的存储节点主从关系信息"""

    # 解析实例地址为 (ip, port) 集合，用于后续过滤
    addr_set = set()
    if instance_addresses:
        for addr in instance_addresses:
            try:
                ip, port = addr.split(":")
                addr_set.add((ip, int(port)))
            except (ValueError, IndexError):
                continue

    # 基于集群域名查询所有主从关系
    base_qs = (
        StorageInstanceTuple.objects.filter(ejector__cluster__immute_domain=immute_domain)
        .select_related("ejector__machine", "receiver__machine")
        .values(
            "ejector__machine__ip",
            "ejector__port",
            "receiver__machine__ip",
            "receiver__port",
        )
        .distinct()
        .order_by("ejector__machine__ip", "ejector__port")
    )

    tuples = []
    seen = set()
    for data in base_qs:
        master_ip = data["ejector__machine__ip"]
        master_port = data["ejector__port"]
        slave_ip = data["receiver__machine__ip"]
        slave_port = data["receiver__port"]

        # 如果指定了实例地址，则仅保留与指定地址相关的主从对
        if addr_set:
            if (master_ip, master_port) not in addr_set and (slave_ip, slave_port) not in addr_set:
                continue

        master_addr = f"{master_ip}:{master_port}"
        slave_addr = f"{slave_ip}:{slave_port}"

        # 去重
        pair_key = (master_addr, slave_addr)
        if pair_key in seen:
            continue
        seen.add(pair_key)

        tuples.append(
            {
                "redis_master": master_addr,
                "redis_slave": slave_addr,
            }
        )

    total = len(tuples)
    offset = (page - 1) * page_size
    paged = tuples[offset : offset + page_size]

    return {"total": total, "page": page, "page_size": page_size, "tuples": paged}


def list_clusters_by_hosts(hosts: List) -> List[Dict]:
    cluster_host = []

    # 通过storageinstance查询
    storage_data = (
        Cluster.objects.filter(storageinstance__machine__ip__in=hosts)
        .values(
            "immute_domain", host=F("storageinstance__machine__ip"), instance_role=F("storageinstance__instance_role")
        )
        .distinct()
    )

    cluster_host.extend(storage_data)

    # 通过proxyinstance查询
    proxy_data = (
        Cluster.objects.filter(proxyinstance__machine__ip__in=hosts)
        .values(
            "immute_domain",
            host=F("proxyinstance__machine__ip"),
            instance_role=F("proxyinstance__machine__access_layer"),
        )
        .distinct()
    )

    cluster_host.extend(proxy_data)

    # 去重（如果需要）
    seen = set()
    unique_results = []
    for item in cluster_host:
        key = (item["immute_domain"], item["host"], item["instance_role"])
        if key not in seen:
            seen.add(key)
            unique_results.append(item)

    return unique_results
