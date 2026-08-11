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

from backend.dbm_aiagent.mcp_tools.mysql.views import (
    MySQLBillMcpToolsViewSet,
    MySQLConfigUpdateMcpToolsViewSet,
    MySQLMetricsMcpToolsViewSet,
    MySQLProxyConnlogMcpToolsViewSet,
    MySQLQueryMcpToolsViewSet,
    MySQLSensitiveMcpViewSet,
    MySQLSlowlogMcpToolsViewSet,
    MySQLTableCapacityMcpToolsViewSet,
    SqlSyntaxCheckMcpViewSet,
)
from backend.dbm_aiagent.mcp_tools.mysql.views.bkjob_wrap.viewset import BKJobWrapMcpToolsViewSet
from backend.dbm_aiagent.mcp_tools.mysql.views.mysql_backup_mcp import MySQLBackupMcpToolsViewSet

routers = DefaultRouter(trailing_slash=True)

routers.register(r"", MySQLQueryMcpToolsViewSet, basename="mcp-mysql-query")
routers.register(r"", MySQLBillMcpToolsViewSet, basename="mcp-mysql-bill")
routers.register(r"", MySQLSlowlogMcpToolsViewSet, basename="mcp-mysql-slowlog")
routers.register(r"", SqlSyntaxCheckMcpViewSet, basename="mcp-sql-syntax-check")
routers.register(r"", MySQLMetricsMcpToolsViewSet, basename="mcp-mysql-metrics")
routers.register(r"", MySQLConfigUpdateMcpToolsViewSet, basename="mcp-mysql-config-update")
routers.register(r"", MySQLTableCapacityMcpToolsViewSet, basename="mcp-mysql-table-capacity")
routers.register(r"", MySQLSensitiveMcpViewSet, basename="mcp-mysql-sensitive")
routers.register(r"", MySQLBackupMcpToolsViewSet, basename="mcp-mysql-backup")
routers.register(r"", MySQLProxyConnlogMcpToolsViewSet, basename="mcp-mysql-proxy-connlog")
routers.register(r"", BKJobWrapMcpToolsViewSet, basename="mcp-bkjob-wrap")
urlpatterns = routers.urls
