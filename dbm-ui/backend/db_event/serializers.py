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


class QueryDetailSerializer(serializers.Serializer):
    """查询dbha事件详情"""

    sw_id = serializers.IntegerField(help_text=_("事件ID"))


class LogSerializer(serializers.Serializer):
    """日志格式"""

    message = serializers.CharField(max_length=1024, help_text=_("日志内容"))
    levelname = serializers.CharField(max_length=64, help_text=_("日志级别"))
    timestamp = serializers.DateTimeField(help_text=_("时间戳"))


class DetailLogsSerializer(serializers.Serializer):
    """dbha事件详情日志"""

    logs = serializers.ListSerializer(child=LogSerializer(), help_text=_("日志列表"))


class EventDetailSerializer(serializers.Serializer):
    """dbha事件详情"""

    uid = serializers.CharField(max_length=255)
    port = serializers.IntegerField()
    slave_ip = serializers.CharField(
        max_length=255,
    )
    slave_port = serializers.IntegerField()
    domain_name = serializers.CharField(max_length=255, help_text=_("集群"))

    app = serializers.IntegerField(help_text=_("业务ID"), required=False)
    ip = serializers.IPAddressField(help_text=_("实例IP"))
    db_type = serializers.CharField(max_length=255, help_text=_("实例类型"))
    db_role = serializers.CharField(max_length=255, help_text=_("实例角色"))
    switch_start_time = serializers.DateTimeField(help_text=_("开始时间"))
    switch_finished_time = serializers.DateTimeField(help_text=_("结束时间"), required=False)
    confirm_check_time = serializers.DateTimeField(help_text=_("结束时间"))
    switch_result = serializers.CharField(max_length=255)
    confirm_result = serializers.CharField(max_length=255)


class QueryListSerializer(serializers.Serializer):
    """查询dbha事件列表"""

    app = serializers.IntegerField(help_text=_("业务ID"), required=False)
    # ip = serializers.IPAddressField(help_text=_("实例IP"))
    # domain_name = serializers.CharField(max_length=255, help_text=_("集群"))
    # db_type = serializers.CharField(max_length=255, help_text=_("实例类型"))
    # db_role = serializers.CharField(max_length=255, help_text=_("实例角色"))
    switch_start_time = serializers.DateTimeField(help_text=_("开始时间"), required=False)
    switch_finished_time = serializers.DateTimeField(help_text=_("结束时间"), required=False)


class ListSerializer(serializers.Serializer):
    """dbha事件列表"""

    events = serializers.ListSerializer(child=EventDetailSerializer())
