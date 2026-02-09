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
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    cluster_type = serializers.ChoiceField(choices=mysql_cluster_type_choices, help_text=_("集群类型"))
    # instance_role = serializers.ChoiceField(choices=mysql_instance_role_choices, help_text=_("db实例角色"))
    start_time = serializers.DateTimeField(help_text=_("开始时间, 时间格式 2026-01-08T16:33:38+08:00"))
    end_time = serializers.DateTimeField(help_text=_("结束时间, 时间格式 2026-01-08T16:33:38+08:00"))
    metric_name = serializers.ChoiceField(
        choices=mysql_metric_name_choices, help_text=_("mysql 指标名称，" "性能指标有 cpu负载, qps请求量, 慢日志数量，线程数，连接数")
    )


class MysqlMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    datapoints = serializers.JSONField(help_text=_("时序指标结果"))
