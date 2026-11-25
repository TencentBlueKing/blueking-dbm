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

from rest_framework.routers import DefaultRouter

from backend.dbm_aiagent.mcp_tools.hdfs.views.hdfs_metrics_mcp import HdfsMetricsMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.hdfs.views.hdfs_query_meta_mcp import HdfsQueryMetaMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.hdfs.views.hdfs_toolbox_mcp import HdfsToolboxMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

# 监控指标查询
routers.register(r"", HdfsMetricsMcpToolsViewSet, basename="mcp-hdfs-metrics")
# 与元数据相关的 query
routers.register(r"", HdfsQueryMetaMcpToolsViewSet, basename="mcp-hdfs-query-meta")
# 库表目录数据量。在 DataNode 上执行 hdfs dfs
routers.register(r"", HdfsToolboxMcpToolsViewSet, basename="mcp-hdfs-toolbox")

urlpatterns = routers.urls
