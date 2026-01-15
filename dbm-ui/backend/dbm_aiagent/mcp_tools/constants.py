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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class DBMAMcpTools(StrStructuredEnum):
    DBM = EnumField("dbm-mcp", "DBM")
    DBMETA_QUERY = EnumField("dbmeta-query", "dbmeta-query")
    MYSQL_QUERY = EnumField("mysql-query", "mysql-query")
    MYSQL_BILL = EnumField("mysql-bill", "mysql-bill")
    MYSQL_SLOWLOG = EnumField("mysql-slowlog", "mysql-slowlog")
    SQLSERVER_QUERY = EnumField("sqlserver-query", "sqlserver-query")
    BILL_QUERY = EnumField("bill-query", "bill-query")
    ALARM_QUERY = EnumField("alarm-query", "alarm-query")
    SQL_SYNTAX_CHECK = EnumField("sql-syntax-check", "sql-syntax-check")
    RESOURCE_QUERY = EnumField("resource-query", "resource-query")
    REDIS_QUERY_META = EnumField("redis-query-meta", "redis-query-meta")
    REDIS_QUERY_STATUS = EnumField("redis-query-status", "redis-query-status")
    REDIS_QUERY_LOG = EnumField("redis-query-log", "redis-query-log")
    REDIS_QUERY_METRIC = EnumField("redis-query-metric", "redis-query-metric")
    REDIS_BILL = EnumField("redis-bill", "redis-bill")
    COMMON_TOOL = EnumField("common-tool", "common-tool")


class DBMMCPTags(StrStructuredEnum):
    READ = EnumField("read", _("只读"))
    WRITE = EnumField("write", _("可写"))
    MCP_TOOLS = EnumField("mcp-tools", _("MCP工具"))
