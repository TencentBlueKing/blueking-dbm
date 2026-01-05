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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_cluster_type_choices


class SqlSyntaxCheckInputSerializer(serializers.Serializer):
    """Input serializer for SQL syntax check."""

    cluster_type = serializers.ChoiceField(
        choices=mysql_cluster_type_choices,
        help_text=_(
            "Cluster type for the SQL syntax check. "
            "Supported values: 'tendbha' (TenDBHA cluster), 'tendbcluster' or 'spider' (TenDBCluster distributed cluster). "
            "Note: 'spider' is an alias for 'tendbcluster', they are equivalent. "
            "集群类型，支持 'tendbha'（TenDBHA主从集群）、'tendbcluster' 或 'spider'（TenDBCluster分布式集群）。"
            "注意：'spider' 是 'tendbcluster' 的别名，两者等价。"
        ),
    )
    sqls = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "List of SQL statements to check. Each item is a complete SQL statement string. "
            "Example: ['CREATE TABLE t1 (id INT)', 'ALTER TABLE t1 ADD COLUMN name VARCHAR(100)']. "
            "待检查的SQL语句列表，每个元素为完整的SQL语句字符串。"
        ),
    )
    versions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=_(
            "List of MySQL versions for syntax check. "
            "Supported versions: '5.5', '5.6', '5.7', '8.0'. "
            "If not provided, defaults to ['MySQL-5.5', 'MySQL-5.6', 'MySQL-5.7', 'MySQL-8.0']. "
            "MySQL版本列表，支持的版本：5.5、5.6、5.7、8.0。不提供时默认检查所有版本。"
        ),
    )


class SyntaxFailItemSerializer(serializers.Serializer):
    """Serializer for a single syntax error item."""

    error_code = serializers.IntegerField(
        help_text=_("MySQL error code, e.g. 1064 for syntax error. MySQL错误码，如1064表示语法错误。")
    )
    error_msg = serializers.CharField(
        help_text=_("Detailed error message with MySQL version info. " "包含MySQL版本信息的详细错误消息。")
    )
    line = serializers.IntegerField(
        help_text=_("Line number where the syntax error occurred (1-indexed). 语法错误所在的行号（从1开始）。")
    )
    sqltext = serializers.CharField(help_text=_("The SQL statement that caused the error. 导致错误的SQL语句。"))


class HighRiskWarningItemSerializer(serializers.Serializer):
    """Serializer for a single high-risk operation warning item."""

    command_type = serializers.CharField(
        help_text=_(
            "Type of the high-risk command, e.g. 'drop_db', 'drop_table'. " "高风险命令类型，如 'drop_db'（删库）、'drop_table'（删表）。"
        )
    )
    line = serializers.IntegerField(
        help_text=_("Line number where the high-risk command occurred (1-indexed). 高风险命令所在的行号（从1开始）。")
    )
    sqltext = serializers.CharField(
        help_text=_("The SQL statement containing the high-risk operation. 包含高风险操作的SQL语句。")
    )
    warn_info = serializers.CharField(
        help_text=_("Warning information with MySQL version and command details. " "包含MySQL版本和命令详情的警告信息。")
    )


class BanCommandWarningItemSerializer(serializers.Serializer):
    """Serializer for a single banned command warning item."""

    command_type = serializers.CharField(
        help_text=_("Type of the banned command, e.g. 'truncate_table'. " "禁用命令类型，如 'truncate_table'（清空表）。")
    )
    line = serializers.IntegerField(
        help_text=_("Line number where the banned command occurred (1-indexed). 禁用命令所在的行号（从1开始）。")
    )
    sqltext = serializers.CharField(help_text=_("The SQL statement containing the banned command. 包含禁用命令的SQL语句。"))
    warn_info = serializers.CharField(
        help_text=_("Warning information about the banned command and reason. " "关于禁用命令及其原因的警告信息。")
    )


class SqlCheckResultItemSerializer(serializers.Serializer):
    """Serializer for syntax check result of a single SQL file."""

    bancommand_warnings = serializers.ListField(
        child=BanCommandWarningItemSerializer(),
        allow_null=True,
        required=False,
        help_text=_(
            "List of banned command warnings. Banned commands are not allowed by DBM platform. "
            "禁用命令警告列表，这些命令被DBM平台禁止执行。"
        ),
    )
    highrisk_warnings = serializers.ListField(
        child=HighRiskWarningItemSerializer(),
        allow_null=True,
        required=False,
        help_text=_(
            "List of high-risk operation warnings. These commands require extra caution. " "高风险操作警告列表，这些命令需要特别谨慎。"
        ),
    )
    syntax_fails = serializers.ListField(
        child=SyntaxFailItemSerializer(),
        allow_null=True,
        required=False,
        help_text=_(
            "List of syntax errors found in the SQL statements. Empty if no syntax errors. " "SQL语句中发现的语法错误列表，无错误时为空。"
        ),
    )


class SqlSyntaxCheckOutputSerializer(serializers.Serializer):
    """Output serializer for SQL syntax check result.

    The result is a dictionary where keys are SQL file identifiers
    and values contain the check results including warnings and errors.
    """

    result = serializers.DictField(
        child=SqlCheckResultItemSerializer(),
        help_text=_(
            "SQL syntax check results keyed by SQL file identifier. "
            "Each value contains bancommand_warnings, highrisk_warnings, and syntax_fails. "
            "SQL语法检查结果，以SQL文件标识符为键。每个值包含禁用命令警告、高风险警告和语法错误。"
        ),
    )


class SqlFileSyntaxCheckInputSerializer(serializers.Serializer):
    """Input serializer for SQL file syntax check.

    This serializer is used for checking SQL syntax from files on the server.
    The execute_objects parameter is automatically constructed by the backend.
    """

    cluster_type = serializers.ChoiceField(
        choices=mysql_cluster_type_choices,
        help_text=_(
            "Cluster type for the SQL syntax check. "
            "Supported values: 'tendbha' (TenDBHA cluster), 'tendbcluster' or 'spider' (TenDBCluster distributed cluster). "
            "Note: 'spider' is an alias for 'tendbcluster', they are equivalent. "
            "集群类型，支持 'tendbha'（TenDBHA主从集群）、'tendbcluster' 或 'spider'（TenDBCluster分布式集群）。"
            "注意：'spider' 是 'tendbcluster' 的别名，两者等价。"
        ),
    )
    path = serializers.CharField(
        help_text=_(
            "Directory path where SQL files are located on the server. "
            "Example: '/data/sql_files/'. "
            "SQL文件所在的服务器目录路径，如 '/data/sql_files/'。"
        )
    )
    file_list = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "List of SQL file names to check (filenames only, not full paths). "
            "Example: ['create_table.sql', 'alter_table.sql']. "
            "待检查的SQL文件名列表（仅文件名，非完整路径），如 ['create_table.sql', 'alter_table.sql']。"
        ),
    )
    versions = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text=_(
            "List of MySQL versions for syntax check. "
            "Supported versions: '5.5', '5.6', '5.7', '8.0'. "
            "If not provided, defaults to ['MySQL-5.5', 'MySQL-5.6', 'MySQL-5.7', 'MySQL-8.0']. "
            "MySQL版本列表，支持的版本：5.5、5.6、5.7、8.0。不提供时默认检查所有版本。"
        ),
    )
