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


class MysqlStandardizeDetailSerializer(MySQLBaseOperateDetailSerializer):
    class StandardizeDetailSerializer(serializers.Serializer):
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"))

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    infos = StandardizeDetailSerializer(help_text=_("标准化信息"))

    def validate(self, attrs):
        return attrs


class MysqlStandardizeFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_standardize_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_STANDARDIZE)
class MysqlStandardizeFlowBuilder(BaseMySQLTicketFlowBuilder):
    """Mysql下架流程的构建基类"""

    serializer = MysqlStandardizeDetailSerializer
    inner_flow_builder = MysqlStandardizeFlowParamBuilder
    inner_flow_name = _("MySQL高可用标准化")
    retry_type = FlowRetryType.MANUAL_RETRY
