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
    mysql_cluster_type_choices,
    mysql_metric_name_choices,
)


class MysqlMetricsInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))
    start_time = serializers.DateTimeField(help_text=_("开始时间, 时间格式 2026-01-08T16:33:38+08:00"))
    end_time = serializers.DateTimeField(help_text=_("结束时间, 时间格式 2026-01-08T16:33:38+08:00"))
    metric_name = serializers.ChoiceField(
        choices=mysql_metric_name_choices, help_text=_("mysql 指标名称，" "性能指标有 cpu负载, qps请求量, 慢日志数量，线程数，连接数")
    )


class MysqlMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    datapoints = serializers.JSONField(help_text=_("时序指标结果"))


class ShowInstanceProcessListAggregatedInputSerializer(serializers.Serializer):
    # 需要使用 auth_parse_instances 鉴权，不要求输入 bk_biz_id / cluster_domain
    processlist_group_by_choices = [
        ("group_by_fingerprint", _("按 sql 类型聚合计数")),
        ("longest_top_5", _("按连 sql 执行时长排序前 5")),
        ("group_by_user", _("按连接账号名聚合计数")),
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
