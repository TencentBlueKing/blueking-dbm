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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_instance_role_choices


class DatabaseSizeInputSerializer(serializers.Serializer):
    mysql_role_choices = [
        ("slave", "slave"),
        ("master", "master"),
    ]

    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(choices=mysql_role_choices, help_text=_("db角色，采集默认都在 slave 上进行"))
    database_names = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("要查询的数据库名列表，传 ['*'] 则查询所有数据库大小"),
    )
    base_time = serializers.DateTimeField(
        help_text=_("基准时间，默认为空表示当前时间。查询范围为 [base_time - 48h, base_time]"),
        required=False,
        default=None,
    )
    limit = serializers.IntegerField(help_text=_("返回数量限制"), required=False, default=20)


class DatabaseSizeRowSerializer(serializers.Serializer):
    database_name = serializers.CharField(help_text=_("数据库名（逻辑库名）"))
    dteventtimehour = serializers.CharField(help_text=_("统计时间（精确到小时）"))
    database_size = serializers.IntegerField(help_text=_("数据库大小（字节）"))
    latest_report_time = serializers.CharField(help_text=_("最近上报时间"))


class DatabaseSizeOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    databases = DatabaseSizeRowSerializer(many=True, help_text=_("数据库大小列表"))


class TableSizeInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(choices=mysql_instance_role_choices, help_text=_("db实例角色"))
    database_name = serializers.CharField(help_text=_("数据库名（逻辑库名）"))
    table_names = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("要查询的表名列表，传 ['*'] 则查询该库下所有表大小"),
    )
    base_time = serializers.DateTimeField(
        help_text=_("基准时间，默认为空表示当前时间。查询范围为 [base_time - 48h, base_time]"),
        required=False,
        default=None,
    )
    limit = serializers.IntegerField(help_text=_("返回数量限制"), required=False, default=50)


class TableSizeRowSerializer(serializers.Serializer):
    database_name = serializers.CharField(help_text=_("数据库名（逻辑库名）"))
    table_name = serializers.CharField(help_text=_("表名"))
    dteventtimehour = serializers.CharField(help_text=_("统计时间（精确到小时）"))
    table_size = serializers.IntegerField(help_text=_("表大小（字节）"))
    latest_report_time = serializers.CharField(help_text=_("最近上报时间"))


class TableSizeOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    database_name = serializers.CharField(help_text=_("数据库名"))
    tables = TableSizeRowSerializer(many=True, help_text=_("表大小列表"))
