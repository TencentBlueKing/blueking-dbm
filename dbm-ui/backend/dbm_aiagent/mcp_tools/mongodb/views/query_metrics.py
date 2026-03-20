"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mongodb.impl.cluster_meta import meta_info
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_metrics import (
    get_mongodb_connections,
    get_mongodb_cpu_usage,
    get_mongodb_locks,
    get_mongodb_qps,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.cluster_meta import (
    MongoMetaInfoInputSerializer,
    MongoMetaInfoOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.query_metrics import (
    ConvertTimestampInputSerializer,
    ConvertTimestampOutputSerializer,
    CurrentTimeOutputSerializer,
    MongoMetricsInputSerializer,
    MongoMetricsOutputSerializer,
    MongoTimeEmptyInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mongodb.tools.comm_tools import estimate_token_count
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.utils.time import datetime2str, timestamp2str

# 毫秒时间戳下界（>= 此值按毫秒处理并转为秒）
_MS_TIMESTAMP_THRESHOLD = 10**12


def _timestamp_to_str(ts: int) -> str:
    """将时间戳转为 ISO8601 字符串，自动判断为秒或毫秒（>= 1e12 视为毫秒）。"""
    ts = int(ts)
    if ts >= _MS_TIMESTAMP_THRESHOLD:
        ts = ts // 1000
    return timestamp2str(ts)


def _metrics_common_slz():
    return {
        "request_slz": MongoMetricsInputSerializer,
        "response_slz": MongoMetricsOutputSerializer,
        "tags": [DBMMCPTags.READ],
        # 仅聚合到 mongodb-mcp server
        "mcp": [DBMMcpTools.MONGODB_MCP],
        "name_prefix": DBMMcpTools.MONGODB_METRICS.replace("-", "_"),
    }


class MongoMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("获取当前时间（UTC，ISO8601 格式）")),
        request_slz=MongoTimeEmptyInputSerializer,
        response_slz=CurrentTimeOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_MCP],
        name_prefix=DBMMcpTools.MONGODB_METRICS.replace("-", "_"),
    )
    def get_current_time(self, request, *args, **kwargs):
        return Response({"current_time": datetime2str(timezone.now())})

    @mcp_tools_api_decorator(
        description=str(_("将多个 Unix 时间戳转换为 ISO8601 格式时间字符串；支持秒（10 位）或毫秒（13 位），会自动判断单位；支持一次转换多个")),
        request_slz=ConvertTimestampInputSerializer,
        response_slz=ConvertTimestampOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_MCP],
        name_prefix=DBMMcpTools.MONGODB_METRICS.replace("-", "_"),
    )
    def convert_timestamp_to_str(self, request, *args, **kwargs):
        timestamps = self.get_param("timestamps")
        time_strs = [_timestamp_to_str(ts) for ts in timestamps]
        return Response({"time_strs": time_strs})

    @mcp_tools_api_decorator(
        description=str(_("根据 IP、IP:PORT 或集群域名查询 MongoDB 实例元数据（cluster_domain、instance_host 等），" "是后续指标/告警查询的第一步")),
        request_slz=MongoMetaInfoInputSerializer,
        response_slz=MongoMetaInfoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_MCP],
        name_prefix=DBMMcpTools.MONGODB_METRICS.replace("-", "_"),
    )
    def get_meta_info(self, request, *args, **kwargs):
        return Response(meta_info(self.get_param("value")))

    def _query_metrics(self, fetcher):
        """统一拉取指标参数、调用 fetcher、附加 token_count 并返回 Response。"""
        params = {
            "cluster_domain": self.get_param("cluster_domain"),
            "start_time": self.get_param("start_time"),
            "end_time": self.get_param("end_time"),
            "instance_host": self.get_param("instance_host") or None,
        }
        out = fetcher(**params)
        if isinstance(out, dict):
            out["token_count"] = estimate_token_count(out)
        return Response(out)

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群 QPS（按 type/instance_role/instance）")),
        **_metrics_common_slz(),
    )
    def get_mongodb_qps(self, request, *args, **kwargs):
        return self._query_metrics(get_mongodb_qps)

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群连接数（current）")),
        **_metrics_common_slz(),
    )
    def get_mongodb_connections(self, request, *args, **kwargs):
        return self._query_metrics(get_mongodb_connections)

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群锁队列（global_lock current_queue）")),
        **_metrics_common_slz(),
    )
    def get_mongodb_locks(self, request, *args, **kwargs):
        return self._query_metrics(get_mongodb_locks)

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 主机 CPU 使用率")),
        **_metrics_common_slz(),
    )
    def get_mongodb_cpu_usage(self, request, *args, **kwargs):
        return self._query_metrics(get_mongodb_cpu_usage)
