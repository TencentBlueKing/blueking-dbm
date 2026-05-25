# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 索引分析功能域

包含面向"SQL 优化分析"的只读 DMV 工具，按 P0/P1 分层：
    P0（必备 / 主分析依据）
        - get_table_schema       表结构（列、类型、可空、计算列、约束）
        - get_table_indexes      现有索引（键列、INCLUDE、唯一性、行数、压缩）
        - get_table_stats        统计信息状态（最近更新、采样、修改行数、是否过期）
    P1（增强 / 辅助决策）
        - get_index_usage_stats   索引使用画像（seek/scan/lookup/update）
        - get_index_fragmentation 索引碎片率（决定 REORG/REBUILD）

故意不实现 missing_index 建议：建议质量低、与具体 SQL 不强相关，不作为分析主依据。
"""
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.index_fragmentation import (
    sqlserver_get_index_fragmentation,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.index_usage_stats import (
    sqlserver_get_index_usage_stats,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.table_indexes import sqlserver_get_table_indexes
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.table_schema import sqlserver_get_table_schema
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.index_analysis.table_stats import sqlserver_get_table_stats

__all__ = [
    "sqlserver_get_table_schema",
    "sqlserver_get_table_indexes",
    "sqlserver_get_table_stats",
    "sqlserver_get_index_usage_stats",
    "sqlserver_get_index_fragmentation",
]
