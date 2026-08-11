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
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_bigkey import (
    get_cluster_bigkey_static,
    get_host_or_instance_bigkey_logs,
)
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_hotkey import (
    get_cluster_hotkey_static,
    get_host_or_instance_hotkey_logs,
)
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_serverlog import (
    get_cluster_serverlog_static,
    get_host_or_instance_serverlog,
)
from backend.dbm_aiagent.mcp_tools.redis.impl.redis_slowlog import (
    get_cluster_slowlog_static,
    get_host_slowlog,
    get_instance_slowlog,
)
from backend.dbm_aiagent.mcp_tools.redis.serializers.redis_log import (  # noqa: F401  传入 ip 时的明细返回结构
    RedisBigkeyClusterStaticSerializer,
    RedisBigkeyQueryInputSerializer,
    RedisBigkeyResponseSerializer,
    RedisHotkeyClusterStaticSerializer,
    RedisHotkeyQueryInputSerializer,
    RedisHotkeyResponseSerializer,
    RedisServerlogClusterStaticSerializer,
    RedisServerlogQueryInputSerializer,
    RedisServerlogResponseSerializer,
    RedisSlowClusterStaticSerializer,
    RedisSlowlogQueryInputSerializer,
    RedisSlowlogResponseSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class RedisQueryLogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询慢查询日志(slowlog)，包括执行时间、命令内容等。可用于分析Redis性能问题和慢查询优化。"
                "如果不传 ip，则获取集群时间范围内慢查询日志统计数据（返回结构见 RedisSlowClusterStaticSerializer）；"
                "如果传入 ip（和可选的 port），则查询该机器或实例的详细慢查询日志列表"
                "（返回结构见 RedisSlowlogResponseSerializer）。"
            )
        ),
        request_slz=RedisSlowlogQueryInputSerializer,
        response_slz=RedisSlowClusterStaticSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_query_log",
    )
    def query_slowlogs(self, request, *args, **kwargs):
        """查询慢查询日志（集群统计或主机/实例明细）"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")
        ip = self.get_param("ip", None)
        port = self.get_param("port", None)

        if ip and port:
            return Response(
                get_instance_slowlog(
                    immute_domain=immute_domain, host=ip, port=port, start_time=start_time, end_time=end_time
                )
            )
        elif ip:
            return Response(
                get_host_slowlog(immute_domain=immute_domain, host=ip, start_time=start_time, end_time=end_time)
            )
        else:
            return Response(
                get_cluster_slowlog_static(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
            )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "【重要说明】查询大key日志。⚠️ 注意：这里获取的大key仅是【每天早上8点的一次快照数据】，"
                "【不是实时数据】，无法反映当前实时状态；且大key扫描仅在 slave 节点上进行，统计时只保留了 TopN 的数据。"
                "如果需要分析当天8点之后新产生的大key，请知悉此数据存在时效性限制。"
                "如果不传 ip，则获取集群时间范围内大key日志统计数据（包含全局摘要和按实例维度的Top10大key，"
                "返回结构见 RedisBigkeyClusterStaticSerializer）；"
                "如果传入 ip（和可选的 port），则查询该机器或实例的详细大key日志列表（按Value大小降序排列，"
                "返回结构见 RedisBigkeyResponseSerializer）。"
            )
        ),
        request_slz=RedisBigkeyQueryInputSerializer,
        response_slz=RedisBigkeyClusterStaticSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_bigkey_log",
    )
    def query_bigkey_logs(self, request, *args, **kwargs):
        """查询大key日志（集群统计或实例明细）。

        ⚠️ 【重要】此处返回的大key数据仅是【每天早上8点采集的一次快照数据】，【非实时数据】；
        并且仅在 slave 节点上进行扫描统计，只保留了 TopN 的结果。
        """
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")
        ip = self.get_param("ip", None)
        port = self.get_param("port", None)

        if ip:
            return Response(
                get_host_or_instance_bigkey_logs(
                    immute_domain=immute_domain, host=ip, start_time=start_time, end_time=end_time, port=port
                )
            )
        else:
            return Response(
                get_cluster_bigkey_static(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
            )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 server log 日志。如果不传 ip，则获取集群时间范围内 server log 统计数据"
                "（返回结构见 RedisServerlogClusterStaticSerializer）；"
                "如果传入 ip（和可选的 port），则查询该机器或实例的详细 server log 日志列表"
                "（返回结构见 RedisServerlogResponseSerializer）。"
                "可用于分析 Redis/Twemproxy 服务端运行日志。"
            )
        ),
        request_slz=RedisServerlogQueryInputSerializer,
        response_slz=RedisServerlogClusterStaticSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_server_log",
    )
    def query_server_logs(self, request, *args, **kwargs):
        """查询 server log 日志（集群统计或实例明细）"""
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")
        ip = self.get_param("ip", None)
        port = self.get_param("port", None)

        if ip:
            return Response(
                get_host_or_instance_serverlog(
                    immute_domain=immute_domain, host=ip, start_time=start_time, end_time=end_time, port=port
                )
            )
        else:
            return Response(
                get_cluster_serverlog_static(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
            )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "【重要说明】查询热key日志。⚠️ 注意：这里获取的热key仅是【每天早上8点的一次快照数据】，"
                "【不是实时数据】，无法反映当前实时的访问热度；采集时基于短时间窗口的采样统计，"
                "按 key_ops（访问次数）降序排列，只保留了 TopN 的结果。"
                "如果需要分析当天8点之后新产生的热点访问，请知悉此数据存在时效性限制。"
                "如果不传 ip，则获取集群时间范围内热key日志统计数据（包含全局摘要和按实例维度的Top10热key，"
                "返回结构见 RedisHotkeyClusterStaticSerializer）；"
                "如果传入 ip（和可选的 port），则查询该机器或实例的详细热key日志列表（按 key_ops 降序排列，"
                "返回结构见 RedisHotkeyResponseSerializer）。"
            )
        ),
        request_slz=RedisHotkeyQueryInputSerializer,
        response_slz=RedisHotkeyClusterStaticSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_QUERY_LOG],
        name_prefix="redis_hotkey_log",
    )
    def query_hotkey_logs(self, request, *args, **kwargs):
        """查询热key日志（集群统计或实例明细）。

        ⚠️ 【重要】此处返回的热key数据仅是【每天早上8点采集的一次快照数据】，【非实时数据】；
        基于短时间窗口的采样统计，按 key_ops 降序排列，只保留了 TopN 的结果。
        """
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        immute_domain = self.get_param("cluster_domain")
        ip = self.get_param("ip", None)
        port = self.get_param("port", None)

        if ip:
            return Response(
                get_host_or_instance_hotkey_logs(
                    immute_domain=immute_domain, host=ip, start_time=start_time, end_time=end_time, port=port
                )
            )
        else:
            return Response(
                get_cluster_hotkey_static(immute_domain=immute_domain, start_time=start_time, end_time=end_time)
            )
