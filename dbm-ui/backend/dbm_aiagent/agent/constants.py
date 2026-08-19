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

FLOW_LOG_AI_ANALYSIS_KEY = "flow_log_ai_analysis"

DEFAULT_AGENT_CHAT_TIMEOUT = 600

# 风险报告语义比对的 prompt 模板
RISK_COMPARE_PROMPT = _(
    """你现在是一个风险报告比对分析师。请判断以下两份风险报告是否描述的是**同一个风险问题**。

## 判断标准
- 如果两份报告的**核心风险点相同**（比如都在说CPU负载高、都在说磁盘空间不足），即使措辞不同、数值略有差异、时间区间不同，也视为**相同风险**。
- 如果两份报告描述的是**不同类型的风险问题**（比如一个说CPU高、另一个说磁盘不足），则视为**不同风险**。
- 如果某份报告包含了新的风险点（即使同时也包含旧的风险点），也视为**不同风险**。

## 上一次风险报告
{last_report}

## 本次风险报告
{current_report}

## 输出要求
只需要输出一个JSON，不要输出其他内容：
- 相同风险：{{"is_same_risk": true, "reason": "简短说明原因"}}
- 不同风险：{{"is_same_risk": false, "reason": "简短说明原因"}}
"""
)


class DBMAgentCode(StrStructuredEnum):
    DBM = EnumField("ai-dbm", _("DBM 主智能体"))
    LOG_ANALYSIS = EnumField("ai-loganalysis", _("日志分析智能体"))
    MYSQL_SLOW_SQL_TUNER = EnumField("ai-sql-tune", _("MySQL 慢查询调优智能体"))
    MYSQL_SLOW_LOGS_QUERY = EnumField("ai-mysql-slowlog", _("MySQL慢日志分析智能体"))
    MYSQL_AI_INSPECT_AGENT = EnumField("ai-mysql-inspect", _("MySQL智能巡检"))
    TASK_GUARDIAN = EnumField("ai-task-guardian", _("单据值守智能体"))
    MYSQL_TASK_GUARDIAN = EnumField("ai-mysql-taskgd", _("MySQL单据值守智能体"))
    SQLSERVER_TASK_GUARDIAN = EnumField("ai-sqlsvr-tgd", _("SQLServer单据值守智能体"))
    REDIS_HELPER = EnumField("ai-tendis-agent", _("Redis智能助手"))
    REDIS_TASK_GUARDIAN = EnumField("ai-redis-taskgd", _("Redis单据值守"))
    REDIS_REPORT = EnumField("ai-tendis-report", _("Redis汇报助手"))
    REDIS_LOG_ANA = EnumField("ai-redis-logana", _("Redis日志解析"))
    REDIS_TOOLS = EnumField("ai-redis-wb", _("Redis工具箱"))
    REDIS_METRICS = EnumField("ai-tendismetrics", _("Redis指标助手"))
    REDIS_CLUSTER_CAPACITY_GROWTH_CHECK = EnumField("ai-rds-capchk", _("Redis集群容量增长检查"))
    REDIS_BACKEND_LOAD_SKEW_CHECK = EnumField("ai-rds-loadskew", _("Redis后端负载均衡检查"))
    REDIS_BACKEND_DATA_SKEW_CHECK = EnumField("ai-rds-dataskew", _("Redis后端数据倾斜检查"))
    REDIS_EXERCISE_ANALYST = EnumField("ai-redis-exana", _("Redis演练分析"))
    KAFKA_TASK_GUARDIAN = EnumField("ai-kafka-taskgd", _("Kafka单据值守"))
    ES_TASK_GUARDIAN = EnumField("ai-es-taskgd", _("ES单据值守"))
    MONGO_TASK_GUARDIAN = EnumField("ai-mongo-taskgd", _("MongoDB单据值守"))
    PULSAR_TASK_GUARDIAN = EnumField("ai-pulsar-taskgd", _("Pulsar单据值守"))
    HDFS_TASK_GUARDIAN = EnumField("ai-hdfs-taskgd", _("HDFS单据值守"))
    DORIS_TASK_GUARDIAN = EnumField("ai-doris-taskgd", _("Doris单据值守"))
    MYSQL_WORKBENCH = EnumField("ai-mysql-workb", _("ai-mysql-workb"))
    MYSQL_SKEW_REPORT = EnumField("ai-mysql-skew", _("MySQL 集群倾向报告"))
    MYSQL_CONFIG_PERF_TUNER = EnumField("ai-db-perf-tuner", _("MySQL配置优化智能体"))
    MYSQL_PORTRAIT_CLUSTER = EnumField("ai-c-report", _("MySQL 集群画像"))
