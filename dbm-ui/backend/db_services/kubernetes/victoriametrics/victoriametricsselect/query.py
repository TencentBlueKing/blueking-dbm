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
from backend.db_meta.api.cluster.k8s_vm.victoriametricsselect.detail import scan_cluster
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.kubernetes.victoriametrics.query import VictoriaMetricsBaseListRetrieveResource
from backend.flow.utils.k8s_db.vm.consts import COMPONENT_VMSELECT
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


@register_resource_decorator()
class VictoriaMetricsSelectListRetrieveResource(VictoriaMetricsBaseListRetrieveResource):
    cluster_types = [ClusterType.K8sVictoriametricsSelect]
    instance_roles = [InstanceRole.VM_SELECT]
    fields = [
        *VictoriaMetricsBaseListRetrieveResource.fields,
    ]

    @classmethod
    def _to_cluster_representation(cls, cluster: Cluster, *args, **kwargs) -> dict:
        cluster_info = super()._to_cluster_representation(cluster, *args, **kwargs)
        # 查询集群无 vminsert 组件，无写入口
        cluster_info["write_entry"] = ""
        # 外部 vmstorage 节点地址仅在部署参数中，从部署单据反查
        cluster_info["storage_nodes"] = cls._get_storage_nodes(cluster)
        return cluster_info

    @classmethod
    def _get_storage_nodes(cls, cluster: Cluster) -> list:
        """从部署单据反查 vmselect 挂载的外部 vmstorage 节点地址列表"""
        ticket = (
            Ticket.objects.filter(
                bk_biz_id=cluster.bk_biz_id,
                ticket_type=TicketType.K8S_VICTORIAMETRICS_SELECT_APPLY,
                details__cluster_name=cluster.name,
            )
            .order_by("-id")
            .first()
        )
        if not ticket:
            return []
        for component in ticket.details.get("component_list") or []:
            if component.get("component_name") != COMPONENT_VMSELECT:
                continue
            storage_node = ((component.get("env") or {}).get("EXTRA_ARGS") or {}).get("storageNode") or ""
            return [node.strip() for node in storage_node.split(",") if node.strip()]
        return []

    @classmethod
    def get_topo_graph(
        cls, bk_biz_id: int, cluster_id: int, bcs_cluster_name: str = None, namespace: str = None
    ) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        return scan_cluster(cluster, bcs_cluster_name, namespace, cls._get_storage_nodes(cluster)).to_dict()
