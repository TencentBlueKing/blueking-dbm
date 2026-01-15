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


class RedisSlowlogInputSerializer(serializers.Serializer):
    """Redis慢查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))


class RedisSlowlog4HostInputSerializer(serializers.Serializer):
    """Redis慢查询输入序列化器"""

    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    ip = serializers.CharField(help_text=_("主机IP"))


class RedisSlowlogEntrySerializer(serializers.Serializer):
    """Redis慢查询日志条目"""

    create_time = serializers.CharField(help_text=_("执行时间"))
    duration_us = serializers.IntegerField(help_text=_("执行耗时（微秒）"))
    # duration_ms = serializers.FloatField(help_text=_("执行耗时（毫秒）"))
    cmd = serializers.CharField(help_text=_("命令"))
    key = serializers.CharField(help_text=_("KEY"))
    args = serializers.ListField(child=serializers.CharField(), help_text=_("参数"))
    instance_addr = serializers.CharField(help_text=_("实例地址"))
    instance_role = serializers.CharField(help_text=_("实例角色"))


class RedisSlowlogResponseSerializer(serializers.Serializer):
    """Redis慢查询响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("慢查询日志总数"))
    slowlog_entries = RedisSlowlogEntrySerializer(many=True, help_text=_("慢查询日志列表"))
