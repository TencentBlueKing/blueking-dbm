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

from backend.components.kubernetes.client import KubernetesApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import SurrealDBTicketFlowBuilderPatchMixin


class BaseQdrantTicketFlowBuilder(SurrealDBTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.K8sQdrant.value
    cluster_types = [ClusterType.K8sQdrantHa.value]

    # 子类需要指定对应的操作类型
    operation_type = None

    # 是否由基类的 patch_ticket_detail 自动补充操作日志。
    # 例如 apply 场景需要自行写入操作日志(operation_type 不同)，故置为 False 避免重复记录。
    enable_operation_log = True

    @classmethod
    def add_operation_log(cls, ticket, operation_type=None):
        """添加操作日志的通用方法

        Args:
            ticket: 单据对象
            operation_type: 操作类型，如果不指定则使用类属性 operation_type
        """
        # Todo: 后期操作记录全部由dba或dbm记录
        op_type = operation_type or cls.operation_type
        if not op_type:
            return
        clusters = ticket.details.get("clusters", {})
        if not clusters:
            return
        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": ticket.details["cluster_id"]}, use_admin=True)
        name_space = cluster_detail.get("namespace")
        k8s_cluster_name = cluster_detail.get("k8sClusterConfig", {}).get("clusterName", "")

        for cluster_id, cluster_info in ticket.details["clusters"].items():
            cluster_name = cluster_info.get("name")
            data = {
                "ticketId": ticket.id,
                "clusterName": cluster_name,
                "k8sClusterName": k8s_cluster_name,
                "nameSpace": name_space,
                "requestType": op_type,
                "bk_username": ticket.creator,
            }
            KubernetesApi.add_operation_log(data, use_admin=True)

    def patch_ticket_detail(self):
        """补充单据详情并添加操作日志"""
        super().patch_ticket_detail()
        # 仅当子类开启时才由基类统一写操作日志，避免与子类自行写的日志重复
        if self.enable_operation_log:
            self.add_operation_log(self.ticket)
