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
from backend.ticket.builders.common.constants import MySQLDataRepairTriggerMode
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MySQLDataRepairDetailSerializer(MySQLBaseOperateDetailSerializer):
    class MySQLDataRepairInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        master = serializers.DictField(help_text=_("master信息"))
        slaves = serializers.ListField(help_text=_("slaves信息"), child=serializers.DictField())

    infos = serializers.ListField(help_text=_("数据修复信息"), child=MySQLDataRepairInfoSerializer())
    checksum_table = serializers.CharField(help_text=_("校验单据结果表名"))
    is_sync_non_innodb = serializers.BooleanField(help_text=_("非innodb表是否修复"), required=False, default=False)
    is_ticket_consistent = serializers.BooleanField(help_text=_("校验结果是否一致"), required=False, default=False)
    start_time = DBTimezoneField(help_text=_("开始时间"), required=False, default="")
    end_time = DBTimezoneField(help_text=_("结束时间"), required=False, default="")
    trigger_type = serializers.ChoiceField(help_text=_("数据修复触发类型"), choices=MySQLDataRepairTriggerMode.get_choices())


class MySQLDataRepairFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL 数据校验执行单据参数"""

    controller = MySQLController.mysql_pt_table_sync_scene


@builders.BuilderFactory.register(TicketType.MYSQL_DATA_REPAIR)
class MySQLDataRepairFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDataRepairDetailSerializer
    inner_flow_builder = MySQLDataRepairFlowParamBuilder
    inner_flow_name = _("数据修复执行")
