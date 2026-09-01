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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_slowlog import query_slowlog_aggregated
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_slowlog import (
    SlowlogAggregatedInputSerializer,
    SlowlogAggregatedOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class MySQLSlowlogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的慢查询统计信息")),
        request_slz=SlowlogAggregatedInputSerializer,
        response_slz=SlowlogAggregatedOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_slowlog",
    )
    def query_aggregated(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        instance_role = self.get_param("instance_role")
        order_by = self.get_param("metric_name")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")
        query_sample = self.get_param("query_sample")
        exclude_system = self.get_param("exclude_system")

        return Response(
            query_slowlog_aggregated(
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                start_time=start_time,
                end_time=end_time,
                order_by=order_by,
                limit=limit,
                query_sample=query_sample,
                exclude_system=exclude_system,
            )
        )
