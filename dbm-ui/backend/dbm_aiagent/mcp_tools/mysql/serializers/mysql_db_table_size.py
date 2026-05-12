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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_capacity_inner_role_choices


class _MysqlCapacityFilterInputMixin:
    """limit：按名字典序截取前 N 条；top_n：按字节大小降序取前 N 条。二者互斥。"""

    def validate(self, attrs):
        limit = attrs.get("limit")
        top_n = attrs.get("top_n")
        if limit is not None and top_n is not None:
            raise serializers.ValidationError(_("参数 limit 与 top_n 不能同时指定"))
        return attrs


class DatabaseSizeInputSerializer(_MysqlCapacityFilterInputMixin, serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(
        choices=mysql_capacity_inner_role_choices, help_text=_("db角色，采集默认都在 slave 上进行")
    )
    database_names = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("要查询的数据库名列表，传 ['*'] 则查询所有数据库大小"),
    )
    base_time = serializers.DateTimeField(
        help_text=_("基准时间，默认为空表示当前时间。查询范围为 [base_time - 48h, base_time]"),
        required=False,
        default=None,
    )
    limit = serializers.IntegerField(
        help_text=_("按 database_name 字典序返回前 limit 条；未传时默认 20。与 top_n 互斥"),
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
        max_value=100,
    )
    top_n = serializers.IntegerField(
        help_text=_("按 database_size 字节从大到小取前 top_n 条；与 limit 互斥"),
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
        max_value=100,
    )
    min_size_bytes = serializers.IntegerField(
        help_text=_("仅返回 database_size 大于等于该值（字节）的库；可与 limit 或 top_n 组合"),
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
    )


class DatabaseSizeRowSerializer(serializers.Serializer):
    database_name = serializers.CharField(help_text=_("数据库名（逻辑库名）"))
    dteventtimehour = serializers.CharField(help_text=_("统计时间（精确到小时）"))
    database_size = serializers.IntegerField(help_text=_("数据库大小（字节）"))
    latest_report_time = serializers.CharField(help_text=_("最近上报时间"))


class DatabaseSizeOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    databases = DatabaseSizeRowSerializer(many=True, help_text=_("数据库大小列表"))


class TableSizeInputSerializer(_MysqlCapacityFilterInputMixin, serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(
        choices=mysql_capacity_inner_role_choices, help_text=_("db角色，采集默认都在 slave 上进行")
    )
    database_name = serializers.CharField(
        help_text=_("数据库名（逻辑库名）；不传或为空时跨集群下所有库查询符合 table_names 的表"),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )
    table_names = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("要查询的表名列表，传 ['*'] 则查询所有表大小；" "未指定 database_name 时表示跨所有库查询同名表，建议同时使用 limit/top_n 控制返回量"),
    )
    base_time = serializers.DateTimeField(
        help_text=_("基准时间，默认为空表示当前时间。查询范围为 [base_time - 48h, base_time]"),
        required=False,
        default=None,
    )
    limit = serializers.IntegerField(
        help_text=_("按 table_name 字典序返回前 limit 条；未传时默认 50。与 top_n 互斥"),
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
        max_value=100,
    )
    top_n = serializers.IntegerField(
        help_text=_("按 table_size 字节从大到小取前 top_n 条；与 limit 互斥"),
        required=False,
        allow_null=True,
        default=None,
        min_value=1,
        max_value=100,
    )
    min_size_bytes = serializers.IntegerField(
        help_text=_("仅返回 table_size 大于等于该值（字节）的表；可与 limit 或 top_n 组合"),
        required=False,
        allow_null=True,
        default=None,
        min_value=0,
    )


class TableSizeRowSerializer(serializers.Serializer):
    database_name = serializers.CharField(help_text=_("数据库名（逻辑库名）"))
    table_name = serializers.CharField(help_text=_("表名"))
    dteventtimehour = serializers.CharField(help_text=_("统计时间（精确到小时）"))
    table_size = serializers.IntegerField(help_text=_("表大小（字节）"))
    latest_report_time = serializers.CharField(help_text=_("最近上报时间"))


class TableSizeOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    database_name = serializers.CharField(
        help_text=_("数据库名；跨库查询（入参未指定 database_name）时为空"),
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
    )
    tables = TableSizeRowSerializer(many=True, help_text=_("表大小列表"))
