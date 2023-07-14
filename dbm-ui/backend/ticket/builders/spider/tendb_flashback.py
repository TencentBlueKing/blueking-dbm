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
from backend.ticket.builders.mysql.mysql_flashback import MySQLFlashbackDetailSerializer
from backend.ticket.builders.spider.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class TendbFlashbackDetailSerializer(MySQLFlashbackDetailSerializer):
    def validate(self, attrs):
        super().validate(attrs)
        return attrs


class TendbFlashbackFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.flashback

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_FLASHBACK)
class TendbFlashbackFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbFlashbackDetailSerializer
    inner_flow_builder = TendbFlashbackFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 闪回执行")
    retry_type = FlowRetryType.MANUAL_RETRY
