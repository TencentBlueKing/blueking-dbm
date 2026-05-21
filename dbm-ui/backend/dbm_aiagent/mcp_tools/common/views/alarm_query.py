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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.query_monitor_alarm_info import QueryMonitorAlarm
from backend.dbm_aiagent.mcp_tools.common.serializers.alarm_query import (
    QueryAlertInputSerializer,
    SearchAlertInputSerializer,
    SearchAlertOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission


class MonitorQueryMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("""根据传入的某个时间区间和某批集群域名列表，查询出时间区间产生的告警记录""")),
        request_slz=SearchAlertInputSerializer,
        response_slz=SearchAlertOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.ALARM_QUERY, DBMMcpTools.DBM_PUBLIC_MARKET],
        name_prefix="alarm_query",
    )
    def query_monitor_alarm_info(self, request, *args, **kwargs):
        bk_biz_id = int(self.get_param("bk_biz_id"))
        cluster_domains = self.get_param("cluster_domains")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        return Response(
            QueryMonitorAlarm.query_alarm_for_cluster_ids(
                bk_biz_id=bk_biz_id,
                cluster_domains=cluster_domains,
                start_time=start_time,
                end_time=end_time,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""查询集群的某段时间内的告警记录，支持传入告警状态。不传则查所有状态""")),
        request_slz=QueryAlertInputSerializer,
        response_slz=SearchAlertOutputSerializer,
        tags=[DBMMCPTags.READ],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        mcp=[DBMMcpTools.MYSQL_METRICS],
        name_prefix="alarm",
    )
    def query_with_status(self, request, *args, **kwargs):
        bk_biz_id = int(self.get_param("bk_biz_id"))
        cluster_domains = self.get_param("cluster_domains")
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        # status = self.get_param("status")
        return Response(
            QueryMonitorAlarm.query_alarm_for_cluster_ids(
                bk_biz_id=bk_biz_id,
                cluster_domains=cluster_domains,
                start_time=start_time,
                end_time=end_time,
            )
        )
