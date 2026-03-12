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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_metrics import (
    get_kafka_performance_summary,
    query_kafka_detail_metrics,
    query_kafka_metrics,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_metrics import (
    KafkaDetailMetricsInputSerializer,
    KafkaDetailMetricsOutputSerializer,
    KafkaMetricsInputSerializer,
    KafkaMetricsOutputSerializer,
    KafkaPerformanceSummaryInputSerializer,
    KafkaPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("flow")

"""
Kafka 监控指标查询相关的 MCP
- 查询集群监控指标
- 获取集群性能摘要
"""


class KafkaMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询Kafka集群监控指标，获取指定时间范围内的指标数据。"
                "支持流量/CPU/内存/磁盘/网络/性能/延迟/日志等指标，不传metric_types则查询所有。"
                "返回每个指标的时间序列数据点和统计信息(min,max,avg,latest,count)。"
            )
        ),
        request_slz=KafkaMetricsInputSerializer,
        response_slz=KafkaMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_METRICS],
        name_prefix="kafka_metrics",
    )
    def query_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        metric_types = validated_params.get("metric_types")
        start_time = validated_params.get("start_time")
        end_time = validated_params.get("end_time")

        result = query_kafka_metrics(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            metric_types=metric_types,
            start_time=start_time,
            end_time=end_time,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取Kafka集群性能摘要。"
                "用途：快速获取集群最近N天的关键性能指标摘要，包括流量、资源使用和健康状态。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. days：可选，查询最近N天的数据，默认7天，范围1-30天"
                ""
                "返回数据："
                "- traffic_summary: 流量摘要（生产/消费峰值和平均流量）"
                "- resource_summary: 资源摘要（CPU/内存/磁盘的平均和峰值使用率）"
                "- health_summary: 健康状态摘要（副本不足分区数、离线分区数）"
                ""
                "典型使用场景："
                "- 用户询问'这个集群最近表现怎么样'时，调用此接口获取摘要"
                "- 用户询问'CPU使用率高吗'、'流量有多大'等问题时，先调用此接口获取概览"
            )
        ),
        request_slz=KafkaPerformanceSummaryInputSerializer,
        response_slz=KafkaPerformanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_METRICS],
        name_prefix="kafka_metrics",
    )
    def performance_summary(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        days = validated_params.get("days", 7)

        result = get_kafka_performance_summary(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            days=days,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询Kafka维度明细指标TopN排行。支持按topic/broker/consumer_group/disk维度查询。"
                "topic维度: topic_traffic_in(生产流量), topic_traffic_out(消费流量), "
                "topic_message_rate(消息速率), topic_log_size(数据量); "
                "消费组: consumer_group_lag(积压量); "
                "broker维度: broker_traffic_in/out, broker_produce/fetch_request_rate, "
                "broker_cpu_usage, broker_tcp_established; "
                "磁盘: disk_usage_detail(按挂载点)。"
                "返回各维度条目的latest_value和统计信息，按值降序排列。"
            )
        ),
        request_slz=KafkaDetailMetricsInputSerializer,
        response_slz=KafkaDetailMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_METRICS],
        name_prefix="kafka_metrics",
    )
    def query_detail_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        metric_name = validated_params["metric_name"]
        top_n = validated_params.get("top_n", 10)
        start_time = validated_params.get("start_time")
        end_time = validated_params.get("end_time")

        result = query_kafka_detail_metrics(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            metric_name=metric_name,
            top_n=top_n,
            start_time=start_time,
            end_time=end_time,
        )
        return Response(result)
