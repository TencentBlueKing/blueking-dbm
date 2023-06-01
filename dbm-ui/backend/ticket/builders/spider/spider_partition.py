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

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.builders.mysql.mysql_partition import MySQLPartitionDetailSerializer, MySQLPartitionParamBuilder
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class SpiderPartitionDetailSerializer(MySQLPartitionDetailSerializer):
    pass


class SpiderPartitionParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_partition

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.SPIDER_PARTITION)
class SpiderPartitionFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = SpiderPartitionDetailSerializer
    inner_flow_builder = SpiderPartitionParamBuilder
    inner_flow_name = _("分区管理执行")

    @property
    def need_itsm(self):
        # TODO：先不考虑执行的分区审批
        return False
