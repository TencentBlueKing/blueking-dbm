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
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_status import (
    get_redis_client_list,
    get_redis_clients_info,
    get_redis_cluster_load_tag,
    get_redis_command_stats_delta,
    get_redis_cpu_info,
    get_redis_keyspace_info,
    get_redis_memory_info,
    get_redis_persistence_info,
    get_redis_replication_info,
    get_redis_server_info,
    get_redis_stats_info,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.instance_status import (
    RedisClusterInputSerializer,
    RedisClusterLoadSerializer,
    RedisInstanceInfoInputSerializer,
    RedisInstanceInfoResponseSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission


class RedisQueryStatusMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询指定 Redis 集群的整体负载标签（如高负载/低负载），用于快速判断集群当前压力水平。")),
        request_slz=RedisClusterInputSerializer,
        response_slz=RedisClusterLoadSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_cluster_load_summary(self, request, *args, **kwargs):
        """查询Redis的负载概要"""
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_cluster_load_tag(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(
            _("查询指定 Redis 实例的详细状态信息，支持通过 sections 参数按需选择模块，避免一次性返回过多数据。" "此为实例级别接口，需提供具体的实例地址（redis_addr）。")
        ),
        request_slz=RedisInstanceInfoInputSerializer,
        response_slz=RedisInstanceInfoResponseSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_instance_info(self, request, *args, **kwargs):
        """查询Redis实例综合状态信息（支持按模块按需查询）"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        sections = self.get_param("sections") or []

        # 各模块查询函数映射
        section_handlers = {
            "server": lambda: get_redis_server_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "clients": lambda: get_redis_clients_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "memory": lambda: get_redis_memory_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "persistence": lambda: get_redis_persistence_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "stats": lambda: get_redis_stats_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "replication": lambda: get_redis_replication_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "cpu": lambda: get_redis_cpu_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "keyspace": lambda: get_redis_keyspace_info(redis_addr=redis_addr, immute_domain=immute_domain),
            "client_list": lambda: get_redis_client_list(redis_addr=redis_addr, immute_domain=immute_domain),
            "command_stats": lambda: get_redis_command_stats_delta(redis_addr=redis_addr, immute_domain=immute_domain),
        }

        # 未指定 sections 则查询全部
        query_sections = sections if sections else list(section_handlers.keys())

        result = {}
        for section in query_sections:
            if section in section_handlers:
                result[section] = section_handlers[section]()

        return Response(result)

    # @mcp_tools_api_decorator(
    #     description=str(
    #         _(
    #             "Redis集群拓扑MCP工具"
    #             "查询Redis集群拓扑信息并以文本格式返回，格式类似：\n"
    #             "1.2.68.13:30000 (40600 keys 0 B) 21/s OK => (1/1 slaves) 1.3.205.182:30000 (40600 keys 0 B) 24/s OK"
    #         )
    #     ),
    #     request_slz=RedisClusterInputSerializer,
    #     response_slz=RedisClusterTopologyTextSerializer,
    #     tags=[DBMMCPTags.READ],
    #     mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
    #     name_prefix="redis_query_status",
    # )
    # def get_cluster_topology(self, request, *args, **kwargs):
    #     """获取Redis集群拓扑信息(文本格式)"""
    #     immute_domain = self.get_param("immute_domain")
    #     return Response(get_redis_cluster_topology_text(immute_domain=immute_domain))
