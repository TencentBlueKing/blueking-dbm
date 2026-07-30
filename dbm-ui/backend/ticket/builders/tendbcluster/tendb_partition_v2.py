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

from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_partition_v2 import (
    MySQLPartitionV2DetailSerializer,
    MySQLPartitionV2ParamBuilder,
)
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder, TendbBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class SpiderPartitionV2DetailSerializer(MySQLPartitionV2DetailSerializer, TendbBaseOperateDetailSerializer):
    pass


class SpiderPartitionV2ParamBuilder(MySQLPartitionV2ParamBuilder):
    controller = MySQLController.mysql_partition_scene_v2

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_PARTITION_V2, iam=ActionEnum.TENDBCLUSTER_PARTITION_MANAGE)
class SpiderPartitionV2FlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderPartitionV2DetailSerializer
    inner_flow_builder = SpiderPartitionV2ParamBuilder
    inner_flow_name = _("分区管理执行v2")
    default_need_itsm = False
    default_need_manual_confirm = False
