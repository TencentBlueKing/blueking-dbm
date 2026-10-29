# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Doris 集群元数据查询实现。

设计边界：本模块只查询平台元数据（db_meta），不涉及任何监控指标。
集群的使用量与水位信息由 doris-metrics 的指标工具提供，两者职责分离，
因此这里严禁引入 BKMonitorV3Api / execute_promql 等监控相关模块。
"""
import logging
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from django.db.models import Count
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, Spec, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_biz_by_abbr, get_managed_biz
from backend.dbm_aiagent.mcp_tools.doris.enums import BE_ROLES, FE_ROLES
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpClusterNotFoundException

logger = logging.getLogger("root")

# 节点角色的中文名，取自 InstanceRole 枚举的 label
_ROLE_ALIAS_MAP = dict(InstanceRole.get_choices())


def list_my_doris_bizs(username: str) -> List[Dict]:
    """查询当前用户作为主负责人管理的 Doris 业务列表。

    未提供 bk_biz_id 时应先调用此接口获取可用业务。

    @param username: 用户名
    @return: [{bk_biz_id, app_name, abbr}]
    """
    try:
        return get_managed_biz(username, DBType.Doris, detailed=True)
    except ValueError:
        # get_managed_biz 在无管理业务时抛裸 ValueError，转为可读提示并给出下一步
        raise DBMMcpBaseException(msg=_("用户 {} 不是任何 Doris 业务的主负责人，请改用业务英文名查询业务，或直接提供 bk_biz_id").format(username))


def list_biz_by_name(biz_name: str) -> List[Dict]:
    """根据业务英文名（模糊匹配）查询业务详情。

    用户提供了业务名称但未提供 bk_biz_id 时，用此接口将名称转换为 bk_biz_id。

    @param biz_name: 业务英文名
    @return: [{bk_biz_id, app_name, abbr}]
    """
    return get_biz_by_abbr(biz_name, detailed=True)


def doris_list_clusters(bk_biz_id: int) -> List[Dict]:
    """查询指定业务下的 Doris 集群列表。

    各角色节点数通过一次 (cluster, instance_role) 聚合计数得到，
    避免对每个集群逐一发起查询造成 N+1。

    @param bk_biz_id: 业务 ID
    @return: 集群列表，每项含基本属性与按角色的节点数
    """
    clusters = list(Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=ClusterType.Doris))
    if not clusters:
        return []

    # 一次聚合拿到所有集群各角色的节点数
    role_counts: Dict[int, Dict[str, int]] = defaultdict(dict)
    counted = (
        StorageInstance.objects.filter(cluster__in=clusters)
        .values("cluster__id", "instance_role")
        .annotate(node_count=Count("id"))
    )
    for row in counted:
        # 聚合结果天然不含计数为 0 的角色，无需额外过滤
        role_counts[row["cluster__id"]][row["instance_role"]] = row["node_count"]

    return [
        {
            "cluster_id": cluster.id,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_domain": cluster.immute_domain,
            "alias": cluster.alias,
            "region": cluster.region,
            "major_version": cluster.major_version,
            # 未部署的角色不会出现在此字典中
            "role_node_counts": dict(sorted(role_counts.get(cluster.id, {}).items())),
        }
        for cluster in clusters
    ]


def validate_doris_cluster(cluster_domain: str) -> Cluster:
    """校验集群存在且为 Doris 集群。

    区分「域名不存在」与「域名存在但不是 Doris 集群」两种情形，
    后者若静默放过会返回语义完全不同的其他组件元数据。

    @param cluster_domain: 集群访问域名（immute_domain）
    @return: 集群对象
    """
    cluster = (
        Cluster.objects.prefetch_related("tags")
        .filter(immute_domain=cluster_domain, cluster_type=ClusterType.Doris)
        .first()
    )
    if not cluster:
        exist_cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
        if exist_cluster:
            raise DBMMcpClusterNotFoundException(
                msg=_("集群 {} 的类型是 {}，不是 Doris 集群，无法使用 Doris 元数据工具查询").format(
                    cluster_domain, exist_cluster.cluster_type
                )
            )
        raise DBMMcpClusterNotFoundException(msg=_("Doris 集群 {} 未找到").format(cluster_domain))
    return cluster


def _collect_spec_details(spec_ids: Iterable[int]) -> Dict[int, Dict]:
    """批量查询规格详情，以 int 型 spec_id 为键。

    @param spec_ids: 规格 ID 集合
    @return: {spec_id: 规格详情}
    """
    valid_ids = {spec_id for spec_id in spec_ids if spec_id}
    if not valid_ids:
        return {}

    return {
        spec.spec_id: {
            "spec_id": spec.spec_id,
            "spec_name": spec.spec_name,
            "cpu": spec.cpu,
            "mem": spec.mem,
            "storage_spec": spec.storage_spec,
            "device_class": spec.device_class,
            "desc": spec.desc,
        }
        for spec in Spec.objects.filter(spec_id__in=valid_ids)
    }


def _role_layer(instance_role: str) -> str:
    """判断角色所属层：FE 或 BE。"""
    if instance_role in FE_ROLES:
        return "fe"
    if instance_role in BE_ROLES:
        return "be"
    return "unknown"


def build_role_stats(instances: Iterable[StorageInstance], spec_details: Dict[int, Dict]) -> Dict[str, Dict]:
    """按 instance_role 分组统计节点数量与规格分布。

    必须以 instance_role 而非 machine_type 分组：Doris 的 BE 热/温/冷三个角色
    共用同一个 machine_type（doris_backend），用 machine_type 分组会把三类节点
    混成一桶，丢失冷热分层信息。

    节点数为 0 的角色不会出现在结果中 —— 实际未部署的 Observer 与温节点
    不应占据输出空间。由于本函数按实际实例分桶，零节点角色天然不产生分组。

    @param instances: 集群的存储实例集合（需已 select_related("machine")）
    @param spec_details: 规格详情映射，由 _collect_spec_details 提供
    @return: {instance_role: 该角色的统计}
    """
    buckets: Dict[str, Dict] = {}

    for instance in instances:
        role = instance.instance_role
        bucket = buckets.setdefault(
            role,
            {
                "node_count": 0,
                "machines": set(),
                "by_status": defaultdict(int),
                "versions": set(),
                "by_spec": defaultdict(int),
                "by_os": defaultdict(int),
                "by_sub_zone": defaultdict(int),
                "by_device_class": defaultdict(int),
            },
        )

        bucket["node_count"] += 1
        bucket["by_status"][instance.status] += 1
        if instance.version:
            bucket["versions"].add(instance.version)

        machine = instance.machine
        # 同一台机器可能承载多个实例，机器维度的统计需按 bk_host_id 去重
        if machine.bk_host_id not in bucket["machines"]:
            bucket["machines"].add(machine.bk_host_id)
            if machine.spec_id:
                bucket["by_spec"][machine.spec_id] += 1
            if machine.bk_os_name:
                bucket["by_os"][machine.bk_os_name] += 1
            if machine.bk_sub_zone:
                bucket["by_sub_zone"][machine.bk_sub_zone] += 1
            if machine.bk_svr_device_cls_name:
                bucket["by_device_class"][machine.bk_svr_device_cls_name] += 1

    role_stats: Dict[str, Dict] = {}
    for role, bucket in buckets.items():
        role_spec_ids = list(bucket["by_spec"].keys())
        role_stats[role] = {
            "role_alias": str(_ROLE_ALIAS_MAP.get(role, role)),
            "layer": _role_layer(role),
            "node_count": bucket["node_count"],
            "machine_count": len(bucket["machines"]),
            "by_status": dict(sorted(bucket["by_status"].items())),
            "versions": sorted(bucket["versions"]),
            "by_spec": dict(sorted(bucket["by_spec"].items())),
            "spec_details": {spec_id: spec_details[spec_id] for spec_id in role_spec_ids if spec_id in spec_details},
            "by_os": dict(sorted(bucket["by_os"].items())),
            "by_sub_zone": dict(sorted(bucket["by_sub_zone"].items())),
            "by_device_class": dict(sorted(bucket["by_device_class"].items())),
        }

    return dict(sorted(role_stats.items()))


def build_layer_summary(instances: Iterable[StorageInstance]) -> Dict[str, int]:
    """按 FE / BE 两层汇总节点数与机器数，便于快速判断集群规模。

    机器数按 bk_host_id 去重；同一台机器若同时承载 FE 与 BE 实例，
    会分别计入两层，total_machine_count 则按全集群去重。

    @param instances: 集群的存储实例集合
    @return: 各层与总计的节点数、机器数
    """
    layer_nodes: Dict[str, int] = defaultdict(int)
    layer_machines: Dict[str, set] = defaultdict(set)
    all_machines = set()

    for instance in instances:
        layer = _role_layer(instance.instance_role)
        layer_nodes[layer] += 1
        layer_machines[layer].add(instance.machine.bk_host_id)
        all_machines.add(instance.machine.bk_host_id)

    return {
        "fe_node_count": layer_nodes.get("fe", 0),
        "fe_machine_count": len(layer_machines.get("fe", set())),
        "be_node_count": layer_nodes.get("be", 0),
        "be_machine_count": len(layer_machines.get("be", set())),
        "total_node_count": sum(layer_nodes.values()),
        "total_machine_count": len(all_machines),
    }


def cluster_overview(cluster_domain: str) -> Dict:
    """查询 Doris 集群概览：基本属性 + 按角色的节点数量与规格统计。

    只返回统计信息，不返回逐节点清单（IP / 端口等），以控制返回体积。
    需要节点级信息或使用量时，分别使用元数据明细接口与 doris-metrics 指标工具。

    查询次数固定：集群（含 tags）1 次 + 实例 1 次 + 规格 1 次 + 访问入口 1 次，
    不随节点规模增长。

    @param cluster_domain: 集群访问域名
    @return: 集群概览
    """
    cluster = validate_doris_cluster(cluster_domain)

    # Doris 的 FE 与 BE 均登记为存储实例，无需查询 ProxyInstance
    instances = list(StorageInstance.objects.filter(cluster=cluster).select_related("machine"))

    spec_details = _collect_spec_details({instance.machine.spec_id for instance in instances})
    role_stats = build_role_stats(instances, spec_details)

    logger.info(
        "doris cluster_overview cluster=%s instance_count=%s role_count=%s",
        cluster_domain,
        len(instances),
        len(role_stats),
    )

    return {
        "cluster_id": cluster.id,
        "bk_biz_id": cluster.bk_biz_id,
        "bk_cloud_id": cluster.bk_cloud_id,
        "cluster_domain": cluster.immute_domain,
        "alias": cluster.alias,
        "cluster_type": cluster.cluster_type,
        "major_version": cluster.major_version,
        "phase": cluster.phase,
        "region": cluster.region,
        "disaster_tolerance_level": cluster.disaster_tolerance_level,
        "tags": ["{}:{}".format(tag.key, tag.value) for tag in cluster.tags.all()],
        "cluster_entries": [
            {"entry_type": entry.cluster_entry_type, "entry_addr": entry.entry}
            for entry in ClusterEntry.objects.filter(cluster=cluster)
        ],
        # 仅包含实际存在节点的角色，未部署的角色不会出现
        "roles": role_stats,
        "summary": build_layer_summary(instances),
    }


def search_doris_specs_by_name(spec_name: str, spec_cluster_type: Optional[str] = None) -> List[Dict]:
    """根据规格名称模糊查询 Doris 规格信息。

    @param spec_name: 规格名称，支持模糊匹配，如 "16核32G"
    @param spec_cluster_type: 规格集群类型，默认为 Doris
    @return: 匹配的规格列表，无匹配时返回空列表
    """
    specs = Spec.objects.filter(
        spec_name__icontains=spec_name,
        spec_cluster_type=spec_cluster_type or DBType.Doris.value,
        enable=True,
    )

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
