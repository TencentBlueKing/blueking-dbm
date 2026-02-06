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


class MysqlOneSlowlogInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    query_digest_md5 = serializers.CharField(help_text=_("慢日志摘要，query_digest 与 query_digest_md5 是同一个意思"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))


class MysqlSlowTunerInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    query_digest_md5 = serializers.CharField(help_text=_("慢日志摘要"))
    sql_text = serializers.CharField(help_text=_("SQL 文本"))
    db_name = serializers.CharField(help_text=_("database name"))


class MysqlSlowTunerOutputSerializer(serializers.Serializer):
    content = serializers.CharField(help_text=_("慢日志分析结果"))
