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
    RedisClientListResponseSerializer,
    RedisClientsInfoSerializer,
    RedisCommandStatsResponseSerializer,
    RedisCPUInfoSerializer,
    RedisInstanceInputSerializer,
    RedisKeyspaceInfoSerializer,
    RedisMemoryInfoSerializer,
    RedisPersistenceInfoSerializer,
    RedisReplicationInfoSerializer,
    RedisServerInfoSerializer,
    RedisStatsInfoSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission


class RedisQueryStatusMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询Redis服务器基本信息，包括版本、运行模式、操作系统、进程ID、端口、运行时长等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisServerInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_server_info(self, request, *args, **kwargs):
        """获取Redis服务器基本信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_server_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis客户端连接信息，包括已连接客户端数、阻塞客户端数、缓冲区使用情况等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisClientsInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_clients_info(self, request, *args, **kwargs):
        """获取Redis客户端连接信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_clients_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis内存使用信息，包括已使用内存、RSS内存、内存峰值、内存碎片率、淘汰策略等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisMemoryInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_memory_info(self, request, *args, **kwargs):
        """获取Redis内存使用信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_memory_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis持久化信息，包括RDB和AOF的状态、上次保存时间、保存耗时等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisPersistenceInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_persistence_info(self, request, *args, **kwargs):
        """获取Redis持久化信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_persistence_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis统计信息，包括总连接数、命令处理数、QPS、网络IO、键过期淘汰、命中率等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisStatsInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_stats_info(self, request, *args, **kwargs):
        """获取Redis统计信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_stats_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis复制信息，包括主从角色、复制偏移量、从节点数量、复制积压缓冲区状态等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisReplicationInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_replication_info(self, request, *args, **kwargs):
        """获取Redis复制信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_replication_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis CPU使用信息，包括系统CPU和用户CPU的使用时间, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisCPUInfoSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_cpu_info(self, request, *args, **kwargs):
        """获取Redis CPU使用信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_cpu_info(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis键空间信息,包括各个数据库的键数量、过期键数量、平均TTL等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisKeyspaceInfoSerializer(many=True),
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_keyspace_info(self, request, *args, **kwargs):
        """获取Redis键空间信息"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_keyspace_info(redis_addr=redis_addr, immute_domain=immute_domain))

    # ## Redis客户端和命令统计 ###
    @mcp_tools_api_decorator(
        description=str(_("查询Redis所有已连接客户端的详细信息列表，包括客户端地址、连接时长、空闲时间、执行的命令等, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisClientListResponseSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_client_list(self, request, *args, **kwargs):
        """获取Redis客户端列表"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_client_list(redis_addr=redis_addr, immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("查询Redis命令统计信息（间隔1秒采样），返回每个命令在1秒内的调用次数、耗时等增量数据, 实例级别，仅用于要求查询某个实例时候调用")),
        request_slz=RedisInstanceInputSerializer,
        response_slz=RedisCommandStatsResponseSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_STATUS],
        name_prefix="redis_query_status",
    )
    def get_command_stats(self, request, *args, **kwargs):
        """获取Redis命令统计信息（1秒间隔采样）"""
        redis_addr = self.get_param("redis_addr")
        immute_domain = self.get_param("cluster_domain")
        return Response(get_redis_command_stats_delta(redis_addr=redis_addr, immute_domain=immute_domain))

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
