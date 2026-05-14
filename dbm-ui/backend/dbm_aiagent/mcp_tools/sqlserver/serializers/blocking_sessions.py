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


class SQLServerBlockingSessionsInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省查询 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    top = serializers.IntegerField(
        help_text=_("返回条数上限，按等待时间倒序，取值范围 (0, 200]"),
        required=False,
        default=20,
        min_value=1,
        max_value=200,
    )


class SQLServerBlockingSessionRowSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(help_text=_("被阻塞会话 ID"))
    blocking_session_id = serializers.IntegerField(help_text=_("阻塞源会话 ID"))
    status = serializers.CharField(help_text=_("请求状态"), allow_null=True)
    command = serializers.CharField(help_text=_("命令类型"), allow_null=True)
    wait_type = serializers.CharField(help_text=_("等待类型"), allow_null=True)
    wait_time_ms = serializers.IntegerField(help_text=_("当前等待时长 ms"))
    wait_resource = serializers.CharField(help_text=_("等待资源描述"), allow_null=True, allow_blank=True)
    cpu_time_ms = serializers.IntegerField(help_text=_("CPU 时间 ms"))
    elapsed_time_ms = serializers.IntegerField(help_text=_("总耗时 ms"))
    reads = serializers.IntegerField(help_text=_("物理读次数"))
    writes = serializers.IntegerField(help_text=_("物理写次数"))
    logical_reads = serializers.IntegerField(help_text=_("逻辑读次数"))
    database_name = serializers.CharField(help_text=_("数据库名"), allow_null=True)
    login_name = serializers.CharField(help_text=_("登录名"), allow_null=True)
    host_name = serializers.CharField(help_text=_("客户端主机"), allow_null=True)
    program_name = serializers.CharField(help_text=_("客户端程序"), allow_null=True)
    blocker_login_name = serializers.CharField(help_text=_("阻塞源登录名"), allow_null=True)
    blocker_host_name = serializers.CharField(help_text=_("阻塞源客户端主机"), allow_null=True)
    blocker_program_name = serializers.CharField(help_text=_("阻塞源客户端程序"), allow_null=True)
    sql_text = serializers.CharField(help_text=_("当前语句文本（已截断）"), allow_null=True, allow_blank=True)
    sql_text_truncated = serializers.IntegerField(help_text=_("SQL 文本是否被截断，1/0"))


class SQLServerBlockingSessionsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    blocking_count = serializers.IntegerField(help_text=_("阻塞链条数"))
    blocking_sessions = SQLServerBlockingSessionRowSerializer(
        many=True,
        help_text=_("阻塞会话列表"),
    )
