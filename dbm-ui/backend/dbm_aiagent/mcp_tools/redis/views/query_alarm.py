"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs, auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_alarms import get_alarms_flat, get_cluster_alarms
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_alarms import (
    RedisAppAlarmInputSerializer,
    RedisAppAlarmOutputSerializer,
    RedisClusertAlarmInputSerializer,
    RedisClusertAlarmOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission, McpDBManagePermission

logger = logging.getLogger("flow")


class RedisQueryALARMMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询获取集群时间范围内告警列表")),
        request_slz=RedisClusertAlarmInputSerializer,
        response_slz=RedisClusertAlarmOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_ALARM],
        name_prefix="redis_query_alarm",
    )
    def fetch_cluster_alarms(self, request, *args, **kwargs):
        """获取集群时间范围内告警信息"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")

        return Response(get_cluster_alarms(immute_domain=immute_domain, start_time=start_time, end_time=end_time))

    @mcp_tools_api_decorator(
        description=str(_("查询某个业务在时间范围内告警信息,按集群汇总")),
        request_slz=RedisAppAlarmInputSerializer,
        response_slz=RedisAppAlarmOutputSerializer,
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_ALARM],
        name_prefix="redis_query_alarm",
    )
    def fetch_app_alarms(self, request, *args, **kwargs):
        """获取某业务时间范围内告警列表"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        bk_biz_id = self.get_param("bk_biz_id")

        return Response(get_alarms_flat(appid=bk_biz_id, start_time=start_time, end_time=end_time))
