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
from backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check import (
    check_sql_file_grammar,
    parse_sql_file_statement_impl,
    syntax_check_sql_impl,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.sql_syntax_check import (
    ParseSqlFileStatementInputSerializer,
    ParseSqlFileStatementOutputSerializer,
    SqlFileSyntaxCheckInputSerializer,
    SqlSyntaxCheckInputSerializer,
    SqlSyntaxCheckOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpSkipPermission

logger = logging.getLogger("root")


class SqlSyntaxCheckMcpViewSet(McpToolsViewSet):
    """MCP viewset for SQL syntax check."""

    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Check SQL syntax for TenDBHA/TenDBCluster against MySQL 5.5/5.6/5.7/8.0. "
                "Validates syntax errors and DBM constraints (banned commands, high-risk ops). "
                "Use cases: pre-execution validation, cross-version compatibility, detect TRUNCATE/DROP DATABASE."
            )
        ),
        request_slz=SqlSyntaxCheckInputSerializer,
        response_slz=SqlSyntaxCheckOutputSerializer,
        permission_classes=[McpSkipPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQL_SYNTAX_CHECK, DBMMcpTools.DBM_PUBLIC_MARKET],
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
                "PREREQUISITE: SQL files must be uploaded to BKRepo before calling this tool. "
                "This tool reads files from BKRepo only; it does NOT upload files. "
                "Validates syntax errors and DBM constraints (banned commands, high-risk ops). "
                "path=BKRepo dir (format: /{project}/{repo}/{dir}/), file_list=filenames only."
            )
        ),
        request_slz=SqlFileSyntaxCheckInputSerializer,
        response_slz=SqlSyntaxCheckOutputSerializer,
        permission_classes=[McpSkipPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQL_SYNTAX_CHECK, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="check_sql_file_syntax",
    )
    def check_sql_file_syntax(self, request, *args, **kwargs):
        """
        SQL file grammar check endpoint.

        **Prerequisite**: SQL files MUST be uploaded to BKRepo (蓝鲸制品库) before calling this endpoint.
        This endpoint only reads files that already exist in BKRepo; it does NOT upload files.

        - path: BKRepo directory path where SQL files are stored, e.g. '/bkdbm/sqlfiles/20240101/'
        - file_list: list of SQL filenames (not full paths) that exist in BKRepo under the given path
        - versions: optional MySQL versions to check against; defaults to 5.5, 5.6, 5.7, 8.0
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

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Parse SQL files in BKRepo for command counts; optionally find ALTER/DROP/TRUNCATE tables >= 500MB. "
                "PREREQUISITE: SQL files must be uploaded to BKRepo before calling this tool. "
                "This tool reads files from BKRepo only; it does NOT upload files. "
                "Returns command_counts (all files) and file_command_counts (per file). "
                "Optional cluster_ids: identify large tables. For DDL without db_name, pass execute_objects "
                "(dbnames/ignore_dbnames/sql_files, same as SQL change ticket) to expand real databases. "
                "include_sql_text defaults to false. path=BKRepo dir, file_list=filenames only."
            )
        ),
        request_slz=ParseSqlFileStatementInputSerializer,
        response_slz=ParseSqlFileStatementOutputSerializer,
        permission_classes=[McpSkipPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQL_SYNTAX_CHECK, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="parse_sql_file_statement",
    )
    def parse_sql_file_statement(self, request, *args, **kwargs):
        """
        Parse SQL files from BKRepo: command counts plus optional large ALTER/DROP/TRUNCATE tables.

        **Prerequisite**: SQL files MUST be uploaded to BKRepo before calling this endpoint.

        - path: BKRepo directory path
        - file_list: SQL filenames (not full paths)
        - include_sql_text: optional, default false
        - cluster_ids: optional; when set, return large_tables (>=500MB)
        - execute_objects: optional; expand empty db_name via dbnames - ignore_dbnames
        """
        path = self.get_param("path")
        file_list = self.get_param("file_list")
        include_sql_text = self.get_param("include_sql_text", False)
        cluster_ids = self.get_param("cluster_ids", [])
        execute_objects = self.get_param("execute_objects", [])

        logger.info(
            _(
                "Received SQL file statement parse request. Path: {}, Files: {}, include_sql_text: {}, "
                "cluster_ids: {}"
            ).format(path, file_list, include_sql_text, cluster_ids)
        )

        result = parse_sql_file_statement_impl(
            path=path,
            file_list=file_list,
            include_sql_text=include_sql_text,
            cluster_ids=cluster_ids,
            execute_objects=execute_objects,
        )
        return Response(result)
