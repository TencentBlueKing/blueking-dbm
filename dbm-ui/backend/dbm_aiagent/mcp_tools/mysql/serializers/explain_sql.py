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


class ExplainSQLInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    db_name = serializers.CharField(help_text=_("库名, 为空时会自动使用 query_sql 里面的库名"), required=False)
    query_sql = serializers.CharField(help_text=_("需要查询执行计划的 SQL 语句，不需要带 explain"))


class ExplainSQLOutputSerializer(serializers.Serializer):
    explain_result = serializers.DictField(help_text=_("explain sql 的执行计划结果"))
    explained_sql = serializers.CharField(
        help_text=_("实际被 EXPLAIN 的 SQL；UPDATE/DELETE/INSERT...SELECT 会被改写为等价 SELECT"),
    )
    rewritten = serializers.BooleanField(
        help_text=_("用户提供的 SQL 是否被改写。改写后的执行计划与原始 DML 高度相近但不完全相同"),
    )
