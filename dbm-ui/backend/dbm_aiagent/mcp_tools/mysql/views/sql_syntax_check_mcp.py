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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check import check_sql_file_grammar, syntax_check_sql_impl
from backend.dbm_aiagent.mcp_tools.mysql.serializers.sql_syntax_check import (
    SqlFileSyntaxCheckInputSerializer,
    SqlSyntaxCheckInputSerializer,
    SqlSyntaxCheckOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")


class SqlSyntaxCheckMcpViewSet(McpToolsViewSet):
    """MCP viewset for SQL syntax check."""

    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Check SQL syntax for TenDBHA/TenDBCluster against MySQL 5.5/5.6/5.7/8.0. "
                "Validates syntax errors and DBM constraints (banned commands, high-risk ops). "
                "根据SQL对TenDBHA/TenDBCluster进行语法和平台约束检查（禁用命令、高风险操作）。"
                "Use cases: pre-execution validation, cross-version compatibility, detect TRUNCATE/DROP DATABASE."
            )
        ),
        request_slz=SqlSyntaxCheckInputSerializer,
        response_slz=SqlSyntaxCheckOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQL_SYNTAX_CHECK],
        name_prefix="check_sql_syntax",
    )
    def check_sql_syntax(self, request, *args, **kwargs):
        """
        SQL syntax check endpoint.

        This endpoint validates SQL statements against specified MySQL versions.
        If versions are not provided, it defaults to checking against 5.5, 5.6, 5.7, and 8.0.
        """
        cluster_type = self.get_param("cluster_type")
        sqls = self.get_param("sqls")
        versions = self.get_param("versions", [""])

        # Normalize 'spider' to 'tendbcluster' (they are equivalent)
        # 将 'spider' 标准化为 'tendbcluster'（两者等价）
        if cluster_type == "spider":
            cluster_type = "tendbcluster"

        # For tendbcluster, versions should be empty (no version-specific checks)
        # 对于tendbcluster集群类型，versions应为空（不进行版本特定检查）
        if cluster_type == "tendbcluster":
            versions = []

        logger.info(
            _(
                "Received SQL syntax check request. Cluster type: {}, Versions: {}, Number of SQL statements: {}"
            ).format(cluster_type, versions, len(sqls))
        )

        result = syntax_check_sql_impl(sqls=sqls, cluster_type=cluster_type, versions=versions)

        return Response({"result": result})

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Check SQL file syntax for TenDBHA/TenDBCluster against MySQL 5.5/5.6/5.7/8.0. "
                "Validates server-side SQL files for syntax errors and DBM constraints (banned commands, high-risk ops). "
                "根据服务器SQL文件进行语法和平台约束检查（禁用命令、高风险操作）。"
                "Use cases: batch validate before deployment, cross-version compatibility. path=目录, file_list=文件名列表."
            )
        ),
        request_slz=SqlFileSyntaxCheckInputSerializer,
        response_slz=SqlSyntaxCheckOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQL_SYNTAX_CHECK],
        name_prefix="check_sql_file_syntax",
    )
    def check_sql_file_syntax(self, request, *args, **kwargs):
        """
        SQL file grammar check endpoint.

        This endpoint validates SQL files on the server against specified MySQL versions.
        If versions are not provided, it defaults to checking against 5.5, 5.6, 5.7, and 8.0.
        The execute_objects parameter is automatically constructed by the backend.
        """
        cluster_type = self.get_param("cluster_type")
        path = self.get_param("path")
        file_list = self.get_param("file_list")
        versions = self.get_param("versions", [""])

        # Normalize 'spider' to 'tendbcluster' (they are equivalent)
        # 将 'spider' 标准化为 'tendbcluster'（两者等价）
        if cluster_type == "spider":
            cluster_type = "tendbcluster"

        # For tendbcluster, versions should be empty (no version-specific checks)
        # 对于tendbcluster集群类型，versions应为空（不进行版本特定检查）
        if cluster_type == "tendbcluster":
            versions = []

        logger.info(
            _("Received SQL file syntax check request. " "Cluster type: {}, Path: {}, Files: {}, Versions: {}").format(
                cluster_type, path, file_list, versions
            )
        )

        result = check_sql_file_grammar(cluster_type=cluster_type, path=path, file_list=file_list, versions=versions)

        return Response({"result": result})
