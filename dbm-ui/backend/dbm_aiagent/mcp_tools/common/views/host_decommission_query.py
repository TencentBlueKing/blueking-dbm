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

from backend.dbm_aiagent.mcp_tools.common.impl.query_cluster_by_ip import query_cluster_by_ip
from backend.dbm_aiagent.mcp_tools.common.serializers.query_cluster_by_ip import (
    QueryClusterByIpInputSerializer,
    QueryClusterByIpOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpIsDbaPermission

logger = logging.getLogger("root")


class HostDecommissionQueryMcpToolsViewSet(McpToolsViewSet):
    """裁撤信息查询工具 ViewSet"""

    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                """根据单个 IP 查询主机所属集群信息，仅 DBA 可调用
返回字段包括:
* 集群域名、集群ID、集群类型、DB类型
* 业务ID
* 主机机型(bk_svr_device_cls_name)、机器类型、规格ID(spec_id)
* 子Zone、城市
* 亲和性(disaster_tolerance_level)
* 关联实例端口列表"""
            )
        ),
        request_slz=QueryClusterByIpInputSerializer,
        response_slz=QueryClusterByIpOutputSerializer,
        permission_classes=[McpIsDbaPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HOST_DECOMMISSION_QUERY],
        name_prefix="host_decommission_query",
    )
    def query_cluster_by_ip(self, request, *args, **kwargs):
        ip = self.get_param("ip")
        bk_cloud_id = self.get_param("bk_cloud_id")

        return Response({"clusters": query_cluster_by_ip(ip=ip, bk_cloud_id=bk_cloud_id)})
