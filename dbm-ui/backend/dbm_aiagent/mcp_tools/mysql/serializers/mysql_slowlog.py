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
    mysql_instance_role_choices,
    mysql_slowlog_metric_name_choices,
    mysql_slowlog_orderby_choices,
)


class MysqlSlowlogInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(choices=mysql_instance_role_choices, help_text=_("db实例角色"))
    metric_name = serializers.ChoiceField(
        choices=mysql_slowlog_metric_name_choices, help_text=_("慢日志指标名称，例如 query_time,slow_count,rows_scan")
    )
    limit = serializers.IntegerField(help_text=_("查看 top N 慢日志种类"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))


class MysqlSlowlogOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    slowlogs = serializers.JSONField(
        help_text=_(
            "慢日志列表."
            "query_digest_text 是慢日志摘要字段，也叫 digest_text 或者 fingerprint。"
            "query_digest_md5 是慢日志摘要字段的 MD5 值，也叫 digest 或者 query_digest"
        )
    )


class SlowlogAggregatedInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.ChoiceField(choices=mysql_instance_role_choices, help_text=_("db实例角色"))
    metric_name = serializers.ChoiceField(choices=mysql_slowlog_orderby_choices, help_text=_("按照哪个指标来聚合排序"))
    limit = serializers.IntegerField(help_text=_("查看 top N 慢日志种类"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    query_sample = serializers.BooleanField(help_text=_("是否返回原始 sql 示例"), required=False, default=True)
    exclude_system = serializers.BooleanField(help_text=_("是否排除系统自身产生的慢日志"), required=False, default=True)


class SlowlogAggregatedRowSerializer(serializers.Serializer):
    query_digest_md5 = serializers.CharField(help_text=_("慢日志摘要字段的 MD5 值，也叫 digest 或者 query_digest"))
    query_digest_text = serializers.CharField(help_text=_("慢日志摘要字段，也叫 digest_text 或者 fingerprint"))
    time_window_min = serializers.DateTimeField(help_text=_("时间窗口开始"))
    time_window_max = serializers.DateTimeField(help_text=_("时间窗口结束"))
    count_star = serializers.IntegerField(help_text=_("慢日志数量"))
    query_time_max = serializers.FloatField(help_text=_("最大查询时间"))
    query_time_sum = serializers.FloatField(help_text=_("总查询时间"))
    rows_examined_max = serializers.IntegerField(help_text=_("最大扫描行数"))
    rows_examined_sum = serializers.IntegerField(help_text=_("总扫描行数"))
    rows_sent_max = serializers.IntegerField(help_text=_("最大返回行数"))
    rows_sent_sum = serializers.IntegerField(help_text=_("总返回行数"))
    query_string = serializers.CharField(help_text=_("原始 sql 示例"))
    query_command = serializers.CharField(help_text=_("sql 类型"))
    query_db_name = serializers.CharField(help_text=_("数据库名"))
    table_names = serializers.CharField(help_text=_("表名"))
    username = serializers.CharField(help_text=_("用户名"))
    instance_host = serializers.CharField(help_text=_("DB机器主机 ip 示例"))
    instance_port = serializers.IntegerField(help_text=_("DB实例 port 示例"))


class SlowlogAggregatedOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    metric_name = serializers.CharField(help_text=_("返回的结果是按照哪种指标聚合排序的"))
    slow_logs = SlowlogAggregatedRowSerializer(many=True, help_text=_("慢日志列表"))


class MysqlOneSlowlogInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    query_digest_md5 = serializers.CharField(help_text=_("慢日志摘要，query_digest 与 query_digest_md5 是同一个意思"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))


class MysqlSlowTunerInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    query_digest_md5 = serializers.CharField(help_text=_("慢日志摘要"))
    sql_text = serializers.CharField(help_text=_("SQL 文本"))
    db_name = serializers.CharField(help_text=_("database name, 如果这条 sql 上下文没有找到 db_name, 则为空字符串"))


class MysqlSlowTunerOutputSerializer(serializers.Serializer):
    content = serializers.CharField(help_text=_("慢日志分析结果"))
