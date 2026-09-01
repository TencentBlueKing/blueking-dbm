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

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.qdrant.qdrant_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class DeleteK8sQdrantService(BaseService):
    """
    删除qdrant集群
    """

    def _execute(self, data, parent_data):
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        cluster_id = global_data["cluster_id"]
        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)

        trans_data.cluster_name = cluster_detail["clusterName"]
        trans_data.namespace = cluster_detail["namespace"]
        trans_data.k8s_cluster_name = cluster_detail["k8sClusterConfig"]["clusterName"]

        params = {
            "k8sClusterName": cluster_detail["k8sClusterConfig"]["clusterName"],
            "namespace": cluster_detail["namespace"],
            "clusterName": cluster_detail["clusterName"],
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }
        KubernetesApi.delete_cluster(params, use_admin=True)

        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DeleteK8sQdrantComponent(Component):
    name = __name__
    code = "delete_k8s_qdrant"
    bound_service = DeleteK8sQdrantService
