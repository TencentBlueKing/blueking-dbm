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
from typing import Dict, List

from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, ClusterEntry, StorageInstance


def list_my_kafka_bizs(userID: str) -> List:
    """查询用户负责的Kafka业务列表"""
    from backend.configuration.constants import DBType
    from backend.configuration.models import DBAdministrator

    res = []
    for app in AppCache.objects.all():
        bk_biz_id = app.bk_biz_id

        if DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, users__0=userID, db_type=DBType.Kafka.value):
            res.append({"bk_biz_id": bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def list_biz_by_name(biz_name: str) -> List:
    """根据业务英文名查询业务详情"""
    res = []
    for app in AppCache.objects.all():
        if app.db_app_abbr.__contains__(biz_name.lower()):
            res.append({"bk_biz_id": app.bk_biz_id, "app_name": app.bk_biz_name, "abbr": app.db_app_abbr})
    return res


def kafka_list_clusters(bk_biz_id: int) -> List:
    """查询业务下的Kafka集群列表"""
    clusters = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.Kafka,
    )

    return [
        {
            "cluster_id": c.id,
            "bk_cloud_id": c.bk_cloud_id,
            "cluster_type": c.cluster_type,
            "immute_domain": c.immute_domain,
            "alias": c.alias,
            "region": c.region,
            "broker_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value)),
            "zookeeper_count": len(c.storageinstance_set.filter(machine_type=MachineType.ZOOKEEPER.value)),
            "kafka_version": c.major_version,
        }
        for c in clusters
    ]


def get_machine_stats(all_machine_ids) -> Dict:
    """统计机器分布信息"""
    from backend.db_meta.models import Machine

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


def get_spec_details(spec_keys: List) -> Dict:
    """获取规格详细信息"""
    from backend.db_meta.models import Spec

    if not spec_keys:
        return {}

    # 从 spec_keys 中提取 spec_id (spec_576 -> 576)
    spec_ids = []
    for key in spec_keys:
        if key.startswith("spec_"):
            try:
                spec_id = int(key.replace("spec_", ""))
                spec_ids.append(spec_id)
            except ValueError:
                continue

    if not spec_ids:
        return {}

    # 查询 Spec 对象
    specs = Spec.objects.filter(spec_id__in=spec_ids)

    # 构建规格详情字典
    spec_details = {}
    for spec in specs:
        spec_details[spec.spec_id] = {
            "spec_id": spec.spec_id,
            "spec_name": spec.spec_name,
            "cpu": spec.cpu,
            "memory": spec.mem,
            "storage_spec": spec.storage_spec,
            "device_class": spec.device_class,
            "desc": spec.desc,
        }

    return spec_details


def cluster_overview(immute_domain: str) -> Dict:
    """查询Kafka集群详细信息，返回统计信息"""
    from backend.db_meta.models import Spec

    cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)

    # 基本信息
    stats = {
        "bk_cloud_id": cluster_obj.bk_cloud_id,
        "bk_biz_id": cluster_obj.bk_biz_id,
        "cluster_id": cluster_obj.id,
        "immute_domain": cluster_obj.immute_domain,
        "alias": cluster_obj.alias,
        "cluster_type": cluster_obj.cluster_type,
        "major_version": cluster_obj.major_version,
        "phase": cluster_obj.phase,
        "region": cluster_obj.region,
        "disaster_tolerance_level": cluster_obj.disaster_tolerance_level,
        "tags": ["{}:{}".format(tag.key, tag.value) for tag in cluster_obj.tags.all()],
        "cluster_entries": [
            {"entry_type": ce.cluster_entry_type, "entry_addr": ce.entry}
            for ce in ClusterEntry.objects.filter(cluster=cluster_obj)
        ],
    }

    # 查询存储实例 (broker 和 zookeeper)
    storage_instances = (
        StorageInstance.objects.filter(cluster=cluster_obj)
        .select_related("machine", "machine__bk_city")
        .prefetch_related("bind_entry")
    )

    # 统计broker实例信息
    broker_instances = storage_instances.filter(instance_role=InstanceRole.BROKER.value)
    broker_stats = {
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }
    broker_nodes = []

    # 收集所有 spec_id 用于批量查询规格信息
    broker_spec_ids = set()
    for instance in broker_instances:
        if instance.machine.spec_id:
            broker_spec_ids.add(instance.machine.spec_id)

    # 批量查询规格信息
    broker_specs = {}
    if broker_spec_ids:
        specs = Spec.objects.filter(spec_id__in=broker_spec_ids)
        broker_specs = {spec.spec_id: spec for spec in specs}

    for instance in broker_instances:
        broker_stats["by_status"][instance.status] += 1
        broker_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            broker_stats["versions"].add(instance.version)
        broker_stats["machines"].add(instance.machine.bk_host_id)
        # 收集节点详细信息，用于缩容/替换操作
        node_info = {
            "ip": instance.machine.ip,
            "bk_host_id": instance.machine.bk_host_id,
            "bk_cloud_id": instance.machine.bk_cloud_id,
            "port": instance.port,
            "instance_id": instance.id,
            "machine_type": instance.machine_type,
            "status": instance.status,
            "device_class": instance.machine.bk_svr_device_cls_name,
        }
        # 添加规格详细信息
        if instance.machine.spec_id and instance.machine.spec_id in broker_specs:
            spec = broker_specs[instance.machine.spec_id]
            node_info["spec"] = {
                "spec_id": spec.spec_id,
                "spec_name": spec.spec_name,
                "cpu": spec.cpu,
                "memory": spec.mem,
                "storage_spec": spec.storage_spec,
            }
        broker_nodes.append(node_info)

    broker_machines = get_machine_stats(broker_stats["machines"])
    stats["broker_instances"] = {
        "node_count": broker_instances.count(),
        "by_status": dict(sorted(broker_stats["by_status"].items())),
        "versions": sorted(list(broker_stats["versions"])),
        "machine_count": len(broker_stats["machines"]),
        "by_os": dict(sorted(broker_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(broker_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(broker_machines["by_device_class"].items())),
        "by_spec": dict(sorted(broker_machines["spec_summary"].items())),
        "spec_details": get_spec_details(list(broker_machines["spec_summary"].keys())),
        "nodes": broker_nodes,
    }

    # 统计zookeeper实例信息
    zookeeper_instances = storage_instances.filter(machine_type=MachineType.ZOOKEEPER.value)
    zookeeper_stats = {
        "by_status": defaultdict(int),
        "by_machine_type": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }
    zookeeper_nodes = []

    # 收集所有 spec_id 用于批量查询规格信息
    zookeeper_spec_ids = set()
    for instance in zookeeper_instances:
        if instance.machine.spec_id:
            zookeeper_spec_ids.add(instance.machine.spec_id)

    # 批量查询规格信息
    zookeeper_specs = {}
    if zookeeper_spec_ids:
        specs = Spec.objects.filter(spec_id__in=zookeeper_spec_ids)
        zookeeper_specs = {spec.spec_id: spec for spec in specs}

    for instance in zookeeper_instances:
        zookeeper_stats["by_status"][instance.status] += 1
        zookeeper_stats["by_machine_type"][instance.machine_type] += 1
        if instance.version:
            zookeeper_stats["versions"].add(instance.version)
        zookeeper_stats["machines"].add(instance.machine.bk_host_id)
        # 收集节点详细信息
        node_info = {
            "ip": instance.machine.ip,
            "bk_host_id": instance.machine.bk_host_id,
            "bk_cloud_id": instance.machine.bk_cloud_id,
            "port": instance.port,
            "instance_id": instance.id,
            "machine_type": instance.machine_type,
            "status": instance.status,
            "device_class": instance.machine.bk_svr_device_cls_name,
        }
        # 添加规格详细信息
        if instance.machine.spec_id and instance.machine.spec_id in zookeeper_specs:
            spec = zookeeper_specs[instance.machine.spec_id]
            node_info["spec"] = {
                "spec_id": spec.spec_id,
                "spec_name": spec.spec_name,
                "cpu": spec.cpu,
                "memory": spec.mem,
                "storage_spec": spec.storage_spec,
            }
        zookeeper_nodes.append(node_info)

    zookeeper_machines = get_machine_stats(zookeeper_stats["machines"])
    stats["zookeeper_instances"] = {
        "node_count": zookeeper_instances.count(),
        "by_status": dict(sorted(zookeeper_stats["by_status"].items())),
        "versions": sorted(list(zookeeper_stats["versions"])),
        "machine_count": len(zookeeper_stats["machines"]),
        "by_os": dict(sorted(zookeeper_machines["by_os"].items())),
        "by_sub_zone": dict(sorted(zookeeper_machines["by_sub_zone"].items())),
        "by_device_class": dict(sorted(zookeeper_machines["by_device_class"].items())),
        "by_spec": dict(sorted(zookeeper_machines["spec_summary"].items())),
        "spec_details": get_spec_details(list(zookeeper_machines["spec_summary"].keys())),
        "nodes": zookeeper_nodes,
    }

    return stats


def search_specs_by_name(spec_name: str, spec_cluster_type: str = "kafka") -> List:
    """根据规格名称模糊查询规格信息

    Args:
        spec_name: 规格名称（支持模糊匹配，如 '16核32G'）
        spec_cluster_type: 规格集群类型，默认为 kafka

    Returns:
        匹配的规格列表
    """
    from backend.db_meta.models import Spec

    specs = Spec.objects.filter(spec_name__icontains=spec_name, spec_cluster_type=spec_cluster_type, enable=True)

    return [
        {
            "spec_id": spec.spec_id,
            "spec_name": spec.spec_name,
            "spec_cluster_type": spec.spec_cluster_type,
            "spec_machine_type": spec.spec_machine_type,
            "cpu": spec.cpu,
            "mem": spec.mem,
            "device_class": spec.device_class,
            "storage_spec": spec.storage_spec,
            "desc": spec.desc,
        }
        for spec in specs
    ]
