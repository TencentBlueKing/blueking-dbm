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
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.cluster_topo import sqlserver_cluster_topo
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.cluster_topo import (
    SQLServerTopoInputSerializer,
    SQLServerTopoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission


class SqlserverMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询 SQLServer 集群拓扑结构")),
        request_slz=SQLServerTopoInputSerializer,
        response_slz=SQLServerTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.SQLSERVER_QUERY],
        name_prefix="sqlserver_query",
    )
    def cluster_topo(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        return Response(sqlserver_cluster_topo(cluster_domain=cluster_domain))
