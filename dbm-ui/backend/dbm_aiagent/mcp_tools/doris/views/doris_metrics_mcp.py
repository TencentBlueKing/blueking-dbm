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
from backend.dbm_aiagent.mcp_tools.doris.impl.doris_metrics import get_doris_performance_summary, query_doris_metrics
from backend.dbm_aiagent.mcp_tools.doris.serializers.doris_metrics import (
    DorisMetricsInputSerializer,
    DorisMetricsOutputSerializer,
    DorisPerformanceSummaryInputSerializer,
    DorisPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")

"""
Doris 监控指标查询相关的 MCP
- 查询集群监控指标时序数据
- 获取集群性能摘要与健康状态
"""


class DorisMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 Doris 集群监控指标时序数据。"
                "指标名只表达语义不含节点角色：查 FE 还是 BE 由 instance_roles 参数决定，"
                "取峰值还是均值由 aggregation 参数决定。"
                "FE 与 BE 通用指标: cpu_usage, memory_usage, disk_usage, system_load1, "
                "tcp_established, net_recv, net_sent；"
                "仅 FE 适用: jvm_heap_usage, query_err_rate, txn_failed_rate, txn_reject_rate, "
                "editlog_write_latency, image_push_failed, image_write_failed, compaction_score；"
                "仅 BE 适用: capacity_usage。"
                "注意以下几点: "
                "(1) 返回的 unit 字段标明单位，unit=percent 表示服务端已换算为百分比不要再做除法，"
                "unit=count_per_sec 表示次/秒; "
                "(2) query_err_rate 是单台 FE 的查询失败速率(次/秒)，不是错误占比，不要按百分比解读; "
                "(3) disk_usage 是操作系统分区水位，capacity_usage 是 BE 数据盘水位"
                "（按 1-可用/总量 计算，含预留空间与非 Doris 占用），两者用途不同; "
                "(4) capacity_usage 可按 instance_role 分组区分热/温/冷节点，作为分层扩容依据; "
                "(5) compaction_score 是集群级汇总值，已按时间点动态关联 master 标识时序，"
                "master 发生切换时结果自动跟随，无需外部指定 master 节点; "
                "(6) jvm_heap_usage 的节点角色已固化在查询内（固定覆盖 follower 与 observer），"
                "传入 instance_roles 会报错，请留空; "
                "(7) 其余 FE 专属指标传入 BE 角色（或反之）会直接报错并提示合法角色，不会静默返回空数据。"
                "返回时序数据、实际执行的 PromQL 以及该指标的适用角色。"
            )
        ),
        request_slz=DorisMetricsInputSerializer,
        response_slz=DorisMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="doris_metrics",
    )
    def query_metrics(self, request, *args, **kwargs):
        # 一次性取出全部参数：McpToolsViewSet.get_param 每次调用都会重跑一遍序列化器校验
        validated_params = self.params_validate(self.get_serializer_class())
        result = query_doris_metrics(
            cluster_domain=validated_params["cluster_domain"],
            metric_name=validated_params["metric_name"],
            instance_roles=validated_params.get("instance_roles"),
            aggregation=validated_params.get("aggregation"),
            group_by=validated_params.get("group_by"),
            start_time=validated_params.get("start_time"),
            end_time=validated_params.get("end_time"),
            step=validated_params.get("step"),
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取 Doris 集群最近 N 天的性能摘要与健康状态，适用于集群巡检、画像与排障起点。"
                "覆盖 cpu_usage, disk_usage, capacity_usage, jvm_heap_usage, query_err_rate, "
                "txn_failed_rate, editlog_write_latency, compaction_score 八个关键指标，"
                "按系统资源/容量与内存/查询/事务/元数据分组，"
                "每个指标给出峰值、谷值、均值、最新值，"
                "并基于 DBM 平台既定的告警阈值给出健康判定(normal/warning/fatal/unknown)。"
                "abnormal_metrics 字段直接列出命中预警或致命阈值的指标，可作为排障入口。"
                "无对应告警策略或无采集数据的指标健康状态为 unknown，不做判定。"
                "为控制返回数据量，摘要使用小时级采样且只返回统计值，不返回原始数据点；"
                "需要查看指标曲线时改用指标时序查询工具。"
            )
        ),
        request_slz=DorisPerformanceSummaryInputSerializer,
        response_slz=DorisPerformanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.DORIS_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="doris_metrics",
    )
    def performance_summary(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = get_doris_performance_summary(
            cluster_domain=validated_params["cluster_domain"],
            days=validated_params["days"],
        )
        return Response(result)
