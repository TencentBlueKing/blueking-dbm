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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLPushPeripheralConfigSerializer(MySQLBaseOperateDetailSerializer):
    class PushPeripheralConfigInfoSerializer(MySQLBaseOperateDetailSerializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"))

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    infos = PushPeripheralConfigInfoSerializer(help_text=_("单据输入"))

    def validate(self, attrs):
        return attrs


class MySQLPushPeripheralConfigFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.push_peripheral_config_scene


@builders.BuilderFactory.register(TicketType.MYSQL_PUSH_PERIPHERAL_CONFIG)
class MySQLPushPeripheralConfigFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLPushPeripheralConfigSerializer
    inner_flow_builder = MySQLPushPeripheralConfigFlowParamBuilder
    inner_flow_name = _("下发周边配置")
    retry_type = FlowRetryType.MANUAL_RETRY
