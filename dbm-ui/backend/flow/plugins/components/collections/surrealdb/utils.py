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

from typing import Optional

from django.utils.translation import gettext as _

from backend.components import KubernetesApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


def fetch_cluster_detail(service: BaseService, cluster_id: int) -> Optional[dict]:
    """
    获取 k8s 集群详情并做防御性字段校验。

    - 调用 KubernetesApi.cluster_detail 拉取集群详情
    - 校验必需字段: k8sClusterConfig.clusterName / namespace / clusterName
    - 任一环节失败时通过 service.log_error 记录本地化错误信息, 并返回 None
    - 全部校验通过则返回原始 cluster_detail 字典

    :param service: 调用方 Service 实例, 用于输出错误日志
    :param cluster_id: 集群 ID
    :return: 校验通过的 cluster_detail 字典; 失败返回 None
    """
    cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)
    if not cluster_detail or not isinstance(cluster_detail, dict):
        service.log_error(_("集群 {} 不存在, 请检查集群是否存在").format(cluster_id))
        return None

    k8s_cluster_config = cluster_detail.get("k8sClusterConfig") or {}
    k8s_cluster_name = k8s_cluster_config.get("clusterName")
    namespace = cluster_detail.get("namespace")
    cluster_name = cluster_detail.get("clusterName")

    missing_fields = [
        name
        for name, value in [
            ("k8sClusterConfig.clusterName", k8s_cluster_name),
            ("namespace", namespace),
            ("clusterName", cluster_name),
        ]
        if not value
    ]
    if missing_fields:
        service.log_error(_("集群 {} 详情信息不完整, 缺失字段: {}").format(cluster_id, ", ".join(missing_fields)))
        return None

    return cluster_detail
