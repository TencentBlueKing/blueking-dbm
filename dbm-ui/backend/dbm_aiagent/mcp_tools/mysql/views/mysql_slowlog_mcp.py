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

from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_slowlog import query_slow_logs
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_slowlog import (
    MysqlSlowlogInputSerializer,
    MysqlSlowlogOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

logger = logging.getLogger("root")


class MySQLSlowlogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取 tendbsingle, tendbha, tendbcluster 集群的慢查询统计信息")),
        request_slz=MysqlSlowlogInputSerializer,
        response_slz=MysqlSlowlogOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.MYSQL_SLOWLOG],
        name_prefix="mysql_slowlog",
    )
    def query_mysql_slow_logs(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")  # noqa: F841
        cluster_type = self.get_param("cluster_type")
        cluster_domain = self.get_param("cluster_domain")
        instance_role = self.get_param("instance_role")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")

        return Response(
            query_slow_logs(
                cluster_type=cluster_type,
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                start_time=start_time,
                end_time=end_time,
            )
        )
