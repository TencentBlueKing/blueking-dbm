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
import logging.config

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.kafka.impl.cluster_meta import (
    cluster_overview,
    kafka_list_clusters,
    list_biz_by_name,
    list_my_kafka_bizs,
    search_specs_by_name,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.cluster_meta import (
    KafkaBizDetailSerializer,
    KafkaBizInputSerializer,
    KafkaBizNameInputSerializer,
    KafkaClusterInputSerializer,
    KafkaClusterOutputSerializer,
    KafkaTopoOutputSerializer,
    SpecOutputSerializer,
    SpecSearchInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Kafka meta 相关的 query
"""


class KafkaQueryMetaMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(_("查询我负责的Kafka业务列表")),
        request_slz=KafkaBizInputSerializer,
        response_slz=KafkaBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_QUERY_META],
        name_prefix="kafka_query_meta",
    )
    def list_my_bizs(self, request, *args, **kwargs):
        return Response(list_my_kafka_bizs(userID=request.user.username))

    @mcp_tools_api_decorator(
        description=str(_("根据业务英文名查询业务详情")),
        request_slz=KafkaBizNameInputSerializer,
        response_slz=KafkaBizDetailSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_QUERY_META],
        name_prefix="kafka_query_meta",
    )
    def list_bizs_by_name(self, request, *args, **kwargs):
        biz_name = self.get_param("biz_name")
        return Response(list_biz_by_name(biz_name=biz_name))

    @mcp_tools_api_decorator(
        description=str(_("查询业务下的Kafka集群列表")),
        request_slz=KafkaBizInputSerializer,
        response_slz=KafkaClusterOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_QUERY_META],
        name_prefix="kafka_query_meta",
    )
    def list_kafka_clusters(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        return Response(kafka_list_clusters(bk_biz_id=bk_biz_id))

    @mcp_tools_api_decorator(
        description=str(_("查询 Kafka 集群信息")),
        request_slz=KafkaClusterInputSerializer,
        response_slz=KafkaTopoOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_QUERY_META],
        name_prefix="kafka_query_meta",
    )
    def cluster_overview(self, request, *args, **kwargs):
        immute_domain = self.get_param("immute_domain")
        return Response(cluster_overview(immute_domain=immute_domain))

    @mcp_tools_api_decorator(
        description=str(_("根据规格名称模糊查询规格信息，支持如 '16核32G' 等规格名称搜索")),
        request_slz=SpecSearchInputSerializer,
        response_slz=SpecOutputSerializer(many=True),
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_QUERY_META],
        name_prefix="kafka_query_meta",
    )
    def search_specs_by_name(self, request, *args, **kwargs):
        spec_name = self.get_param("spec_name")
        spec_cluster_type = self.get_param("spec_cluster_type", "kafka")
        return Response(search_specs_by_name(spec_name=spec_name, spec_cluster_type=spec_cluster_type))
