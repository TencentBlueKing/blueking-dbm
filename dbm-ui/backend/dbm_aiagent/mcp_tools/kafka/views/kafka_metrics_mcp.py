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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs, auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_metrics import (
    get_kafka_performance_summary,
    query_kafka_detail_metrics,
    query_kafka_metrics,
)
from backend.dbm_aiagent.mcp_tools.kafka.impl.kafka_rightsize import RightsizeParams, kafka_cluster_rightsize
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_metrics import (
    KafkaDetailMetricsInputSerializer,
    KafkaDetailMetricsOutputSerializer,
    KafkaMetricsInputSerializer,
    KafkaMetricsOutputSerializer,
    KafkaPerformanceSummaryInputSerializer,
    KafkaPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.kafka.serializers.kafka_rightsize import (
    KafkaClusterRightsizeInputSerializer,
    KafkaClusterRightsizeOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpBizManageOrDbaPermission, McpClusterDetailPermission

logger = logging.getLogger("flow")

"""
Kafka 监控指标查询相关的 MCP
- 查询集群监控指标
- 获取集群性能摘要
- 评估集群下线/缩容空间
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
        mcp=[DBMMcpTools.KAFKA_METRICS, DBMMcpTools.DBM_PUBLIC_MARKET],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
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
                "磁盘: disk_usage_detail(仅ext/xfs数据盘，排除/和/usr/local，"
                "按主机和挂载点，返回ip、instance、mount_point及原始dimensions，"
                "无法识别IP时ip为空)。"
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

    @mcp_tools_api_decorator(
        description=str(
            _(
                "评估Kafka集群的下线/缩容空间，一次调用覆盖多个集群。"
                "用途：1. 某个业务想知道名下集群有没有缩容/下架空间；2. DBA想知道某个城市能从现有集群里腾出多少机器资源。"
                "参数说明：bk_biz_id 传了则只评估该业务（需要该业务的管理权限）；不传则评估所有业务的Kafka集群（仅DBA可用）；city 传城市名（如 上海）则只看该城市的集群；"
                "days 为峰值统计窗口，默认30天。"
                "判定规则（verdict）："
                "decommission=窗口内生产流量严格为0，可整集群下线（consumer_active标记表示生产为0但仍有消费，下线前需确认）；"
                "rightsize=非空且当前峰值CPU不超过门槛，按 max(磁盘需要的台数, 网络需要的台数, 最少台数) 反推出目标台数，"
                "目标台数小于现有台数；"
                "keep=不建议缩容，reasons 为 cpu_guard(当前峰值CPU超过门槛) 或 already_right_sized(已是合理规模)；"
                "unclear=缺少判定所需的指标/规格/带宽数据，需要人工查看，reasons 说明缺什么。"
                "磁盘按所有broker数据盘已用字节数之和计算（含日志以外的残留数据）；"
                "网络按所有broker主机网卡 出+入 流量之和的峰值计算，已包含副本同步和多份消费；"
                "单机带宽取自broker主机的带宽指标（与均衡自动调速同一来源），任一台broker取不到有效带宽时该集群为unclear。"
                "决策指标（生产流量/CPU/网络/磁盘）必须每台broker都在上报，否则判unclear(metrics_incomplete)，不会用部分数据下结论。"
                "不会推算缩容后的CPU利用率。"
                "注意：给出的目标台数只是容量层面的建议，没有校验topic副本数，也没有校验分区迁移的可行性。"
                "返回：summary 汇总可回收的broker数/CPU核数/内存/磁盘及按业务分布；"
                "clusters 为集群明细，可下线/可缩容的排在前面，按可回收broker数降序，默认不返回keep的集群。"
                "该工具只做评估，不会创建任何单据；缩容或下线前仍需与业务方确认并分批执行。"
            )
        ),
        request_slz=KafkaClusterRightsizeInputSerializer,
        response_slz=KafkaClusterRightsizeOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.KAFKA_METRICS],
        permission_classes=[McpBizManageOrDbaPermission],
        mcp_auth_parser=auth_parse_bizs,
        name_prefix="kafka_metrics",
    )
    def cluster_rightsize(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        # 传了业务就只评估该业务（装饰器已校验业务管理权限）；没传则是 DBA 跨业务评估（装饰器已校验 DBA 身份）
        bk_biz_id = validated_params.get("bk_biz_id")
        bk_biz_ids = None if bk_biz_id in (None, "") else [bk_biz_id]
        params = RightsizeParams(
            disk_target_pct=validated_params["disk_target_percent"],
            net_watermark_pct=validated_params["net_watermark_percent"],
            cpu_guard_pct=validated_params["cpu_guard_percent"],
            min_nodes=validated_params["min_nodes"],
        )
        result = kafka_cluster_rightsize(
            bk_biz_ids=bk_biz_ids,
            city=validated_params.get("city") or None,
            days=validated_params["days"],
            params=params,
            limit=validated_params["limit"],
            include_keep=validated_params["include_keep"],
        )
        return Response(result)
