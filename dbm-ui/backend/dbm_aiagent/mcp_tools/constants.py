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


class DBMMcpTools(StrStructuredEnum):
    DBM = EnumField("dbm-mcp", "DBM")
    DBMETA_QUERY = EnumField("dbmeta-query", "dbmeta-query")
    DBMETA_UPDATE = EnumField("dbmeta-update", "dbmeta-update")
    MYSQL_QUERY = EnumField("mysql-query", "mysql-query")
    MYSQL_LOG = EnumField("mysql-log", "mysql-log")
    MYSQL_BILL = EnumField("mysql-bill", "mysql-bill")
    MYSQL_CONFIG = EnumField("mysql-config", "mysql-config")
    MYSQL_SLOWLOG = EnumField("mysql-slowlog", "mysql-slowlog")
    MYSQL_CAPACITY = EnumField("mysql-capacity", "mysql-capacity")
    MYSQL_METRICS = EnumField("mysql-metrics", "mysql-metrics")
    MYSQL_SENSITIVE = EnumField("mysql-sensitive", "mysql-sensitive")
    MYSQL_BACKUP = EnumField("mysql-backup", "mysql-backup")
    SQLSERVER_QUERY = EnumField("sqlserver-query", "sqlserver-query")
    TICKET_OP = EnumField("ticket-op", "ticket-op")
    ALARM_QUERY = EnumField("alarm-query", "alarm-query")
    SQL_SYNTAX_CHECK = EnumField("sql-syntax-check", "sql-syntax-check")
    RESOURCE_QUERY = EnumField("resource-query", "resource-query")
    REDIS_QUERY_META = EnumField("redis-query-meta", "redis-query-meta")
    REDIS_QUERY_STATUS = EnumField("redis-query-status", "redis-query-status")
    REDIS_QUERY_LOG = EnumField("redis-query-log", "redis-query-log")
    REDIS_BIGKEY_LOG = EnumField("redis-bigkey-log", "redis-bigkey-log")
    REDIS_SERVER_LOG = EnumField("redis-server-log", "redis-server-log")
    REDIS_METRICS = EnumField("redis-metrics", "redis-metrics")
    REDIS_REPORTS = EnumField("redis-reports", "redis-reports")
    REDIS_QUERY_ALARM = EnumField("redis-query-alarm", "redis-query-alarm")
    REDIS_BILL = EnumField("redis-bill", "redis-bill")
    REDIS_JOB = EnumField("redis-job", "redis-job")
    MONGODB_META = EnumField("mongodb-meta", "mongodb-meta")
    MONGODB_METRICS = EnumField("mongodb-metrics", "mongodb-metrics")
    MONGODB_LOG = EnumField("mongodb-log", "mongodb-log")
    MONGODB_ALARM = EnumField("mongodb-alarm", "mongodb-alarm")
    # 聚合型 MCP server：同时包含 mongodb-meta/mongodb-log/mongodb-metrics/mongodb-alarm 的 tools
    MONGODB_MCP = EnumField("mongodb-mcp", "mongodb-mcp")
    MONGODB_BILL = EnumField("mongodb-bill", "mongodb-bill")
    KAFKA_QUERY_META = EnumField("kafka-query-meta", "kafka-query-meta")
    KAFKA_BILL = EnumField("kafka-bill", "kafka-bill")
    KAFKA_METRICS = EnumField("kafka-metrics", "kafka-metrics")
    HOST_DECOMMISSION_QUERY = EnumField("host-decommission-query", _("主机裁撤信息查询"))
    HOST_PERFORMANCE_QUERY = EnumField("host-performance-query", _("主机性能查询"))
    TASKFLOW_QUERY = EnumField("taskflow-query", _("任务流查询"))
    KAFKA_TOOLBOX = EnumField("kafka-toolbox", "kafka-toolbox")
    PROMQL_QUERY = EnumField("promql-query", _("通用PromQL指标查询"))
    AI_REPORT = EnumField("ai-report", _("AI分析报告"))
    CLUSTER_PORTRAIT = EnumField("cluster-portrait", _("集群画像基础mcp工具集合"))
    # MARKET
    DBM_PUBLIC_MARKET = EnumField("dbm-public-market", _("DBM公共服务"))
    RESOURCE_POOL = EnumField("resource-pool", "resource-pool")
    # 3rd platform wrap
    BKCC_WRAP = EnumField("bkcc-wrap", _("bkcc-wrap"))
    BKJOB_WRAP = EnumField("bkjob-wrap", _("bkjob-wrap"))
    RESOURCE_REPLENISH = EnumField("resource-replenish", "resource-replenish")
    PULSAR_QUERY_META = EnumField("pulsar-query-meta", "pulsar-query-meta")
    PULSAR_BILL = EnumField("pulsar-bill", "pulsar-bill")
    PULSAR_METRICS = EnumField("pulsar-metrics", "pulsar-metrics")
    PULSAR_TOOLBOX = EnumField("pulsar-toolbox", "pulsar-toolbox")


class DBMMCPTags(StrStructuredEnum):
    READ = EnumField("read", _("只读"))
    WRITE = EnumField("write", _("可写"))
    MCP_TOOLS = EnumField("mcp-tools", _("MCP工具"))
