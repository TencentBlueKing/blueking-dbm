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
from backend.flow.utils.k8s_db.surrealdb.consts import NAMESPACE_PREFIX
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import SurrealDBTicketFlowBuilderPatchMixin


class BaseSurrealDBTicketFlowBuilder(SurrealDBTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.K8sSurrealdb.value
    cluster_types = [ClusterType.K8sSurrealdbHa.value, ClusterType.K8sSurrealdbSingle.value]

    operation_type = None
    enable_operation_log = True

    @classmethod
    def add_operation_log(cls, ticket, operation_type=None):
        """添加 DBS 操作日志"""
        op_type = operation_type or cls.operation_type
        if not op_type:
            return
        clusters = ticket.details.get("clusters", {})
        if not clusters:
            return

        cluster_detail = KubernetesApi.cluster_detail({"cluster_id": ticket.details["cluster_id"]}, use_admin=True)
        name_space = cluster_detail.get("namespace")
        k8s_cluster_name = cluster_detail.get("k8sClusterConfig", {}).get("clusterName", "")

        for cluster_id, cluster_info in clusters.items():
            data = {
                "ticketId": ticket.id,
                "clusterName": cluster_info.get("name"),
                "k8sClusterName": k8s_cluster_name,
                "nameSpace": name_space,
                "requestType": op_type,
                "bk_username": ticket.creator,
            }
            KubernetesApi.add_operation_log(data, use_admin=True)

    @classmethod
    def add_apply_operation_log(cls, ticket, operation_type):
        """添加 SurrealDB 部署类单据的 DBS 操作日志"""
        name_space = f"{NAMESPACE_PREFIX}-{ticket.details['db_app_abbr']}-{ticket.bk_biz_id}"
        data = {
            "ticketId": ticket.id,
            "clusterName": ticket.details["cluster_name"],
            "k8sClusterName": ticket.details["k8s_cluster_name"],
            "nameSpace": name_space,
            "requestType": operation_type,
            "bk_username": ticket.creator,
        }
        KubernetesApi.add_operation_log(data, use_admin=True)

    def patch_ticket_detail(self):
        """补充单据详情并添加 DBS 操作日志"""
        super().patch_ticket_detail()
        if self.enable_operation_log:
            self.add_operation_log(self.ticket)
