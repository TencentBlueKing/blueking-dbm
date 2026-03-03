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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mongodb.impl.mongodb_slowlog import (
    get_mongodb_slowlog_list,
    get_mongodb_slowlog_overview,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mongodb_log import (
    MongoSlowlogListInputSerializer,
    MongoSlowlogOverviewInputSerializer,
    MongoSlowlogOverviewResponseSerializer,
    MongoSlowlogResponseSerializer,
)
from backend.dbm_aiagent.mcp_tools.mongodb.tools.comm_tools import estimate_token_count
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission


class MongoLogMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "功能: 查询 MongoDB 集群慢查询按 ns（命名空间）与 queryHash 聚合的统计；"
                "适用于 MongoShardedCluster 或 MongoReplicaSetCluster；"
                "以 queryHash + ns 为唯一标识做去重统计，返回按 ns 分桶、每桶内按 queryHash 的条数。"
            )
        ),
        request_slz=MongoSlowlogOverviewInputSerializer,
        response_slz=MongoSlowlogOverviewResponseSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_LOG],
        name_prefix=DBMMcpTools.MONGODB_LOG,
    )
    def get_mongodb_slowlog_overview(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain") or None
        instance_host = self.get_param("instance_host") or None
        instance = self.get_param("instance") or None
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        # 调用get_mongodb_slowlog_overview，如果返回结果不为空且为字典，则计算token_count
        out = get_mongodb_slowlog_overview(
            cluster_domain=cluster_domain,
            instance_host=instance_host,
            instance=instance,
            start_time=start_time,
            end_time=end_time,
        )
        if isinstance(out, dict):
            out["token_count"] = estimate_token_count(out)
        return Response(out)

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群的慢查询日志，支持按 ns、queryHash 可选过滤")),
        request_slz=MongoSlowlogListInputSerializer,
        response_slz=MongoSlowlogResponseSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.MONGODB_LOG],
        name_prefix=DBMMcpTools.MONGODB_LOG,
    )
    def get_mongodb_slowlog_list(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain") or None
        instance = self.get_param("instance") or None
        start_time = self.get_param("start_time")
        end_time = self.get_param("end_time")
        ns = self.get_param("ns") or None
        query_hash = self.get_param("queryHash") or None
        return Response(
            get_mongodb_slowlog_list(
                cluster_domain=cluster_domain,
                instance=instance,
                start_time=start_time,
                end_time=end_time,
                ns=ns,
                query_hash=query_hash,
            )
        )
