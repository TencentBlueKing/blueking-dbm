"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import TypedDict

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mongodb.impl.cluster_meta import (
    cluster_mongos,
    cluster_overview,
    cluster_shards,
    list_clusters_by_hosts,
    list_my_mongodb_bizs,
    mongodb_list_clusters,
)
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.cluster_meta import (
    ClusterTopoOutputSerializer,
    MongoBizDetailSerializer,
    MongoBizInputSerializer,
    MongoClustersOutputSerializer,
    MongoEmptyInputSerializer,
    MongoHostClusterOutputSerializer,
    MongoHostInputSerializer,
    MongoMongosSummarySerializer,
    MongoShardsSummarySerializer,
    MongoTopoInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission


class _MetaDecoratorKwargs(TypedDict):
    tags: list
    mcp: list
    name_prefix: str


_META_DECORATOR: _MetaDecoratorKwargs = {
    "tags": [DBMMCPTags.READ],
    "mcp": [DBMMcpTools.MONGODB_META],
    "name_prefix": DBMMcpTools.MONGODB_META,
}


class MongoMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询我负责的MongoDB业务列表")),
        request_slz=MongoEmptyInputSerializer,
        response_slz=MongoBizDetailSerializer,
        **_META_DECORATOR,
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_mongodb_bizs(username=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的MongoDB集群列表")),
        request_slz=MongoBizInputSerializer,
        response_slz=MongoClustersOutputSerializer,
        **_META_DECORATOR,
    )
    def list_mongodb_clusters(self, request, *args, **kwargs):
        return Response(mongodb_list_clusters(bk_biz_id=self.get_param("bk_biz_id")))

    @mcp_tools_api_decorator(
        description=str(_("查询指定MongoDB集群的拓扑部署信息，包括集群基本信息、存储实例统计、Mongos/代理实例统计、机器分布等")),
        request_slz=MongoTopoInputSerializer,
        response_slz=ClusterTopoOutputSerializer,
        **_META_DECORATOR,
    )
    def cluster_overview(self, request, *args, **kwargs):
        return Response(cluster_overview(immute_domain=self.get_param("immute_domain")))

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群的 Mongos 节点信息")),
        request_slz=MongoTopoInputSerializer,
        response_slz=MongoMongosSummarySerializer,
        **_META_DECORATOR,
    )
    def list_cluster_mongos(self, request, *args, **kwargs):
        return Response({"mongos": cluster_mongos(immute_domain=self.get_param("immute_domain"))})

    @mcp_tools_api_decorator(
        description=str(_("查询 MongoDB 集群的分片(Shard)节点信息")),
        request_slz=MongoTopoInputSerializer,
        response_slz=MongoShardsSummarySerializer,
        **_META_DECORATOR,
    )
    def list_cluster_shards(self, request, *args, **kwargs):
        return Response({"shards": cluster_shards(immute_domain=self.get_param("immute_domain"))})

    @mcp_tools_api_decorator(
        description=str(_("根据输入的IP列表查询MongoDB集群列表")),
        request_slz=MongoHostInputSerializer,
        response_slz=MongoHostClusterOutputSerializer,
        **_META_DECORATOR,
    )
    def list_clusters_by_hosts(self, request, *args, **kwargs):
        return Response(list_clusters_by_hosts(hosts=self.get_param("hosts")))
