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
from backend.ticket.constants import FlowRetryType


class CloneMySQLGrantsDetailSerializer(MySQLBaseOperateDetailSerializer):
    class CloneMySQLGrantsInfoSerializer(serializers.Serializer):
        """
        这里隐含了, 不同云区域之间是不能克隆权限的
        跨云克隆权限实际上意义不大
        """

        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        machine_type = serializers.CharField(help_text=_("机器类型"))
        source_address = serializers.CharField(help_text=_("源实例地址"))
        dest_addresses = serializers.ListField(help_text=_("目标实例地址列表"), child=serializers.CharField())

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    infos = serializers.ListSerializer(help_text=_("权限克隆参数"), child=CloneMySQLGrantsInfoSerializer())


class CloneMySQLGrantsFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.clone_mysql_grants


# @builders.BuilderFactory.register(TicketType.MYSQL_INSTANCE_CLONE_RULES)
class CloneMySQLGrantsFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = CloneMySQLGrantsDetailSerializer
    inner_flow_builder = CloneMySQLGrantsFlowParamBuilder
    inner_flow_name = _("MySQL 权限克隆")
    retry_type = FlowRetryType.MANUAL_RETRY
