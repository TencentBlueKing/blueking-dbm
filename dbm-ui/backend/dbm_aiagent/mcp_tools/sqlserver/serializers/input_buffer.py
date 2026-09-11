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


class SQLServerInputBufferInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    session_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=32767),
        help_text=_("会话 ID 列表（正整数），一次最多 100 个"),
    )
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省查询 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    max_event_info_chars = serializers.IntegerField(
        help_text=_("event_info 截断长度（防超长语句），取值范围 [256, 32767]"),
        required=False,
        default=4000,
        min_value=256,
        max_value=32767,
    )


class SQLServerInputBufferRowSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(help_text=_("会话 ID"))
    login_name = serializers.CharField(help_text=_("登录名"), allow_null=True)
    host_name = serializers.CharField(help_text=_("客户端主机"), allow_null=True)
    program_name = serializers.CharField(help_text=_("客户端程序"), allow_null=True)
    database_name = serializers.CharField(help_text=_("数据库名"), allow_null=True)
    event_type = serializers.CharField(help_text=_("事件类型：RPC Event（存储过程调用）/ Language Event（直接 SQL）"), allow_null=True)
    is_sp_executesql = serializers.IntegerField(help_text=_("是否为 sp_executesql 动态 SQL，1/0"))
    event_info = serializers.CharField(help_text=_("最近执行的 SQL 文本（已脱敏，可能被截断）"), allow_null=True, allow_blank=True)
    event_info_truncated = serializers.IntegerField(help_text=_("event_info 是否被截断，1/0"))


class SQLServerInputBufferOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    session_count = serializers.IntegerField(help_text=_("实际返回的会话数"))
    input_buffers = SQLServerInputBufferRowSerializer(many=True, help_text=_("input buffer 列表"))
