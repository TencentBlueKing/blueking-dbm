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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.configuration.constants import DBType
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    auth_parse_bizs,
    auth_parse_cluster_biz,
    auth_parse_clusters,
    auth_parse_my_bizs,
)
from backend.dbm_aiagent.mcp_tools.common.impl.biz_helpers import get_managed_biz
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_reports import (
    create_report_record,
    query_redis_reports_by_biz,
    query_redis_reports_by_cluster,
    resolve_biz_ids_for_query,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_reports import (
    AddReportRecordInputSerializer,
    AddReportRecordOutputSerializer,
    RedisReportsByBizInputSerializer,
    RedisReportsByClusterInputSerializer,
    RedisReportsByMyBizsInputSerializer,
    RedisReportsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.env import DEFAULT_USERNAME
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission, McpDBManagePermission


class RedisReportsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Query Redis inspection reports by business (bk_biz_id or bk_biz_abbr), cluster, subtype, state, and time range"
            )
        ),
        request_slz=RedisReportsByBizInputSerializer,
        response_slz=RedisReportsOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_REPORTS],
        name_prefix="redis_reports",
    )
    def query_reports_by_biz(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        app_abbr = self.get_param("app_abbr")
        bk_biz_ids = resolve_biz_ids_for_query(bk_biz_id=bk_biz_id, app_abbr=app_abbr)
        subtypes = self.get_param("subtypes")
        states = self.get_param("states")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_redis_reports_by_biz(
                bk_biz_ids=bk_biz_ids,
                subtypes=subtypes,
                states=states,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _("Create a Redis check report record (subtype: agent_universal or other agent-creatable subtypes)")
        ),
        request_slz=AddReportRecordInputSerializer,
        response_slz=AddReportRecordOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_cluster_biz,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.REDIS_REPORTS],
        name_prefix="redis_reports",
    )
    def add_report_record(self, request, *args, **kwargs):
        creator = self.get_param("creator")
        if not creator:
            creator = getattr(request.user, "username", "agent_check") or "agent_check"
            if creator == DEFAULT_USERNAME:
                creator = "agent_check"
        return Response(
            create_report_record(
                subtype=self.get_param("subtype"),
                cluster_domain=self.get_param("cluster_domain"),
                msg=self.get_param("msg"),
                creator=creator,
                state=self.get_param("state"),
                shard=self.get_param("shard"),
                instance=self.get_param("instance"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("Query Redis inspection reports by cluster domain")),
        request_slz=RedisReportsByClusterInputSerializer,
        response_slz=RedisReportsOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_REPORTS],
        name_prefix="redis_reports",
    )
    def query_reports_by_cluster(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        subtypes = self.get_param("subtypes")
        states = self.get_param("states")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_redis_reports_by_cluster(
                cluster_domain=cluster_domain,
                subtypes=subtypes,
                states=states,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _('Query Redis inspection reports across user\'s managed bizs (non-normal: states=["warning","abnormal"])')
        ),
        request_slz=RedisReportsByMyBizsInputSerializer,
        response_slz=RedisReportsOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_my_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_REPORTS],
        name_prefix="redis_reports",
    )
    def query_reports_by_my_bizs(self, request, *args, **kwargs):
        bk_biz_ids = get_managed_biz(request.user.username, DBType.Redis)
        subtypes = self.get_param("subtypes")
        states = self.get_param("states")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        limit = self.get_param("limit")

        return Response(
            query_redis_reports_by_biz(
                bk_biz_ids=bk_biz_ids,
                subtypes=subtypes,
                states=states,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )
        )
