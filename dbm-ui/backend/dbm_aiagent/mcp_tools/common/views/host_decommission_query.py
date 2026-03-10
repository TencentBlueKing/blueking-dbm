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

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_services.risk_memo.constants import Status
from backend.db_services.risk_memo.models.risk_memo import RiskMemo
from backend.dbm_aiagent.mcp_tools.common.impl.query_cluster_by_ip import query_cluster_by_ip
from backend.dbm_aiagent.mcp_tools.common.serializers.query_cluster_by_ip import (
    QueryClusterByIpInputSerializer,
    QueryClusterByIpOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.query_risk_by_cluster import (
    QueryRiskByClusterInputSerializer,
    QueryRiskByClusterOutputSerializer,
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

    @mcp_tools_api_decorator(
        description="Query active risk memos by biz_id and cluster domain (DBA only). "
        "Returns: id, name, bk_biz_id, level, status, db_type, description, biz_inpact, is_special, creator, create_at. "
        "Excludes done/closed risks.",
        request_slz=QueryRiskByClusterInputSerializer,
        response_slz=QueryRiskByClusterOutputSerializer,
        permission_classes=[McpIsDbaPermission],
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HOST_DECOMMISSION_QUERY],
        name_prefix="host_decommission_query",
    )
    def query_risk_by_cluster(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        # impact_cluster 存储逗号分隔多域名，需精确匹配，避免子串误命中
        # 排除已结项（DONE）的风险备忘录
        risks = (
            RiskMemo.objects.filter(bk_biz_id=bk_biz_id)
            .exclude(status=Status.DONE.value)
            .filter(
                Q(inpact_cluster=cluster_domain)
                | Q(inpact_cluster__startswith=f"{cluster_domain},")
                | Q(inpact_cluster__endswith=f",{cluster_domain}")
                | Q(inpact_cluster__contains=f",{cluster_domain},")
            )
            .values(
                "id",
                "name",
                "bk_biz_id",
                "level",
                "status",
                "db_type",
                "description",
                "biz_inpact",
                "is_special",
                "creator",
                "create_at",
            )
        )
        return Response({"risks": list(risks)})
