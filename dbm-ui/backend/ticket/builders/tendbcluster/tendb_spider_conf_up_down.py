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
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateResourceParamBuilder
from backend.ticket.builders.tendbcluster.tendb_spider_switch_nodes import SpiderSwitchNodesDetailSerializer
from backend.ticket.constants import TicketType


class SpiderConfUpDownDetailSerializer(SpiderSwitchNodesDetailSerializer):
    pass


class SpiderConfUpDownFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_nodes_change_spec_scene


class TendbSpiderConfUpDownResourceParamBuilder(TendbBaseOperateResourceParamBuilder):
    def format(self):
        infos = self.ticket_data["infos"]
        cluster_ids = fetch_cluster_ids(infos)
        cluster_map = Cluster.objects.in_bulk(cluster_ids)
        for info in infos:
            self.patch_common_affinity(
                info,
                role=info["switch_spider_role"],
                cluster=cluster_map[info["cluster_id"]],
                exclusive_hosts=[],
                tolerance=0.5,
                no_need_affinity=info["switch_spider_role"] == TenDBClusterSpiderRole.SPIDER_SLAVE,
            )

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        for info in next_flow.details["ticket_data"]["infos"]:
            # 格式化规格信息
            role = info["switch_spider_role"]
            info["spider_new_ip_list"] = info.pop(role)

        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(
    TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN, is_recycle=True, iam=ActionEnum.TENDBCLUSTER_MANAGE
)
class SpiderConfUpDownFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderConfUpDownDetailSerializer
    inner_flow_builder = SpiderConfUpDownFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 接入层升降配")
    need_patch_recycle_host_details = True
    resource_batch_apply_builder = TendbSpiderConfUpDownResourceParamBuilder
    validator = SpiderController.tendbcluster_nodes_change_spec_scene.validator
