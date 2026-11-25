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
from backend.dbm_aiagent.mcp_tools.hdfs.impl.cluster_meta import validate_hdfs_cluster
from backend.dbm_aiagent.mcp_tools.hdfs.impl.hdfs_metrics import get_hdfs_performance_summary, query_hdfs_metrics
from backend.dbm_aiagent.mcp_tools.hdfs.serializers.hdfs_metrics import (
    HdfsMetricsInputSerializer,
    HdfsMetricsOutputSerializer,
    HdfsPerformanceSummaryInputSerializer,
    HdfsPerformanceSummaryOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")

"""
HDFS 监控指标查询相关的 MCP
- 查询集群监控指标时序数据
- 获取集群性能摘要与健康状态
"""


class HdfsMetricsMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 HDFS 集群监控指标时序数据。"
                "指标名只表达语义不含节点角色：查 NameNode 还是 DataNode 由 instance_roles 参数决定，"
                "取峰值还是均值由 aggregation 参数决定。"
                "NameNode 与 DataNode 通用指标: cpu_usage, memory_usage, disk_usage, system_load1, "
                "tcp_established, net_recv, net_sent；"
                "仅 NameNode 适用: capacity_usage, corrupt_blocks, missing_blocks, uncheckpointed_txns, "
                "datanode_last_contact, namenode_state, namenode_rpc_queue_time；"
                "仅 DataNode 适用: datanode_jvm_heap_usage, datanode_xceiver_count, "
                "datanode_call_queue_length。"
                "注意以下几点: "
                "(1) 返回的 unit 字段标明单位，unit=percent 表示服务端已换算为百分比不要再做除法，"
                "second 为秒、ms 为毫秒不要混用; "
                "(2) NameNode 专有指标已在 PromQL 内固化只取当前 Active NameNode"
                "（Standby 的时间线被整条丢弃，不会产生 0 值污染统计），"
                "主备切换时结果自动跟随，无需也无法指定主节点; "
                "(3) 上述已固化的指标 capacity_usage, corrupt_blocks, missing_blocks, "
                "uncheckpointed_txns, datanode_last_contact, namenode_rpc_queue_time 以及 "
                "datanode_jvm_heap_usage 传入 instance_roles 会报错，请留空; "
                "(4) namenode_state 是主备状态原始值（1 表示 Active），结果按 instance_host 展开可看到"
                "主备分布，它刻意不做 Active 过滤，用于确认当前主节点是谁; "
                "(5) disk_usage 是操作系统分区水位（结果按 mount_point 展开，可定位具体磁盘），"
                "capacity_usage 是 HDFS 文件系统逻辑容量水位（已计入副本放大），两者用途不同; "
                "(6) missing_blocks 比 corrupt_blocks 更严重：前者所有副本均不可用、数据已实际丢失，"
                "后者仍有其他可用副本; "
                "(7) datanode_last_contact 按 datanode 标签展开，可定位具体哪台 DataNode 失联; "
                "(8) 其余 NameNode 专属指标传入 DataNode 角色（或反之）会直接报错并提示合法角色，"
                "不会静默返回空数据。"
                "返回时序数据、实际执行的 PromQL 以及该指标的适用角色。"
            )
        ),
        request_slz=HdfsMetricsInputSerializer,
        response_slz=HdfsMetricsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="hdfs_metrics",
    )
    def query_metrics(self, request, *args, **kwargs):
        # 一次性取出全部参数：McpToolsViewSet.get_param 每次调用都会重跑一遍序列化器校验
        validated_params = self.params_validate(self.get_serializer_class())
        validate_hdfs_cluster(validated_params["cluster_domain"])
        result = query_hdfs_metrics(
            cluster_domain=validated_params["cluster_domain"],
            metric_name=validated_params["metric_name"],
            instance_roles=validated_params.get("instance_roles"),
            aggregation=validated_params.get("aggregation"),
            start_time=validated_params.get("start_time"),
            end_time=validated_params.get("end_time"),
            step=validated_params.get("step"),
        )
        return Response(result)

    @mcp_tools_api_decorator(
        description=str(
            _(
                "获取 HDFS 集群最近 N 天的性能摘要与健康状态，适用于集群巡检、画像与排障起点。"
                "覆盖 cpu_usage, disk_usage, capacity_usage, corrupt_blocks, missing_blocks, "
                "uncheckpointed_txns, datanode_last_contact, datanode_jvm_heap_usage 八个关键指标，"
                "按系统资源/容量与内存/数据块/元数据分组，"
                "每个指标给出峰值与均值，"
                "并基于既定阈值给出健康判定(normal/warning/fatal/unknown)。"
                "abnormal_metrics 字段直接列出命中预警或致命阈值的指标，可作为排障入口。"
                "无既定阈值或无采集数据的指标健康状态为 unknown，不做判定"
                "（datanode_jvm_heap_usage 无平台告警阈值，只提供统计值）。"
                "容量与数据块类指标只统计当前 Active NameNode 上报的值。"
                "为控制返回数据量，摘要使用小时级采样且只返回统计值，不返回原始数据点；"
                "需要查看指标曲线时改用指标时序查询工具。"
            )
        ),
        request_slz=HdfsPerformanceSummaryInputSerializer,
        response_slz=HdfsPerformanceSummaryOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_METRICS],
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_clusters,
        name_prefix="hdfs_metrics",
    )
    def performance_summary(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        validate_hdfs_cluster(validated_params["cluster_domain"])
        result = get_hdfs_performance_summary(
            cluster_domain=validated_params["cluster_domain"],
            days=validated_params["days"],
        )
        return Response(result)
