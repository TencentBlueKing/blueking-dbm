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

# ============================== 版本信息对外接口 ==============================
# 读取模块 / 集群 / 实例的版本信息请只用下面导出的函数，不要直接读这些字段：
#   DBModule.current_db_version_info_dict、Cluster.apply_snapshot、StorageInstance / ProxyInstance.db_package
# 字段结构、快照优先、操作系统跟随介质包等规则都封装在函数里。
#
# 目前只有 TenDBSingle、TenDBHA、TenDBCluster 接入了模块版本，其他集群类型的结果都是空字典 / None。
# 带 s 的是批量版本，一批数据里版本和介质包各只查一次，处理多条数据时优先用批量版本。
#
# ---------- 返回对象（backend.db_meta.dataclass）----------
# LayerVersion：一层组件的版本
#   component            组件名：tendbsingle 是 single，tendbha 是 backend / proxy，tendbcluster 是 remote / spider
#   binding              模块或快照上保存的原始绑定 DBModuleComponentVersion：db_version_id、permit_os_type、permit_os
#   effective_permit_os  实际生效的操作系统列表。[] 表示不限制；跟随介质包但查不到同类型的已启用介质包时为 None
#   version              绑定的版本 VersionInfo，版本已被删除时为 None
#   source               "module" 表示来自模块，"snapshot" 表示来自集群部署快照
# VersionInfo：一个具体版本
#   db_version_id、full_version（六段式，如 8.0.32.0.0.11）、version_series（系列名，如 MySQL-8.0）、
#   version_name、distribution（发行版名）
#
# ---------- 模块 ----------
# get_modules_layer_versions(modules)            -> {模块ID: {组件名: LayerVersion}}
# get_module_versions(module)                    -> {组件名: LayerVersion}
# get_module_layer_version(module, access_layer) -> 这一层的 LayerVersion，没设置版本时为 None
#
# ---------- 集群（通用）----------
# 集群所属模块当前绑定的版本，所有集群类型都适用，不看部署快照；模块改过版本后结果跟着变
# get_clusters_module_versions(clusters)            -> {集群ID: {组件名: LayerVersion}}
# get_cluster_module_versions(cluster)              -> {组件名: LayerVersion}
# get_cluster_module_layer_version(cluster, layer)  -> 这一层的 LayerVersion 或 None
#
# ---------- 集群（MySQL 专用）----------
# MySQL 集群部署时的版本：有部署快照 apply_snapshot 时按快照，没有时按所属模块
# get_mysql_clusters_versions(clusters)             -> {集群ID: {组件名: LayerVersion}}
# get_mysql_cluster_versions(cluster)               -> {组件名: LayerVersion}
# get_mysql_clusters_os_version(clusters, layer)    -> {集群ID: 这一层的 LayerVersion 或 None}
# get_mysql_cluster_os_version(cluster, layer)      -> 这一层的 LayerVersion 或 None
#
# ---------- 实例 ----------
# 实例实际安装的版本，来自实例的 db_package；存量实例没有 db_package 时为 None
# get_instances_version(instances)               -> {实例ID: VersionInfo 或 None}，同一批只传一种实例
# get_instance_version(instance)                 -> VersionInfo 或 None
#
# 参数里的 access_layer / layer 取 AccessLayer.STORAGE 或 AccessLayer.PROXY。
# =============================================================================
from .apis import *
from .cluster_version import (
    get_cluster_module_layer_version,
    get_cluster_module_versions,
    get_clusters_module_versions,
    get_instance_version,
    get_instances_version,
    get_mysql_cluster_os_version,
    get_mysql_cluster_versions,
    get_mysql_clusters_os_version,
    get_mysql_clusters_versions,
)
from .version import get_module_layer_version, get_module_versions, get_modules_layer_versions
