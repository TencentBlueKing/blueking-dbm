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
from rest_framework import serializers

from backend.ticket.constants import TicketType


class TaskflowLogQueryInputSerializer(serializers.Serializer):
    root_id = serializers.CharField(help_text=_("任务流 ID"))


class LogRecordSerializer(serializers.Serializer):
    timestamp = serializers.IntegerField(help_text=_("日志时间戳（毫秒）"))
    levelname = serializers.CharField(help_text=_("日志级别"))
    message = serializers.CharField(help_text=_("日志内容"))


class TaskflowErrorLogOutputSerializer(serializers.Serializer):
    node_id = serializers.CharField(help_text=_("失败节点 ID，无失败节点时为空字符串"))
    node_name = serializers.CharField(help_text=_("失败节点名称，无失败节点时为空字符串"))
    logs = serializers.ListField(child=LogRecordSerializer(), help_text=_("错误日志列表"))


class FailedTaskflowListInputSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    ticket_types = serializers.ListField(
        child=serializers.ChoiceField(choices=TicketType.get_choices()),
        help_text=_("单据类型列表，为空则查询所有类型"),
        default=[],
    )


class FailedTaskflowListOutputSerializer(serializers.Serializer):
    root_ids = serializers.ListField(child=serializers.CharField(), help_text=_("失败的任务流 root_id 列表"))
