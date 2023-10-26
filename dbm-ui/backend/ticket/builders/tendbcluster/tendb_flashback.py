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

from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_flashback import MySQLFlashbackDetailSerializer
from backend.ticket.builders.tendbcluster.base import (
    BaseTendbTicketFlowBuilder,
    TendbBaseOperateDetailSerializer,
    TendbBasePauseParamBuilder,
)
from backend.ticket.constants import FlowRetryType, TicketType


class TendbFlashbackDetailSerializer(MySQLFlashbackDetailSerializer, TendbBaseOperateDetailSerializer):
    def validate(self, attrs):
        # 校验闪回时间
        super().validate_flash_time(attrs)
        # 校验集群是否可用
        super(TendbBaseOperateDetailSerializer, self).validate_cluster_can_access(attrs)
        # 校验flash的库表选择器
        RemoteServiceHandler(bk_biz_id=self.context["bk_biz_id"]).check_flashback_database(attrs["infos"])

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
    pause_node_builder = TendbBasePauseParamBuilder

    @property
    def need_manual_confirm(self):
        return True
