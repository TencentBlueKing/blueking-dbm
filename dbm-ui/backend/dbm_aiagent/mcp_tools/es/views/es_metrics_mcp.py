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
from backend.dbm_aiagent.mcp_tools.es.impl.es_metrics import (
    get_es_performance_summary,
    query_es_detail_metrics,
    query_es_metrics,
)
from backend.dbm_aiagent.mcp_tools.es.serializers.es_metrics import (
    EsDetailMetricsInputSerializer,
    EsDetailMetricsOutputSerializer,
    EsMetricsInputSerializer,
    EsMetricsOutputSerializer,
    EsPerformanceSummaryInputSerializer,
    EsPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("flow")

"""
ES 监控指标查询相关的 MCP
- 查询集群监控指标
- 获取集群性能摘要
- 查询维度明细指标（索引/节点/磁盘/线程池 TopN）
"""


class EsMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询ES集群监控指标，获取指定时间范围内的指标数据。"
                "支持集群健康/索引规模/写入检索速率与延迟/线程池/JVM堆内存/"
                "热冷节点CPU与内存/磁盘水位与IO/网络流量等指标，不传metric_types则查询所有。"
                "返回每个指标按维度标签区分的多条series、每条series的时间序列数据点与统计信息，以及聚合统计信息。"
                "若单条series无非空点，则该series的 statistics 为空；当同一指标返回多条series时，聚合统计仅保留 series_count 和 max。"
                "若所有series均无非空点，则 aggregate_statistics 为空。"
                "前置校验失败时返回顶层 error 字段；单个指标查询失败时，在对应 metric 对象内返回 error 字段，HTTP 状态仍为 200。"
            )
        ),
        request_slz=EsMetricsInputSerializer,
        response_slz=EsMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_METRICS, DBMMcpTools.DBM_PUBLIC_MARKET],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="es_metrics",
    )
    def query_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        metric_types = validated_params.get("metric_types")
        start_time = validated_params.get("start_time")
        end_time = validated_params.get("end_time")

        result = query_es_metrics(
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
                "获取ES集群性能摘要。"
                "用途：快速获取集群最近N天的关键性能指标摘要，包括集群健康、数据规模、"
                "读写请求速率与延迟、线程池排队与拒绝、JVM堆、节点资源等。"
                "参数说明："
                "1. bk_biz_id：必填，业务ID"
                "2. cluster_domain：必填，集群域名"
                "3. days：可选，查询最近N天的数据，默认7天，范围1-30天"
                ""
                "返回数据："
                "- health_summary: 集群健康摘要(latest_status/worst_status以及原始状态码，latest_status 基于真实尾点，尾点为空时为 unknown)"
                "- data_summary: 数据规模摘要(主分片文档数、存储大小；latest 字段基于真实尾点，尾点为空时返回空值)"
                "- request_summary: 请求速率与延迟摘要(indexing/search)"
                "- thread_pool_summary: 线程池摘要(queue_peak，以及5分钟窗口拒绝增量峰值字段rejected_peak)"
                "- datanode_resource_summary: 数据节点资源摘要(热/冷节点CPU、内存、磁盘、磁盘IO，以及仅统计data node的JVM)"
                "- master_resource_summary: Master资源摘要(CPU)"
                "前置校验失败时返回顶层 error 字段；部分关键指标查询失败、无数据或尾点为空时，对应摘要字段返回空值或 unknown，HTTP 状态仍为 200。"
                ""
                "典型使用场景："
                "- 用户询问'这个ES集群最近表现怎么样'时，调用此接口获取摘要"
                "- 用户询问'集群健康吗'、'有没有写拒绝'、'磁盘/JVM怎么样'等问题时，先调用此接口获取概览"
            )
        ),
        request_slz=EsPerformanceSummaryInputSerializer,
        response_slz=EsPerformanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="es_metrics",
    )
    def performance_summary(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        days = validated_params.get("days", 7)

        result = get_es_performance_summary(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            days=days,
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询ES维度明细指标TopN排行。支持按index/node/disk/thread_pool维度查询。"
                "索引维度: index_docs_topn(文档数), index_store_size_topn(存储大小), "
                "index_indexing_rate_topn(写入速率), index_search_rate_topn(检索速率); "
                "节点维度: hot/cold/master/client_node_cpu_usage, "
                "node_jvm_heap_usage(按节点名聚合，instance 可能为空); "
                "磁盘维度: hot_disk_usage_detail, cold_disk_usage_detail(按挂载点); "
                "线程池维度: thread_pool_rejected_topn(按pool类型统计5分钟窗口拒绝增量), "
                "thread_pool_queue_topn(按pool类型如write/search/get的队列长度)。"
                "返回各维度条目的label/instance/latest_value和统计信息，仅对尾点非空的series按最新值降序排列后统一截取TopN。"
                "total_series_count 表示尾点非空、参与当前TopN排序的series数量（截断前）。"
                "前置校验失败或查询异常时通过 error 字段返回，HTTP 状态仍为 200。"
            )
        ),
        request_slz=EsDetailMetricsInputSerializer,
        response_slz=EsDetailMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ES_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="es_metrics",
    )
    def query_detail_metrics(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_params["bk_biz_id"]
        cluster_domain = validated_params["cluster_domain"]
        metric_name = validated_params["metric_name"]
        top_n = validated_params.get("top_n", 10)
        start_time = validated_params.get("start_time")
        end_time = validated_params.get("end_time")

        result = query_es_detail_metrics(
            bk_biz_id=bk_biz_id,
            cluster_domain=cluster_domain,
            metric_name=metric_name,
            top_n=top_n,
            start_time=start_time,
            end_time=end_time,
        )
        return Response(result)
