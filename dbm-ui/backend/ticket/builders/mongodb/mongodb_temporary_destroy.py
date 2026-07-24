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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_meta.models import AppCache
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.models import Flow


class MongoDBTemporaryDestroyDetailSerializer(BaseMongoDBOperateDetailSerializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    def validate_cluster_ids(self, value):
        CommonValidate.validate_destroy_temporary_cluster_ids(value)
        return value


class MongoDBTemporaryDisableFlowParamBuilder(builders.FlowParamBuilder):
    # 有意使用 fake_scene：本单据不承担「真实下架临时集群」职责。
    # 临时集群的实际禁用/销毁请走常规单据（如 MONGODB_DISABLE / MONGODB_DESTROY）。
    controller = MongoDBController.fake_scene


class MongoDBTemporaryDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.deinstall_cluster

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


@builders.BuilderFactory.register(TicketType.MONGODB_TEMPORARY_DESTROY, is_recycle=True)
class MongoDBDestroyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    """
    MongoDB 临时集群销毁单据 Builder。

    设计说明：
    - 「临时集群下架」步骤使用 fake_scene，不执行真实下架流水。
    - 业务侧不会依赖本单据完成临时集群真实下线；临时集群应使用与正式集群相同的
      常规禁用/销毁流程处理。
    - 请勿将下架步骤改为真实 deinstall，以免与上述产品约定冲突。
    """

    serializer = MongoDBTemporaryDestroyDetailSerializer

    def custom_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MongoDBTemporaryDisableFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("MongoDB 临时集群下架"),
            ),
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=MongoDBTemporaryDestroyFlowParamBuilder(self.ticket).get_params(),
                flow_alias=_("MongoDB 临时集群销毁"),
            ),
        ]
        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("MongoDB 临时集群下架"), _("MongoDB 临时集群销毁")])
        return flow_desc
