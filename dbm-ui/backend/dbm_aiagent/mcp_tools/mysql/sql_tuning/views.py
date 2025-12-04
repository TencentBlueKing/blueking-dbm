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
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.sql_tuning.impl.explain_sql import explain_sql
from backend.dbm_aiagent.mcp_tools.mysql.sql_tuning.impl.show_create_table import show_create_table
from backend.dbm_aiagent.mcp_tools.mysql.sql_tuning.serializers.explain_sql_serializer import (
    ExplainSQLInputSerializer,
    ExplainSQLOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.sql_tuning.serializers.show_create_table_serializer import (
    ShowCreateTableInputSerializer,
    ShowCreateTableOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission


class MySQLSQLTuningMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取表结构")),
        request_slz=ShowCreateTableInputSerializer,
        response_slz=ShowCreateTableOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_SQL_TUNING],
    )
    def show_create_table(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        tablename = self.get_param("tablename")

        return Response(
            show_create_table(
                cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname, tablename=tablename
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 SQL 执行计划")),
        request_slz=ExplainSQLInputSerializer,
        response_slz=ExplainSQLOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_SQL_TUNING],
    )
    def explain_sql(self, request, *args, **kwargs):
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        dbname = self.get_param("dbname")
        query_sql = self.get_param("query_sql")

        return Response(
            explain_sql(cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname, query_sql=query_sql)
        )
