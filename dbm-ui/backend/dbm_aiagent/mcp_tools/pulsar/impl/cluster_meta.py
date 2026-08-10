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

from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, Machine, Spec, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_biz_by_abbr, get_managed_biz

# Pulsar 的三种角色，broker/bookkeeper/zookeeper
PULSAR_ROLES = {
    "broker": InstanceRole.PULSAR_BROKER.value,
    "bookkeeper": InstanceRole.PULSAR_BOOKKEEPER.value,
    "zookeeper": InstanceRole.PULSAR_ZOOKEEPER.value,
}


def list_my_pulsar_bizs(userID: str) -> List:
    """查询用户负责的Pulsar业务列表"""
    return get_managed_biz(userID, DBType.Pulsar, detailed=True)


def list_biz_by_name(biz_name: str) -> List:
    """根据业务英文名查询业务详情"""
    return get_biz_by_abbr(biz_name, detailed=True)


def pulsar_list_clusters(bk_biz_id: int) -> List:
    """查询业务下的Pulsar集群列表"""
    clusters = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.Pulsar,
    )

    return [
        {
            "cluster_id": c.id,
            "bk_cloud_id": c.bk_cloud_id,
            "cluster_type": c.cluster_type,
            "immute_domain": c.immute_domain,
            "alias": c.alias,
            "region": c.region,
            "broker_count": c.storageinstance_set.filter(instance_role=PULSAR_ROLES["broker"]).count(),
            "bookkeeper_count": c.storageinstance_set.filter(instance_role=PULSAR_ROLES["bookkeeper"]).count(),
            "zookeeper_count": c.storageinstance_set.filter(instance_role=PULSAR_ROLES["zookeeper"]).count(),
            "pulsar_version": c.major_version,
        }
        for c in clusters
    ]


def get_machine_stats(all_machine_ids) -> Dict:
    """统计机器分布信息"""
    machines = Machine.objects.filter(bk_host_id__in=all_machine_ids).select_related("bk_city")

    machine_distribution = {
        "total_count": len(all_machine_ids),
        "by_sub_zone": defaultdict(int),
        "by_os": defaultdict(int),
        "by_device_class": defaultdict(int),
        "spec_summary": defaultdict(int),
    }

    for machine in machines:
        if machine.bk_sub_zone:
            machine_distribution["by_sub_zone"][machine.bk_sub_zone] += 1
        if machine.bk_os_name:
            machine_distribution["by_os"][machine.bk_os_name] += 1
        if machine.bk_svr_device_cls_name:
            machine_distribution["by_device_class"][machine.bk_svr_device_cls_name] += 1
        if machine.spec_id:
            machine_distribution["spec_summary"][f"spec_{machine.spec_id}"] += 1

    return machine_distribution


def get_spec_details(spec_keys: List) -> Dict:
    """获取规格详细信息，spec_keys 形如 ['spec_576']"""
    if not spec_keys:
        return {}

    # 从 spec_keys 中提取 spec_id (spec_576 -> 576)
    spec_ids = []
    for key in spec_keys:
        if key.startswith("spec_"):
            try:
                spec_ids.append(int(key.replace("spec_", "")))
            except ValueError:
                continue

    if not spec_ids:
        return {}

    return {
        spec.spec_id: {
            "spec_id": spec.spec_id,
            "spec_name": spec.spec_name,
            "cpu": spec.cpu,
            "memory": spec.mem,
            "storage_spec": spec.storage_spec,
            "device_class": spec.device_class,
            "desc": spec.desc,
        }
        for spec in Spec.objects.filter(spec_id__in=spec_ids)
    }


def summarize_role_instances(instances: QuerySet) -> Dict:
    """
    汇总某个角色下的实例信息：状态/版本分布、机器分布、规格详情和节点明细。
    Pulsar 有 broker/bookkeeper/zookeeper 三个角色，统一走该函数避免重复逻辑。
    """
    by_status = defaultdict(int)
    versions = set()
    machine_ids = set()

    # 批量查询规格信息，避免逐实例查询
    spec_ids = {ins.machine.spec_id for ins in instances if ins.machine.spec_id}
    specs = {spec.spec_id: spec for spec in Spec.objects.filter(spec_id__in=spec_ids)} if spec_ids else {}

    nodes = []
    for instance in instances:
        by_status[instance.status] += 1
        if instance.version:
            versions.add(instance.version)
        machine_ids.add(instance.machine.bk_host_id)

        # 节点明细，用于缩容/替换操作时定位主机
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
        spec = specs.get(instance.machine.spec_id)
        if spec:
            node_info["spec"] = {
                "spec_id": spec.spec_id,
                "spec_name": spec.spec_name,
                "cpu": spec.cpu,
                "memory": spec.mem,
                "storage_spec": spec.storage_spec,
            }
        nodes.append(node_info)

    machine_stats = get_machine_stats(machine_ids)
    return {
        "node_count": len(nodes),
        "by_status": dict(sorted(by_status.items())),
        "versions": sorted(versions),
        "machine_count": len(machine_ids),
        "by_os": dict(sorted(machine_stats["by_os"].items())),
        "by_sub_zone": dict(sorted(machine_stats["by_sub_zone"].items())),
        "by_device_class": dict(sorted(machine_stats["by_device_class"].items())),
        "by_spec": dict(sorted(machine_stats["spec_summary"].items())),
        "spec_details": get_spec_details(list(machine_stats["spec_summary"].keys())),
        "nodes": nodes,
    }


def cluster_overview(immute_domain: str) -> Dict:
    """查询Pulsar集群详细信息，按 broker/bookkeeper/zookeeper 三个角色分别返回统计信息"""
    try:
        cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)
    except Cluster.DoesNotExist:
        raise serializers.ValidationError(_("集群不存在: {}").format(immute_domain))
    # immute_domain 全局唯一，理论上不会查到非 Pulsar 集群，这里显式校验避免按
    # Pulsar 角色统计时对非 Pulsar 集群静默返回空数据，报错信息更直接
    if cluster_obj.cluster_type != ClusterType.Pulsar.value:
        raise serializers.ValidationError(
            _("集群 {} 不是 Pulsar 类型集群（实际类型: {}）").format(immute_domain, cluster_obj.cluster_type)
        )

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

    storage_instances = StorageInstance.objects.filter(cluster=cluster_obj).select_related(
        "machine", "machine__bk_city"
    )

    for role_name, instance_role in PULSAR_ROLES.items():
        stats[f"{role_name}_instances"] = summarize_role_instances(
            storage_instances.filter(instance_role=instance_role)
        )

    return stats


def search_specs_by_name(spec_name: str, spec_cluster_type: str = ClusterType.Pulsar.value) -> List:
    """根据规格名称模糊查询规格信息

    Args:
        spec_name: 规格名称（支持模糊匹配，如 '16核32G'）
        spec_cluster_type: 规格集群类型，默认为 pulsar

    Returns:
        匹配的规格列表
    """
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
