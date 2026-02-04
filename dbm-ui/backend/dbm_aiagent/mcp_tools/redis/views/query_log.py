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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_slowlog import (
    get_cluster_slowlog_static,
    get_host_slowlog,
    get_instance_slowlog,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_log import (
    RedisSlowClusterStaticSerializer,
    RedisSlowlog4HostInputSerializer,
    RedisSlowlog4InstInputSerializer,
    RedisSlowlogInputSerializer,
    RedisSlowlogResponseSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission

logger = logging.getLogger("root")


class RedisQueryLogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                """功能:获取集群时间范围内慢查询日志统计数据
        展示方式: 1.分多个多维表格展示结果;2.按实例维度详细统计的表格,需按照最大耗时,慢日志条数排序"""
            )
        ),
        request_slz=RedisSlowlogInputSerializer,
        response_slz=RedisSlowClusterStaticSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_log",
    )
    def get_cluster_slowlog_statics(self, request, *args, **kwargs):
        """获取集群时间范围内慢查询日志统计数据"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")

        return Response(
            get_cluster_slowlog_static(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
        )

    @mcp_tools_api_decorator(
        description=str(_("查询某台机器上的慢查询日志(slowlog),包括执行时间、命令内容等。可用于分析Redis性能问题和慢查询优化")),
        request_slz=RedisSlowlog4HostInputSerializer,
        response_slz=RedisSlowlogResponseSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_log",
    )
    def fetch_host_slowlog(self, request, *args, **kwargs):
        """获取某台机器上时间范围内慢查询日志"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        ip = self.get_param("ip")
        immute_domain = self.get_param("cluster_domain")

        return Response(
            get_host_slowlog(immute_domain=immute_domain, start_time=start_time, end_time=end_time, host=ip)
        )

    @mcp_tools_api_decorator(
        description=str(_("查询某个实例的慢查询日志(slowlog),包括执行时间、命令内容等。可用于分析Redis性能问题和慢查询优化")),
        request_slz=RedisSlowlog4InstInputSerializer,
        response_slz=RedisSlowlogResponseSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_log",
    )
    def fetch_instance_slowlog(self, request, *args, **kwargs):
        """获取某个实例上时间范围内慢查询日志"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        host = self.get_param("host")
        port = self.get_param("port")
        immute_domain = self.get_param("cluster_domain")

        return Response(
            get_instance_slowlog(
                immute_domain=immute_domain, start_time=start_time, end_time=end_time, host=host, port=port
            )
        )
