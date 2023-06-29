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
import copy
import logging
from typing import List

from django.db.models import Q
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class GetRiakClusterNodeService(BaseService):
    """
    根据Riak单据获取集群中的节点
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        cluster = Cluster.objects.get(id=global_data["cluster_id"])

        # 集群下架获取集群中所有的节点
        if global_data["ticket_type"] == TicketType.RIAK_CLUSTER_DESTROY:
            storages = StorageInstance.objects.filter(cluster=cluster).all()
            trans_data.nodes = list(set([storage.machine.ip for storage in storages]))
            self.log_info(_("获取集群所有节点成功。{}").format(trans_data))
            data.outputs["trans_data"] = trans_data
            return True

        query_filters = Q(cluster=cluster, status=InstanceStatus.RUNNING.value)
        storages = StorageInstance.objects.filter(query_filters).all()

        # 集群扩容，base_node为集群中running的节点
        if global_data["ticket_type"] in TicketType.RIAK_CLUSTER_SCALE_OUT:
            base_node = storages[0].machine.ip
            trans_data.base_node = base_node
        # 集群缩容，base_node为集群中running的节点，并且不能为待剔除的节点
        elif global_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN:
            scale_in_nodes = [node["ip"] for node in global_data["nodes"]]
            running_nodes = list(
                set([storage.machine.ip for storage in storages if storage.machine.ip not in scale_in_nodes])
            )
            if len(running_nodes) < 2:
                self.log_error("exclude scale in nodes, number of running nodes less than 2")
            base_node = running_nodes[0]
            trans_data.base_node = base_node

        if (
            global_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_OUT
            or global_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN
        ):
            trans_data.nodes = copy.deepcopy(trans_data.operate_nodes)
            trans_data.nodes.append(base_node)

        self.log_info(_("获取集群中running节点成功。{}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
            Service.InputItem(name="trans_data", key="trans_data", type="dict", required=True),
        ]


class GetRiakClusterNodeComponent(Component):
    name = __name__
    code = "get_riak_cluster_node"
    bound_service = GetRiakClusterNodeService
