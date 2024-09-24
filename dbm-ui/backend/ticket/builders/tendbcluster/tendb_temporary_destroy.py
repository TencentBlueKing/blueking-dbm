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

from django.utils.translation import ugettext as _

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate, HostRecycleSerializer
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbClustersTakeDownDetailsSerializer,
)
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow


class TendbTemporaryDestroyDetailSerializer(TendbClustersTakeDownDetailsSerializer):
    ip_recycle = HostRecycleSerializer(help_text=_("主机回收信息"), default=HostRecycleSerializer.DEFAULT)

    def validate_cluster_ids(self, value):
        CommonValidate.validate_destroy_temporary_cluster_ids(value)
        return value


class TendbTemporaryDisableFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_disable_scene


class TendbTemporaryDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_destroy_scene


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_TEMPORARY_DESTROY, is_recycle=True)
class TendbDestroyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbTemporaryDestroyDetailSerializer
    need_patch_recycle_cluster_details = True

    def custom_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbTemporaryDisableFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 临时集群下架"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=TendbTemporaryDestroyFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("TenDBCluster 临时集群销毁"),
            ),
        ]
        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("TenDBCluster 临时集群下架"), _("TenDBCluster 临时集群销毁")])
        return flow_desc
