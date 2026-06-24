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
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class K8sQdrantSyncTicketIdService(BaseService):
    """
    同步ticket_id给dbs
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 如果是创建单据，可以从trans_data获取cluster_id
        if trans_data.cluster_id is None:
            cluster_id = global_data["cluster_id"]
        else:
            cluster_id = trans_data.cluster_id

        # delete类型的单据从trans_data中取数据
        if global_data["ticket_type"] == TicketType.K8S_QDRANT_DELETE:
            k8s_cluster_name = trans_data.k8s_cluster_name
            namespace = trans_data.namespace
            cluster_name = trans_data.cluster_name
        else:
            cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)
            k8s_cluster_name = cluster_detail["k8sClusterConfig"]["clusterName"]
            namespace = cluster_detail["namespace"]
            cluster_name = cluster_detail["clusterName"]

        params = {
            "k8sClusterName": k8s_cluster_name,
            "namespace": namespace,
            "clusterName": cluster_name,
            "ticketId": global_data["uid"],
            "requestType": self.get_request_type(global_data["ticket_type"]),
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }
        KubernetesApi.update_log_ticket_id(params, use_admin=True)

        return True

    @staticmethod
    def get_request_type(ticket_type: str) -> str:
        if ticket_type == TicketType.K8S_QDRANT_HA_APPLY:
            return "CreateCluster"
        elif ticket_type == TicketType.K8S_QDRANT_ENABLE:
            return "StartCluster"
        elif ticket_type == TicketType.K8S_QDRANT_DISABLE:
            return "StopCluster"
        elif ticket_type == TicketType.K8S_QDRANT_DELETE:
            return "DeleteCluster"
        elif ticket_type == TicketType.K8S_QDRANT_RESTART:
            return "RestartCluster"
        else:
            return "unknown"

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class K8sQdrantSyncTicketIdComponent(Component):
    name = __name__
    code = "k8s_qdrant_sync_ticket_id"
    bound_service = K8sQdrantSyncTicketIdService
