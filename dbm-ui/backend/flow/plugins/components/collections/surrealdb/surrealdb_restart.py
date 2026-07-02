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

import logging.config
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components import KubernetesApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class RestartSurrealDBService(BaseService):
    """
    调用dbs创建接口重启 surrealdb 集群
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        cluster_id = global_data["cluster_id"]
        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)
        if not cluster_detail or not isinstance(cluster_detail, dict):
            self.log_error(_("集群 {} 不存在, 请检查集群是否存在").format(cluster_id))
            return False

        # 防御性校验必需字段, 避免 API 返回结构不完整时抛出 KeyError
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
            self.log_error(_("集群 {} 详情信息不完整, 缺失字段: {}").format(cluster_id, ", ".join(missing_fields)))
            return False

        params = {
            "k8sClusterName": k8s_cluster_name,
            "namespace": namespace,
            "clusterName": cluster_name,
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }
        KubernetesApi.restart_cluster(params, use_admin=True)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RestartSurrealDBComponent(Component):
    name = __name__
    code = "restart_surrealdb"
    bound_service = RestartSurrealDBService
