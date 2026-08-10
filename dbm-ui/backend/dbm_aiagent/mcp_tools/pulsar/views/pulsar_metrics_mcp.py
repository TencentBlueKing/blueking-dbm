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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.pulsar.impl.pulsar_metrics import (
    get_pulsar_performance_summary,
    query_pulsar_detail_metrics,
    query_pulsar_metrics,
)
from backend.dbm_aiagent.mcp_tools.pulsar.serializers.pulsar_metrics import (
    PulsarDetailMetricsInputSerializer,
    PulsarDetailMetricsOutputSerializer,
    PulsarMetricsInputSerializer,
    PulsarMetricsOutputSerializer,
    PulsarPerformanceSummaryInputSerializer,
    PulsarPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("flow")

"""
Pulsar 监控指标查询相关的 MCP
- 查询集群监控指标
- 查询维度明细指标(TopN)
- 获取集群性能摘要
"""


class PulsarMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询Pulsar集群监控指标，获取指定时间范围内的指标数据。"
                "支持消息积压/CPU/内存/磁盘/磁盘IO/网络等指标，覆盖 Broker 和 BookKeeper 两层，"
                "不传metric_types则查询所有。"
                "返回每个指标的时间序列数据点和统计信息(min,max,avg,latest,count)。"
            )
        ),
        request_slz=PulsarMetricsInputSerializer,
        response_slz=PulsarMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="pulsar_metrics",
    )
    def query_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = query_pulsar_metrics(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            metric_types=validated_params.get("metric_types"),
            start_time=validated_params.get("start_time"),
            end_time=validated_params.get("end_time"),
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询Pulsar维度明细指标TopN排行。支持按 topic/namespace/broker/bookkeeper/disk 维度查询。"
                "topic维度: topic_msg_backlog(各topic积压量); "
                "namespace维度: namespace_msg_backlog(各namespace积压量); "
                "broker维度: broker_cpu_usage; bookkeeper维度: bookkeeper_cpu_usage; "
                "磁盘维度: bookkeeper_disk_usage_detail/broker_disk_usage_detail(按挂载点)。"
                "返回各维度条目的latest_value和统计信息，按值降序排列。"
                "定位是哪个topic积压、哪台机器磁盘满时使用该工具。"
            )
        ),
        request_slz=PulsarDetailMetricsInputSerializer,
        response_slz=PulsarDetailMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="pulsar_metrics",
    )
    def query_detail_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = query_pulsar_detail_metrics(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            metric_name=validated_params["metric_name"],
            top_n=validated_params.get("top_n", 10),
            start_time=validated_params.get("start_time"),
            end_time=validated_params.get("end_time"),
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取Pulsar集群性能摘要。"
                "用途：快速获取集群最近N天的关键性能指标摘要，包括消息积压和 Broker/BookKeeper 两层资源使用。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. days：可选，查询最近N天的数据，默认7天，范围1-30天"
                ""
                "返回数据："
                "- backlog_summary: 消息积压摘要（峰值/均值/最新值）"
                "- broker_resource_summary: Broker资源摘要（CPU/内存/磁盘）"
                "- bookkeeper_resource_summary: BookKeeper资源摘要（CPU/内存/磁盘/磁盘IO）"
                ""
                "典型使用场景："
                "- 用户询问'这个集群最近表现怎么样'时，调用此接口获取摘要"
                "- 用户询问'有没有消息积压'、'磁盘快满了吗'等问题时，先调用此接口获取概览"
            )
        ),
        request_slz=PulsarPerformanceSummaryInputSerializer,
        response_slz=PulsarPerformanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.PULSAR_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="pulsar_metrics",
    )
    def performance_summary(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_pulsar_performance_summary(
            bk_biz_id=validated_params["bk_biz_id"],
            cluster_domain=validated_params["cluster_domain"],
            days=validated_params.get("days", 7),
        )
        return Response(result)
