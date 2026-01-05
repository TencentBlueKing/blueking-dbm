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

from backend.components.dbresource.client import DBResourceApi
from backend.dbm_aiagent.mcp_tools.common.serializers.resource_param_query import (
    ResourceParamQueryInputSerializer,
    ResourceParamQueryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")


class ResourceParamQueryMcpToolsViewSet(McpToolsViewSet):
    """
    ViewSet for resource parameter query MCP tools.
    Provides functionality to query resource request parameters by bill_id or task_id.
    """

    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Query resource request parameters by bill_id or task_id. "
                "This tool retrieves the resource allocation parameters submitted during ticket/task execution, "
                "useful for debugging resource issues or auditing resource requests. "
                "根据单据ID(bill_id)或任务ID(task_id)查询资源请求参数。"
                "用于获取单据/任务执行时提交的资源申请参数，适用于排查资源问题或审计资源请求。"
            )
        ),
        request_slz=ResourceParamQueryInputSerializer,
        response_slz=ResourceParamQueryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.RESOURCE_QUERY],
        name_prefix="resource_query",
    )
    def resource_param_query(self, request, *args, **kwargs):
        """
        Query resource request parameters by bill_id or task_id.
        This method calls DBResourceApi.resource_param_query to retrieve
        the resource request parameters associated with the given identifiers.
        """
        bill_id = self.get_param("bill_id")
        task_id = self.get_param("task_id")
        latest = self.get_param("latest")

        # Build request parameters for the API call
        params = {"latest": latest}
        if bill_id:
            params["bill_id"] = bill_id
        if task_id:
            params["task_id"] = task_id

        # Call DBResourceApi to query resource parameters
        result = DBResourceApi.resource_param_query(params)

        return Response({"data": result})
