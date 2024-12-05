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
# 此单据用于各种线上的后台流程测试，可以保留

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MySQLFakeDetailSerializer(MySQLBaseOperateDetailSerializer):
    params = serializers.JSONField(help_text=_("测试参数"))


class MySQLFakeFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL 数据校验执行单据参数"""

    controller = MySQLController.mysql_fake_sql_semantic_check_scene


@builders.BuilderFactory.register(TicketType.FAKE_TICKET)
class MySQLDataMigrateFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLFakeDetailSerializer
    inner_flow_builder = MySQLFakeFlowParamBuilder

    @property
    def need_itsm(self):
        return False

    @property
    def need_manual_confirm(self):
        return False
