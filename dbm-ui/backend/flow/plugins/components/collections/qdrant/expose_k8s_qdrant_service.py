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


class ExposeK8sQdrantServiceService(BaseService):
    """
    调用dbs接口暴露服务
    """

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")
        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        clb_id = trans_data.clb_id
        params = {
            "name": "qdrant-clb",
            "serviceType": "LoadBalancer",
            "annotations": {"service.kubernetes.io/tke-existed-lbid": clb_id},
            "ports": [6333, 6334],
            "async_to_dbm": False,
            "bk_username": global_data["creator"],
            "k8sClusterName": global_data["k8s_cluster_name"],
            "namespace": trans_data.namespace,
            "clusterName": global_data["cluster_name"],
        }
        KubernetesApi.expose_ports(params)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExposeK8sQdrantServiceComponent(Component):
    name = __name__
    code = "expose_k8s_qdrant_service"
    bound_service = ExposeK8sQdrantServiceService
