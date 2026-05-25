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


class SQLServerTopRequestsInputSerializer(serializers.Serializer):
    order_by_choices = [
        ("cpu", _("按 CPU 时间倒序")),
        ("duration", _("按总耗时倒序")),
        ("reads", _("按逻辑读次数倒序")),
        ("writes", _("按写次数倒序")),
    ]

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省查询 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    top = serializers.IntegerField(
        help_text=_("返回条数上限，取值范围 (0, 100]"),
        required=False,
        default=20,
        min_value=1,
        max_value=100,
    )
    order_by = serializers.ChoiceField(
        choices=order_by_choices,
        help_text=_("排序维度，仅允许 cpu/duration/reads/writes"),
        required=False,
        default="cpu",
    )


class SQLServerTopRequestRowSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(help_text=_("会话 ID"))
    status = serializers.CharField(help_text=_("请求状态"), allow_null=True)
    command = serializers.CharField(help_text=_("命令类型"), allow_null=True)
    blocking_session_id = serializers.IntegerField(help_text=_("阻塞源会话 ID，0 表示无阻塞"))
    wait_type = serializers.CharField(help_text=_("等待类型"), allow_null=True, allow_blank=True)
    wait_time_ms = serializers.IntegerField(help_text=_("当前等待时长 ms"))
    cpu_time_ms = serializers.IntegerField(help_text=_("CPU 时间 ms"))
    elapsed_time_ms = serializers.IntegerField(help_text=_("总耗时 ms"))
    reads = serializers.IntegerField(help_text=_("物理读次数"))
    writes = serializers.IntegerField(help_text=_("物理写次数"))
    logical_reads = serializers.IntegerField(help_text=_("逻辑读次数"))
    row_count = serializers.IntegerField(help_text=_("已返回行数"))
    database_name = serializers.CharField(help_text=_("数据库名"), allow_null=True)
    login_name = serializers.CharField(help_text=_("登录名"), allow_null=True)
    host_name = serializers.CharField(help_text=_("客户端主机"), allow_null=True)
    program_name = serializers.CharField(help_text=_("客户端程序"), allow_null=True)
    sql_text = serializers.CharField(help_text=_("当前语句文本（已截断）"), allow_null=True, allow_blank=True)
    sql_text_truncated = serializers.IntegerField(help_text=_("SQL 文本是否被截断，1/0"))


class SQLServerTopRequestsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    order_by = serializers.CharField(help_text=_("实际生效的排序维度"))
    top_requests = SQLServerTopRequestRowSerializer(
        many=True,
        help_text=_("活跃请求 TOP N"),
    )
