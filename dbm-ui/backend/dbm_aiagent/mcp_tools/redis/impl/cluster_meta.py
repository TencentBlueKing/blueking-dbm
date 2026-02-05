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

from django.db.models import F

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import (
    AppCache,
    Cluster,
    ClusterEntry,
    Machine,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)


def list_my_redis_bizs(username: str) -> List:
    res = []
    for app in AppCache.objects.all():
        bk_biz_id = app.bk_biz_id

        if DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, users__0=username, db_type=DBType.Redis.value):
            res.append({"bk_biz_id": bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def list_biz_by_name(biz_name: str) -> List:
    res = []
    for app in AppCache.objects.all():
        if app.db_app_abbr.__contains__(biz_name.lower()):
            res.append({"bk_biz_id": app.bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def redis_list_clusters(bk_biz_id: int) -> List:
    clusters = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type__in=[
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
            ClusterType.TwemproxyTendisSSDInstance,
            ClusterType.TendisTwemproxyRedisInstance,
            ClusterType.RedisInstance,
        ],
    )

    return [
        {
            "immute_domain": c.immute_domain,
            "cluster_type": c.cluster_type,
            "alias": c.alias,
            "region": c.region,
        }
        for c in clusters
    ]


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

        # 设备类型分布
        if machine.bk_svr_device_cls_name:
            machine_distribution["by_device_class"][machine.bk_svr_device_cls_name] += 1

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
        "versions": set(),
        "machines": set(),
    }

    for instance in proxy_instances:
        proxy_stats["by_status"][instance.status] += 1
        proxy_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            proxy_stats["versions"].add(instance.version)
        proxy_stats["machines"].add(instance.machine.bk_host_id)

    proxy_machines = get_machine_stats(proxy_stats["machines"])
    stats = {
        "node_count": proxy_instances.count(),
        "by_status": dict(sorted(proxy_stats["by_status"].items())),
        "versions": sorted(list(proxy_stats["versions"])),
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
        "versions": set(),
        "machines": set(),
    }

    for instance in storage_instances:
        storage_stats["by_role"][instance.instance_role] += 1
        storage_stats["by_status"][instance.status] += 1
        storage_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            storage_stats["versions"].add(instance.version)
        storage_stats["machines"].add(instance.machine.bk_host_id)

    storage_machines = get_machine_stats(storage_stats["machines"])
    # 转换为普通字典并排序
    stats = {
        "node_count": storage_instances.count(),
        "by_status": dict(sorted(storage_stats["by_status"].items())),
        "versions": sorted(list(storage_stats["versions"])),
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


def cluster_proxies(immute_domain: str, hosts: Optional[List[str]] = None) -> List:
    """
    集群proxy列表

    Args:
        immute_domain: 集群域名
        hosts: 可选的主机IP列表，用于过滤特定实例。格式: ["ip1", "ip2"]

    Returns:
        proxy实例信息列表
    """
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    proxy_instances = c_obj.proxyinstance_set.all()

    # 如果指定了hosts参数，进行过滤
    if hosts:
        filtered_instances = []
        for s in proxy_instances:
            if s.machine.ip in hosts:
                filtered_instances.append(s)

        proxy_instances = filtered_instances

    return [
        {
            "address": f"{s.machine.ip}:{s.port}",
            "status": s.status,
            "version": s.version,
            "sub_zone": s.machine.bk_sub_zone,
            "cls_name": s.machine.bk_svr_device_cls_name,
        }
        for s in proxy_instances
    ]


def cluster_masters(immute_domain: str) -> List:
    """集群 master节点 列表"""
    c_obj = Cluster.objects.get(immute_domain=immute_domain)
    master_objs = c_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)

    master_hosts, master_infos = {}, []
    for ins_obj in master_objs:
        if not master_hosts.get(ins_obj.machine.ip):
            master_hosts[ins_obj.machine.ip] = []
        master_hosts[ins_obj.machine.ip].append(ins_obj.port)

    for ip, ports in master_hosts.items():
        m_obj = Machine.objects.get(ip=ip, bk_cloud_id=c_obj.bk_cloud_id, bk_biz_id=c_obj.bk_biz_id)
        master_infos.append(
            {"ip": ip, "ports": ports, "sub_zone": m_obj.bk_sub_zone, "cls_name": m_obj.bk_svr_device_cls_name}
        )

    return master_infos


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


def instance_tuple(addr: str) -> List:
    """查找实例的 主从 信息
    1. 可以是主节点, 查slave
    2. 也可以是从节点, 查master"""
    try:
        ip, port = addr.split(":")
        port = int(port)
    except (ValueError, IndexError):
        return {}

    instance_tuples = defaultdict(list)

    # 查询Proxy实例
    proxy_data = (
        ProxyInstance.objects.filter(machine__ip=ip).values("machine__ip", "port", "cluster__immute_domain").distinct()
    )

    for data in proxy_data:
        if data["cluster__immute_domain"]:
            instance_tuples[data["cluster__immute_domain"]].append({"proxy": f"{data['machine__ip']}:{data['port']}"})

    # 查询Storage实例作为主节点
    master_data = (
        StorageInstanceTuple.objects.filter(ejector__machine__ip=ip, ejector__port=port)
        .select_related("ejector__machine", "receiver__machine", "ejector__cluster")
        .values(
            "ejector__machine__ip",
            "ejector__port",
            "receiver__machine__ip",
            "receiver__port",
            "ejector__cluster__immute_domain",
        )
        .distinct()
    )

    for data in master_data:
        if data["ejector__cluster__immute_domain"]:
            instance_tuples[data["ejector__cluster__immute_domain"]].append(
                {
                    "master": f"{data['ejector__machine__ip']}:{data['ejector__port']}",
                    "slave": f"{data['receiver__machine__ip']}:{data['receiver__port']}",
                }
            )

    # 查询Storage实例作为从节点
    slave_data = (
        StorageInstanceTuple.objects.filter(receiver__machine__ip=ip, receiver__port=port)
        .select_related("ejector__machine", "receiver__machine", "receiver__cluster")
        .values(
            "ejector__machine__ip",
            "ejector__port",
            "receiver__machine__ip",
            "receiver__port",
            "receiver__cluster__immute_domain",
        )
        .distinct()
    )

    for data in slave_data:
        if data["receiver__cluster__immute_domain"]:
            instance_tuples[data["receiver__cluster__immute_domain"]].append(
                {
                    "master": f"{data['ejector__machine__ip']}:{data['ejector__port']}",
                    "slave": f"{data['receiver__machine__ip']}:{data['receiver__port']}",
                }
            )

    return dict(instance_tuples)
