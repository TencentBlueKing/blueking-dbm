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


class ShowInstanceProcessListInputSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    address = serializers.CharField(help_text=_("实例地址, ip:port 格式"))


class MySQLProcessListRowSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("连接 ID"))
    source_host = serializers.CharField(help_text=_("来源地址"))
    command = serializers.CharField(help_text=_("正在执行的命令操作"))
    user = serializers.CharField(help_text=_("连接用户名"))
    db = serializers.CharField(help_text=_("正在访问的 db 名"))
    time = serializers.IntegerField(help_text=_("活跃时间, 单位是秒"))
    state = serializers.CharField(help_text=_("连接状态"))
    info = serializers.CharField(help_text=_("正在执行的 SQL 语句"), allow_null=True)
    tables = serializers.ListField(child=serializers.CharField(), help_text=_("SQL 涉及的表"))
    fingerprint = serializers.CharField(help_text=_("SQL 指纹"))
    fingerprint_md5 = serializers.CharField(help_text=_("SQL 指纹 MD5"))
    query_len = serializers.IntegerField(help_text=_("SQL 长度"))


class ShowMySQLInstanceProcessListOutputSerializer(serializers.Serializer):
    processlist = MySQLProcessListRowSerializer(many=True, help_text=_("MySQL 实例进程列表"))


class ProxyProcessListRowSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("连接 ID"))
    source_host = serializers.CharField(help_text=_("来源地址"))
    user = serializers.CharField(help_text=_("连接用户名"))
    destination_host = serializers.CharField(help_text=_("目标后端地址"))
    state = serializers.CharField(help_text=_("连接状态"))
    db = serializers.CharField(help_text=_("正在访问的 db 名"))
    time = serializers.IntegerField(help_text=_("活跃时间, 单位是秒"))


class ShowProxyProcessListOutputSerializer(serializers.Serializer):
    processlist = ProxyProcessListRowSerializer(many=True, help_text=_("Proxy 进程列表"))


class ShowInstanceProcessListAggregatedInputSerializer(serializers.Serializer):
    # 需要使用 auth_parse_instances 鉴权，不要求输入 bk_biz_id / cluster_domain
    processlist_group_by_choices = [
        ("group_by_fingerprint", _("按 sql 类型聚合计数")),
        ("longest_top_5", _("按连 sql 执行时长排序前 5")),
        ("group_by_user", _("按连接账号名聚合计数")),
        ("group_by_state", _("按连接状态聚合计数")),
        ("group_by_command", _("按连接命令聚合计数")),
        ("group_by_client_host", _("按访问来源ip聚合计数")),
    ]

    instance = serializers.CharField(help_text=_("实例，ip:port 格式"))
    aggregate_type = serializers.MultipleChoiceField(
        choices=processlist_group_by_choices,
        help_text=_("用户连接会话 processlist 的聚合方式，可选多个"),
        default=["group_by_fingerprint", "longest_top_5"],
    )


class ShowInstanceProcessListAggregatedRowSerializer(serializers.Serializer):
    processlist_aggregated = serializers.CharField(help_text=_("processlist 聚合结果"))
    aggregate_type = serializers.CharField(help_text=_("processlist 聚合方式"))
    total_count = serializers.IntegerField(help_text=_("processlist 原始的总条数"))


class ShowInstanceProcessListAggregatedOutputSerializer(serializers.Serializer):
    processlist_summary = ShowInstanceProcessListAggregatedRowSerializer(many=True, help_text=_("processlist 多重聚合结果"))
    instance_role = serializers.CharField(help_text=_("processlist 所属实例角色"))
