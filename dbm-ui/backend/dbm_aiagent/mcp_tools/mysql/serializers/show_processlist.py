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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import (
    MySQLProcessListFilterFieldType,
    MySQLProcessListFilterOpType,
    processlist_group_by_choices,
)


class ShowProcessListFilter(serializers.Serializer):
    filter_field = serializers.ChoiceField(choices=MySQLProcessListFilterFieldType.get_choices(), help_text=_("过滤字段"))
    filter_op = serializers.ChoiceField(choices=MySQLProcessListFilterOpType.get_choices(), help_text=_("过滤操作"))
    filter_values = serializers.ListField(child=serializers.CharField(), help_text=_("过滤值"))


class ShowClusterProcessListSummaryInputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    # instance_group = serializers.ChoiceField(
    #     choices=MySQLProcessListInstanceGroupType.get_choices(),
    #     help_text=_("实例分组"),
    #     default=MySQLProcessListInstanceGroupType.MasterGroup,
    # )
    # detail = serializers.BooleanField(help_text=_("显示连接详情"), required=False, default=False)
    # processlist_filters = serializers.ListField(
    #     child=ShowProcessListFilter(), help_text=_("连接信息过滤器"), required=False, default=[]
    # )


class ProcessListRowSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("连接 ID"))
    access_source_address = serializers.CharField(help_text=_("ip:port 形式的来源地址"))
    proxy_address = serializers.CharField(help_text=_("ip:port 形式的接入层地址"))
    mysql_address = serializers.CharField(help_text=_("ip:port 形式的 mysql 地址"))
    command = serializers.CharField(help_text=_("正在执行的命令操作"))
    user = serializers.CharField(help_text=_("连接用户名"))
    db = serializers.CharField(help_text=_("正在访问的 db 名"))
    time = serializers.IntegerField(help_text=_("活跃时间, 单位是秒"))
    state = serializers.CharField(help_text=_("连接状态"))


class ProcessListSummarySerializer(serializers.Serializer):
    total_count = serializers.Serializer(serializers.IntegerField(), help_text=_("总连接数"))
    group_by_access_source_address = serializers.JSONField(help_text=_("按访问来源聚合计数结果"))
    group_by_user = serializers.JSONField(help_text=_("按连接账号名聚合计数结果"))
    group_by_db = serializers.JSONField(help_text=_("按访问数据库名聚合计数结果"))
    group_by_command = serializers.JSONField(help_text=_("按当前执行命令聚合计数结果"))
    group_by_state = serializers.JSONField(help_text=_("按连接状态聚合计数结果"))
    group_by_instance_address = serializers.JSONField(help_text=_("按 DB 实例聚合计数结果"))
    time_histogram = serializers.JSONField(help_text=_("连接时间划分结果"))


class ShowClusterProcessListSummaryOutputSerializer(serializers.Serializer):
    proxy_processlist_summary = ProcessListSummarySerializer(help_text=_("接入层连接摘要"))
    storage_processlist_summary = ProcessListSummarySerializer(help_text=_("存储层连接摘要"))
    message = serializers.CharField(help_text=_("附加说明信息"))


class ShowInstanceProcessListSummaryInputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance = serializers.CharField(help_text=_("实例，ip:port 格式"))
    aggregate_type = serializers.ChoiceField(
        choices=processlist_group_by_choices,
        help_text=_("用户连接会话 processlist 的聚合方式，例如 query_time,slow_count,rows_scan"),
    )


class ShowInstanceProcessListSummaryOutputSerializer(serializers.Serializer):
    processlist_summary = ProcessListSummarySerializer(help_text=_("processlist 聚合结果"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    # aggregate_type = serializers.CharField(help_text=_("processlist 聚合方式"))
    message = serializers.CharField(help_text=_("附加说明信息"))
