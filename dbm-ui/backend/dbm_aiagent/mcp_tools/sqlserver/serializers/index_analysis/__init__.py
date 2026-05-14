# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

索引分析功能域 - serializers 包
"""
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.index_fragmentation import (
    SQLServerIndexFragmentationInputSerializer,
    SQLServerIndexFragmentationOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.index_usage_stats import (
    SQLServerIndexUsageStatsInputSerializer,
    SQLServerIndexUsageStatsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.table_indexes import (
    SQLServerTableIndexesInputSerializer,
    SQLServerTableIndexesOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.table_schema import (
    SQLServerTableSchemaInputSerializer,
    SQLServerTableSchemaOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.table_stats import (
    SQLServerTableStatsInputSerializer,
    SQLServerTableStatsOutputSerializer,
)

__all__ = [
    "SQLServerTableSchemaInputSerializer",
    "SQLServerTableSchemaOutputSerializer",
    "SQLServerTableIndexesInputSerializer",
    "SQLServerTableIndexesOutputSerializer",
    "SQLServerTableStatsInputSerializer",
    "SQLServerTableStatsOutputSerializer",
    "SQLServerIndexUsageStatsInputSerializer",
    "SQLServerIndexUsageStatsOutputSerializer",
    "SQLServerIndexFragmentationInputSerializer",
    "SQLServerIndexFragmentationOutputSerializer",
]
