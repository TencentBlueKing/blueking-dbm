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

import os

from backend import env

# 智能体配置
BK_APIGW_MCP_TIMEOUT = 300
AIDEV_AGENT = "aidev_agent.services.common_agent.CommonQAAgent"
AIDEV_RESOURCE_MANAGER = "backend.dbm_aiagent.agent.configs.manager.DBMAgentResourceManager"
AGENT_APP_CODE = env.BK_AIDEV_AGENT_APP_CODE or env.APP_CODE
AGENT_APP_SECRET = env.BK_AIDEV_AGENT_APP_SECRET or env.SECRET_KEY
BK_AIDEV_APIGW_ENDPOINT = env.BK_AIDEV_APIGW_ENDPOINT

# 智能体客服渠道
CHAT_GROUP_ENABLED = os.environ.get("CHAT_GROUP_ENABLED") == "1"
CHAT_GROUP_STAFF = os.environ.get("CHAT_GROUP_STAFF")
CHAT_GROUP_STAFF = [i.strip() for i in CHAT_GROUP_STAFF.split(",")] if CHAT_GROUP_STAFF else []
CHAT_GROUP_TYPE = os.environ.get("CHAT_GROUP_TYPE", "qyweixin_chat_group")

# 开启MCP server
BK_APIGW_STAGE_ENABLE_MCP_SERVERS = env.BK_APIGW_STAGE_ENABLE_MCP_SERVERS
BK_APIGW_STAGE_MCP_SERVERS = [
    {
        "name": "dbm-mcp",
        "description": "dbm-mcp",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["dbm"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-query",
        "description": """mysql relate information query, such as
        1. mysql instance status, include run-time variables, status, explain sql and so on
        2. tendbsingle/tendbha/tendbcluster cluster info""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-query"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-bill",
        "description": """create mysql bill""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-bill"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-slowlog",
        "description": """query mysql slow logs, include slow logs list and slow log detail""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-slowlog"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-metrics",
        "description": """query mysql metrics like cpu usage, qps summary,
        slow queries count,connections,threads_running""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-metrics"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-capacity",
        "description": """query mysql capacity info""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-capacity"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-config",
        "description": """query or update mysql tools's config, like backup,mysql_monitor,checksum""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-config"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mysql-backup",
        "description": """query mysql backup""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-backup"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "dbmeta-query",
        "description": """query dbm meta info""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["dbmeta-query"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "sqlserver-query",
        "description": """sqlserver relate information query, such as
        1. query result has slow queries count, query_time, rows_scan,rows_sent
        2. need cluster_domain and instance_role provided
        """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["sqlserver-query"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "title": "DBM TenDBHA/TenDBCluster SQL语法检查",
        "name": "sql-syntax-check",
        "description": """SQL syntax check and validation services for TenDBHA/TenDBCluster.
        SQL语法检查与验证服务，适用于TenDBHA/TenDBCluster集群。

        Features / 功能:
        1. Validate SQL syntax across MySQL 5.5/5.6/5.7/8.0 versions - 支持多版本MySQL语法验证
        2. Check DBM platform constraints (banned commands, high-risk operations) - 检查DBM平台约束（禁用命令、高风险操作）
        3. SQL statement/file compatibility checking - SQL语句/文件兼容性检查

        Use Cases / 使用场景:
        - Validate SQL before execution to prevent syntax errors - 执行前验证SQL防止语法错误
        - Check SQL compatibility across different MySQL versions - 检查SQL在不同MySQL版本的兼容性
        - Detect banned commands (e.g., TRUNCATE) and high-risk operations (e.g., DROP DATABASE) - 检测禁用命令和高风险操作
        """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["sql-syntax-check"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": True,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "ticket-op",
        "description": """dbm 单据通用操作. 提单不在这里""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["ticket-op"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "resource-query",
        "description": """DB resource management services, including:
        1. Query resource request parameters by bill_id or task_id
        2. Resource allocation and management
        """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["resource-query"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-query-meta",
        "description": """redis meta query. """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-query-meta"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-query-status",
        "description": """ redis instance running info.""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-query-status"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-query-log",
        "description": """redis的日志查询服务""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-query-log"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-query-alarm",
        "description": """redis的告警查询服务""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-query-alarm"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-bill",
        "description": """create redis bill""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-bill"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "redis-job",
        "description": """Redis Job platform operation services""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-job"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "redis-metrics",
        "description": """Redis Metrics tools""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-metrics"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "redis-reports",
        "description": """Redis reports query tools""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["redis-reports"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "alarm-query",
        "description": """收集DBM集群的告警记录""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["alarm-query"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "dbmeta-update",
        "description": """Database metadata update services for DBM platform.
        DBM平台数据库元数据更新服务。
        Constraints / 约束条件:
        - Only business DBA primary can perform update operations - 只有业务 DBA 主负责人可执行更新操作
        """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["dbmeta-update"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "kafka-query-meta",
        "description": """Kafka cluster meta information query services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["kafka-query-meta"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "kafka-bill",
        "description": """Kafka bill creation services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["kafka-bill"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "kafka-metrics",
        "description": """Kafka cluster monitoring metrics query services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["kafka-metrics"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "mongodb-mcp",
        "description": """Aggregated MongoDB MCP server: include mongodb-meta/mongodb-log/mongodb-metrics/mongodb-alarm tools""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mongodb-mcp"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "mongodb-bill",
        "description": """Create MongoDB cluster apply tickets: replica set and sharded cluster deployment.
        MongoDB 副本集/分片集群部署单据。""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mongodb-bill"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "host-decommission-query",
        "description": """Cluster decommission information query services for DBA only.
        根据单个 IP 查询主机所属集群的裁撤相关信息，仅 DBA 可调用。
        """,
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["host-decommission-query"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "host-performance-query",
        "description": """Host hardware and baseline performance query: by IP (DBA) or by cluster/domain
        with optional instance_roles filter. Returns machine summary, host baseline, and per-mount disk baselines.
        主机硬件与基线性能查询：按 IP（DBA）或按集群/域名及可选实例角色过滤，返回主机摘要、机型基线与各挂载点磁盘基线。
        """,
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["host-performance-query"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "taskflow-query",
        "description": """Task flow query services for DBM.

        Features:
        1. Query the last failed node's error logs by task flow root_id
        2. List failed task flow root_ids by date range and ticket type

        Use Cases:
        - Diagnose task flow failures by retrieving error logs of the last failed node
        - Batch query failed task flows within a specified time range for troubleshooting
        """,
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["taskflow-query"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "kafka-toolbox",
        "description": """Kafka toolbox services for executing Kafka CLI commands on broker nodes,
        including topic/consumer-group inspection and topic config management""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["kafka-toolbox"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "title": "[DBM] 公共服务",
        "name": "dbm-public-market",
        "description": """dbm 公共服务""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["dbm-public-market"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": True,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "title": "mysql-sensitive",
        "name": "mysql-sensitive",
        "description": """mysql 敏感服务""",
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["mysql-sensitive"],
        "status": 1,
        "is_public": False,
        "tools": [],
    },
    {
        "name": "ai-report",
        "description": """read or write ai report with markdown/html format""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["ai-report"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "resource-pool",
        "description": """resource pool host query and operate """,
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["resource-pool"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "bkcc-wrap",
        "description": """bkcc api wrap""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["bkcc-wrap"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "bkjob-wrap",
        "description": """bkjob api wrap, include fast execute script and query job result""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["bkjob-wrap"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "cluster-portrait",
        "description": """集群画像基础mcp工具集合""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["cluster-portrait"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "pulsar-query-meta",
        "description": """Pulsar cluster meta information query services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["pulsar-query-meta"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "pulsar-bill",
        "description": """Pulsar bill creation services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["pulsar-bill"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "pulsar-metrics",
        "description": """Pulsar cluster monitoring metrics query services""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["pulsar-metrics"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
    {
        "name": "pulsar-toolbox",
        "description": """Pulsar toolbox services for executing pulsar-admin CLI commands on broker nodes,
        including tenant/namespace/topic inspection and subscription backlog analysis""",
        # 主动授权 app_code
        "target_app_codes": [env.APP_CODE, "ai-dbm"],
        "labels": ["pulsar-toolbox"],
        # 是否启用：1-启用，0-停止
        "status": 1,
        # 是否公开
        "is_public": False,
        # 自动发现并填充该 MCP 服务器对应的工具
        "tools": [],
    },
]

__all__ = [
    "BK_APIGW_MCP_TIMEOUT",
    "BK_APIGW_STAGE_ENABLE_MCP_SERVERS",
    "BK_APIGW_STAGE_MCP_SERVERS",
    "AIDEV_AGENT",
    "AIDEV_RESOURCE_MANAGER",
    "AGENT_APP_CODE",
    "AGENT_APP_SECRET",
    "BK_AIDEV_APIGW_ENDPOINT",
    "CHAT_GROUP_ENABLED",
    "CHAT_GROUP_STAFF",
    "CHAT_GROUP_TYPE",
]
