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


class SQLServerSlowLogQueryInputSerializer(serializers.Serializer):
    order_by_choices = [
        ("duration", _("按 DURATION 倒序")),
        ("cpu", _("按 CPU 时间倒序")),
        ("reads", _("按 READS 倒序")),
        ("writes", _("按 WRITES 倒序")),
        ("starttime", _("按起始时间倒序")),
    ]

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省查询 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    start_time = serializers.DateTimeField(
        help_text=_("起始时间（含），ISO 格式；不传则取 end_time 之前 1 小时"),
        required=False,
        allow_null=True,
        default=None,
    )
    end_time = serializers.DateTimeField(
        help_text=_("结束时间（含），ISO 格式；不传则取当前时间"),
        required=False,
        allow_null=True,
        default=None,
    )
    database_name = serializers.CharField(
        help_text=_("业务数据库名，可选；精确匹配 TRACE_TSQL.DATABASENAME"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    min_duration_ms = serializers.IntegerField(
        help_text=_("最小耗时阈值，单位毫秒，默认 0"),
        required=False,
        default=0,
        min_value=0,
    )
    top = serializers.IntegerField(
        help_text=_("返回条数上限，取值范围 (0, 200]"),
        required=False,
        default=20,
        min_value=1,
        max_value=200,
    )
    order_by = serializers.ChoiceField(
        choices=order_by_choices,
        help_text=_("排序维度，仅允许 duration/cpu/reads/writes/starttime"),
        required=False,
        default="duration",
    )


class SQLServerSlowLogFilterSerializer(serializers.Serializer):
    start_time = serializers.CharField(help_text=_("实际生效的起始时间"))
    end_time = serializers.CharField(help_text=_("实际生效的结束时间"))
    database_name = serializers.CharField(help_text=_("库名过滤值"), allow_null=True, allow_blank=True)
    min_duration_ms = serializers.IntegerField(help_text=_("最小耗时阈值（毫秒）"))
    order_by = serializers.CharField(help_text=_("排序维度"))


class SQLServerSlowLogRowSerializer(serializers.Serializer):
    starttime = serializers.CharField(help_text=_("SQL 起始时间"), allow_null=True)
    endtime = serializers.CharField(help_text=_("SQL 结束时间"), allow_null=True)
    duration_ms = serializers.IntegerField(help_text=_("总耗时（毫秒，由 DURATION 微秒换算）"))
    cpu_ms = serializers.IntegerField(help_text=_("CPU 时间（毫秒）"), allow_null=True)
    reads = serializers.IntegerField(help_text=_("逻辑读次数"), allow_null=True)
    writes = serializers.IntegerField(help_text=_("写次数"), allow_null=True)
    row_counts = serializers.IntegerField(help_text=_("返回行数"), allow_null=True)
    database_name = serializers.CharField(help_text=_("数据库名"), allow_null=True, allow_blank=True)
    login_name = serializers.CharField(help_text=_("登录名"), allow_null=True, allow_blank=True)
    nt_user_name = serializers.CharField(help_text=_("NT 用户名"), allow_null=True, allow_blank=True)
    application_name = serializers.CharField(help_text=_("客户端应用程序"), allow_null=True, allow_blank=True)
    object_name = serializers.CharField(help_text=_("对象名"), allow_null=True, allow_blank=True)
    error = serializers.IntegerField(help_text=_("错误码，0 表示无错误"), allow_null=True)
    sql_text = serializers.CharField(help_text=_("SQL 文本（已截断）"), allow_null=True, allow_blank=True)
    sql_text_truncated = serializers.IntegerField(help_text=_("SQL 文本是否被截断，1/0"))


class SQLServerSlowLogQueryOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    filter = SQLServerSlowLogFilterSerializer(help_text=_("实际生效的过滤条件回显"))
    row_count = serializers.IntegerField(help_text=_("返回的慢日志条数"))
    slow_logs = SQLServerSlowLogRowSerializer(
        many=True,
        help_text=_("慢日志列表"),
    )
