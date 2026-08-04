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

from backend.dbm_aiagent.mcp_tools.common.views import (
    AiReportMcpToolsViewSet,
    ClusterPortraitMcpToolsViewSet,
    DBMetaQueryMcpToolsViewSet,
    DBMetaUpdateMcpToolsViewSet,
    HcmResourceReplenishMcpToolsViewSet,
    HostDecommissionQueryMcpToolsViewSet,
    HostPerformanceQueryMcpToolsViewSet,
    PromQLQueryMcpToolsViewSet,
    ResourceParamQueryMcpToolsViewSet,
    TaskflowQueryMcpToolsViewSet,
    TicketOperationMcpToolsViewSet,
)
from backend.dbm_aiagent.mcp_tools.common.views.alarm_query import MonitorQueryMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.common.views.bkcc_wrap import BKCCWrapMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.common.views.bkjob_wrap.viewset import BKJobWrapMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.common.views.mcp_callee_plan import McpCalleePlanMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register(r"", DBMetaQueryMcpToolsViewSet, basename="mcp-dbmeta-query")
routers.register(r"", DBMetaUpdateMcpToolsViewSet, basename="mcp-dbmeta-update")
routers.register(r"", TicketOperationMcpToolsViewSet, basename="mcp-ticket-query")
routers.register(r"", ResourceParamQueryMcpToolsViewSet, basename="mcp-resource-query")
routers.register(r"", MonitorQueryMcpToolsViewSet, basename="mcp-monitor-query")
routers.register(r"", HostDecommissionQueryMcpToolsViewSet, basename="mcp-host-decommission-query")
routers.register(r"", HostPerformanceQueryMcpToolsViewSet, basename="mcp-host-performance-query")
routers.register(r"", TaskflowQueryMcpToolsViewSet, basename="mcp-taskflow-query")
routers.register(r"", PromQLQueryMcpToolsViewSet, basename="mcp-promql-query")
routers.register(r"", McpCalleePlanMcpToolsViewSet, basename="mcp-callee-plan")
routers.register(r"", AiReportMcpToolsViewSet, basename="mcp-ai-report")
routers.register(r"", ClusterPortraitMcpToolsViewSet, basename="mcp-cluster-portrait")
routers.register(r"", BKCCWrapMcpToolsViewSet, basename="mcp-bkcc-wrap")
routers.register(r"", BKJobWrapMcpToolsViewSet, basename="mcp-bkjob-wrap")
routers.register(r"", HcmResourceReplenishMcpToolsViewSet, basename="mcp-resource-replenish")
urlpatterns = routers.urls
