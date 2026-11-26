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

from typing import Dict, Mapping, Optional, Sequence, Union

from backend.db_meta.api.db_module.version import get_modules_layer_versions, layer_component, resolve_layer_versions
from backend.db_meta.dataclass import DBModuleComponentVersion, LayerVersion, VersionInfo
from backend.db_meta.enums import module_component_types
from backend.db_meta.models import Cluster, DBModule, ProxyInstance, StorageInstance
from backend.db_package.models import Package

# ---------- 通用：集群所属模块的版本，所有集群类型都适用 ----------


def get_clusters_module_versions(clusters: Sequence[Cluster]) -> Dict[int, Dict[str, LayerVersion]]:
    """批量取集群所属模块当前绑定的版本。

    返回 {集群ID: {组件名: LayerVersion}}。模块之后改过版本时，这里拿到的是改后的版本。
    模块不存在或没设置版本的集群对应空字典。
    """
    modules = DBModule.objects.in_bulk({cluster.db_module_id for cluster in clusters})
    module_versions = get_modules_layer_versions(list(modules.values()))
    return {cluster.id: module_versions.get(cluster.db_module_id, {}) for cluster in clusters}


def get_cluster_module_versions(cluster: Cluster) -> Dict[str, LayerVersion]:
    """单个集群所属模块当前绑定的版本，规则同 get_clusters_module_versions。"""
    return get_clusters_module_versions([cluster])[cluster.id]


def get_cluster_module_layer_version(cluster: Cluster, access_layer: str) -> Optional[LayerVersion]:
    """集群所属模块某一层（AccessLayer.STORAGE / AccessLayer.PROXY）当前绑定的版本，没设置版本时返回 None。"""
    return _pick_layer([cluster], get_clusters_module_versions([cluster]), access_layer)[cluster.id]


# ---------- MySQL 专用：集群部署时的版本，优先取部署快照 ----------


def get_mysql_clusters_versions(clusters: Sequence[Cluster]) -> Dict[int, Dict[str, LayerVersion]]:
    """批量取 MySQL 集群部署时的版本。

    返回 {集群ID: {组件名: LayerVersion}}。
    集群有部署快照 apply_snapshot 时按快照，没有时按所属模块当前绑定的版本，都没有时对应空字典。
    LayerVersion.source 标明了来自快照（snapshot）还是模块（module）。
    """
    snapshot_clusters = [cluster for cluster in clusters if cluster.apply_snapshot]
    module_clusters = [cluster for cluster in clusters if not cluster.apply_snapshot]

    snapshot_bindings = {cluster.id: _mysql_snapshot_bindings(cluster) for cluster in snapshot_clusters}
    return {
        **get_clusters_module_versions(module_clusters),
        **resolve_layer_versions(snapshot_bindings, "snapshot"),
    }


def get_mysql_cluster_versions(cluster: Cluster) -> Dict[str, LayerVersion]:
    """单个 MySQL 集群部署时的版本，规则同 get_mysql_clusters_versions。"""
    return get_mysql_clusters_versions([cluster])[cluster.id]


def get_mysql_clusters_os_version(clusters: Sequence[Cluster], access_layer: str) -> Dict[int, Optional[LayerVersion]]:
    """批量取 MySQL 集群某一层部署时的版本和操作系统约束，规则同 get_mysql_clusters_versions。

    返回 {集群ID: LayerVersion}，这一层没有版本时为 None。
    操作系统看 binding.permit_os_type 和 effective_permit_os。
    """
    return _pick_layer(clusters, get_mysql_clusters_versions(clusters), access_layer)


def get_mysql_cluster_os_version(cluster: Cluster, access_layer: str) -> Optional[LayerVersion]:
    """单个 MySQL 集群某一层部署时的版本和操作系统约束，规则同 get_mysql_clusters_os_version。"""
    return get_mysql_clusters_os_version([cluster], access_layer)[cluster.id]


# ---------- 实例 ----------


def get_instances_version(
    instances: Sequence[Union[StorageInstance, ProxyInstance]]
) -> Dict[int, Optional[VersionInfo]]:
    """批量取实例安装的版本。

    返回 {实例ID: VersionInfo}，版本取自实例 db_package 关联的版本。
    db_package 为空（存量实例）或介质包没关联版本时为 None。
    同一批只传一种实例（存储实例或代理实例），两张表的 ID 会重复。
    """
    packages = Package.objects.select_related("db_version__version_series").in_bulk(
        {instance.db_package_id for instance in instances if instance.db_package_id}
    )

    result = {}
    for instance in instances:
        package = packages.get(instance.db_package_id)
        db_version = package.db_version if package else None
        result[instance.id] = VersionInfo.from_db_version(db_version) if db_version else None
    return result


def get_instance_version(instance: Union[StorageInstance, ProxyInstance]) -> Optional[VersionInfo]:
    """单个实例安装的版本，规则同 get_instances_version。"""
    return get_instances_version([instance])[instance.id]


def _pick_layer(
    clusters: Sequence[Cluster], versions: Mapping[int, Mapping[str, LayerVersion]], access_layer: str
) -> Dict[int, Optional[LayerVersion]]:
    """从 {集群ID: {组件名: LayerVersion}} 里取出每个集群某一层的版本。"""
    return {
        cluster.id: versions[cluster.id].get(layer_component(cluster.cluster_type, access_layer))
        for cluster in clusters
    }


def _mysql_snapshot_bindings(cluster: Cluster) -> Dict[str, DBModuleComponentVersion]:
    """MySQL 的部署快照与模块的 current_db_version_info_dict 结构一致。"""
    snapshot = cluster.apply_snapshot
    return {
        component: DBModuleComponentVersion.from_dict(snapshot[component])
        for component in module_component_types(cluster.cluster_type)
        if snapshot.get(component)
    }
