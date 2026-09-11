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

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_biz_by_abbr, get_managed_biz


def list_my_es_bizs(userID: str) -> List:
    """查询用户负责的 ES 业务列表"""
    return get_managed_biz(userID, DBType.Es, detailed=True)


def list_biz_by_name(biz_name: str) -> List:
    """根据业务英文名查询业务详情"""
    return get_biz_by_abbr(biz_name, detailed=True)


def es_list_clusters(bk_biz_id: int) -> List:
    """查询业务下的 ES 集群列表"""
    clusters = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type=ClusterType.Es,
    )

    return [
        {
            "cluster_id": c.id,
            "bk_cloud_id": c.bk_cloud_id,
            "cluster_type": c.cluster_type,
            "immute_domain": c.immute_domain,
            "alias": c.alias,
            "region": c.region,
            "master_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_MASTER.value)),
            "hot_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_DATANODE_HOT.value)),
            "cold_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_DATANODE_COLD.value)),
            "client_count": len(c.storageinstance_set.filter(instance_role=InstanceRole.ES_CLIENT.value)),
            "es_version": c.major_version,
        }
        for c in clusters
    ]


def _get_machine_stats(all_machine_ids) -> Dict:
    """统计机器分布信息"""
    from backend.db_meta.models import Machine

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


def _get_spec_details(spec_keys: List) -> Dict:
    """获取规格详细信息"""
    from backend.db_meta.models import Spec

    if not spec_keys:
        return {}

    spec_ids = []
    for key in spec_keys:
        if key.startswith("spec_"):
            try:
                spec_ids.append(int(key.replace("spec_", "")))
            except ValueError:
                continue

    if not spec_ids:
        return {}

    specs = Spec.objects.filter(spec_id__in=spec_ids)
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
        for spec in specs
    }


def _build_role_stats(instances, role_label: str) -> Dict:
    """构建单个角色的节点统计信息"""
    role_stats = {
        "by_status": defaultdict(int),
        "versions": set(),
        "machines": set(),
    }
    nodes = []

    spec_ids = set()
    for instance in instances:
        if instance.machine.spec_id:
            spec_ids.add(instance.machine.spec_id)

    specs = {}
    if spec_ids:
        from backend.db_meta.models import Spec

        specs = {spec.spec_id: spec for spec in Spec.objects.filter(spec_id__in=spec_ids)}

    for instance in instances:
        role_stats["by_status"][instance.status] += 1
        if instance.version:
            role_stats["versions"].add(instance.version)
        role_stats["machines"].add(instance.machine.bk_host_id)

        node_info = {
            "ip": instance.machine.ip,
            "bk_host_id": instance.machine.bk_host_id,
            "bk_cloud_id": instance.machine.bk_cloud_id,
            "port": instance.port,
            "instance_id": instance.id,
            "status": instance.status,
            "device_class": instance.machine.bk_svr_device_cls_name,
        }
        if instance.machine.spec_id and instance.machine.spec_id in specs:
            spec = specs[instance.machine.spec_id]
            node_info["spec"] = {
                "spec_id": spec.spec_id,
                "spec_name": spec.spec_name,
                "cpu": spec.cpu,
                "memory": spec.mem,
                "storage_spec": spec.storage_spec,
            }
        nodes.append(node_info)

    machine_stats = _get_machine_stats(role_stats["machines"])
    return {
        "role": role_label,
        "node_count": instances.count(),
        "by_status": dict(sorted(role_stats["by_status"].items())),
        "versions": sorted(list(role_stats["versions"])),
        "machine_count": len(role_stats["machines"]),
        "by_os": dict(sorted(machine_stats["by_os"].items())),
        "by_sub_zone": dict(sorted(machine_stats["by_sub_zone"].items())),
        "by_device_class": dict(sorted(machine_stats["by_device_class"].items())),
        "by_spec": dict(sorted(machine_stats["spec_summary"].items())),
        "spec_details": _get_spec_details(list(machine_stats["spec_summary"].keys())),
        "nodes": nodes,
    }


def cluster_overview(immute_domain: str) -> Dict:
    """查询 ES 集群详细信息，返回统计信息"""
    cluster_obj = Cluster.objects.prefetch_related("tags").get(immute_domain=immute_domain)

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

    # master 节点
    stats["master_instances"] = _build_role_stats(
        storage_instances.filter(instance_role=InstanceRole.ES_MASTER.value), "master"
    )
    # hot 节点
    stats["hot_instances"] = _build_role_stats(
        storage_instances.filter(instance_role=InstanceRole.ES_DATANODE_HOT.value), "hot"
    )
    # cold 节点
    stats["cold_instances"] = _build_role_stats(
        storage_instances.filter(instance_role=InstanceRole.ES_DATANODE_COLD.value), "cold"
    )
    # client 节点
    stats["client_instances"] = _build_role_stats(
        storage_instances.filter(instance_role=InstanceRole.ES_CLIENT.value), "client"
    )

    return stats


def search_specs_by_name(spec_name: str, spec_cluster_type: str = "es") -> List:
    """根据规格名称模糊查询规格信息

    Args:
        spec_name: 规格名称（支持模糊匹配，如 '16核32G'）
        spec_cluster_type: 规格集群类型，默认为 es

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
