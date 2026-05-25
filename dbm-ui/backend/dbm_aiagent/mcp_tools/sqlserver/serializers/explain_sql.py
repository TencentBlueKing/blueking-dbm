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


class SQLServerExplainSQLInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dbname = serializers.CharField(
        help_text=_("目标数据库名，仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}"),
    )
    query_sql = serializers.CharField(
        help_text=_(
            "需要查询执行计划的 SQL 语句；"
            "仅允许 SELECT / WITH(CTE)，不允许多语句、写操作、DDL、xp_/sp_ 调用、WAITFOR、USE/GO 等。"
            "底层走 SET SHOWPLAN_XML ON，仅编译不执行，不会真正读写数据。"
        ),
    )
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时缺省走 master"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class SQLServerExplainSQLOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    explain_xml = serializers.CharField(
        help_text=_("SHOWPLAN_XML 返回的估算执行计划 XML 文本"),
    )
    rewritten = serializers.BooleanField(
        help_text=_("用户提交的 SQL 是否被改写；当前阶段始终为 false"),
    )
    is_trivial = serializers.BooleanField(
        help_text=_("是否为无真实查询计划的平凡语句（如 SELECT 1）；为 true 时无需做深度计划分析"),
        required=False,
        default=False,
    )
