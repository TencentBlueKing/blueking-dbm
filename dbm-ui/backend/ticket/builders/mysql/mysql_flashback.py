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
import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.constants import MYSQL_BINLOG_ROLLBACK
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow
from backend.utils.time import str2datetime


class MySQLFlashbackDetailSerializer(MySQLBaseOperateDetailSerializer):
    class FlashbackSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        start_time = serializers.CharField(help_text=_("开始时间"))
        end_time = serializers.CharField(help_text=_("结束时间"))
        databases = serializers.ListField(help_text=_("目标库列表"), child=serializers.CharField())
        databases_ignore = serializers.ListField(help_text=_("忽略库列表"), child=serializers.CharField())
        tables = serializers.ListField(help_text=_("目标table列表"), child=serializers.CharField())
        tables_ignore = serializers.ListField(help_text=_("忽略table列表"), child=serializers.CharField())
        mysqlbinlog_rollback = serializers.CharField(
            help_text=_("flashback工具地址"), default=MYSQL_BINLOG_ROLLBACK, required=False
        )
        recored_file = serializers.CharField(help_text=_("记录文件"), required=False, default="")

    infos = serializers.ListSerializer(help_text=_("flashback信息"), child=FlashbackSerializer(), allow_empty=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super(MySQLFlashbackDetailSerializer, self).validate_cluster_can_access(attrs)

        # 校验start time和end time的合法性
        for info in attrs["infos"]:
            start_time, end_time = str2datetime(info["start_time"]), str2datetime(info["start_time"])
            now = datetime.datetime.now()
            if start_time > end_time or start_time > now or end_time > now:
                raise serializers.ValidationError(
                    _("flash的起止时间{}--{}不合法，请保证开始时间小于结束时间，并且二者不大于当前时间").format(start_time, end_time)
                )

        return attrs


class MySQLFlashbackFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_flashback_scene

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_FLASHBACK)
class MysqlSingleDestroyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLFlashbackDetailSerializer
    inner_flow_builder = MySQLFlashbackFlowParamBuilder
    inner_flow_name = _("闪回执行")
    retry_type = FlowRetryType.MANUAL_RETRY
