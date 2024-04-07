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

from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_ha_rename import MySQLHaRenameFlowParamBuilder, MySQLHaRenameSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class TendbRenameSerializer(MySQLHaRenameSerializer):
    pass


class TendbRenameFlowParamBuilder(MySQLHaRenameFlowParamBuilder):
    controller = SpiderController.rename_database

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_RENAME_DATABASE)
class MySQLHaRenameFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbRenameSerializer
    inner_flow_builder = TendbRenameFlowParamBuilder
    inner_flow_name = _("TenDBCluster Cluster 重命名执行")
    retry_type = FlowRetryType.MANUAL_RETRY
