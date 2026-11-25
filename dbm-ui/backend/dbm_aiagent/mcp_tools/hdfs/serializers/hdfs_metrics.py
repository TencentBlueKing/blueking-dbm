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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.common.impl.promql_query import parse_step_to_seconds
from backend.dbm_aiagent.mcp_tools.hdfs.constants import (
    DEFAULT_STEP,
    MIN_STEP_SECONDS,
    SUMMARY_DEFAULT_DAYS,
    SUMMARY_MAX_DAYS,
)
from backend.dbm_aiagent.mcp_tools.hdfs.enums import (
    get_hdfs_aggregation_choices,
    get_hdfs_metric_choices,
    get_hdfs_role_choices,
    get_hdfs_unit_choices,
)


class HdfsMetricsInputSerializer(serializers.Serializer):
    """HDFS 指标时序查询入参。

    完整的指标中文含义放在 metric_name 的 choices label 里（由 enums 提供），
    工具 description 只写短清单，避免 description 膨胀。

    不设 bk_biz_id：底层 execute_promql 固定使用 DBA 业务查询监控数据，
    无需调用方传入，可减少智能体需要填写的必填参数。
    """

    cluster_domain = serializers.CharField(required=True, help_text=_("HDFS 集群访问域名"))
    metric_name = serializers.ChoiceField(
        choices=get_hdfs_metric_choices(),
        required=True,
        help_text=_("指标名。指标名只表达语义，不含节点角色，" "查 NameNode 还是 DataNode 由 instance_roles 决定，取峰值还是均值由 aggregation 决定"),
    )
    instance_roles = serializers.ListField(
        child=serializers.ChoiceField(choices=get_hdfs_role_choices()),
        required=False,
        default=None,
        allow_null=True,
        help_text=_(
            "节点角色列表，仅支持 hdfs_namenode 与 hdfs_datanode"
            "（JournalNode 与 Zookeeper 无 exporter 指标上报）。"
            "留空时自动取该指标的全部适用角色。"
            "NameNode 专属指标传入 DataNode 角色（或反之）会直接报错并提示合法角色，"
            "不会静默返回空数据。"
            "capacity_usage / corrupt_blocks / missing_blocks / uncheckpointed_txns / "
            "datanode_last_contact / namenode_rpc_queue_time / datanode_jvm_heap_usage "
            "的角色已固化在查询内，传入任何角色都会报错，请留空"
        ),
    )
    aggregation = serializers.ChoiceField(
        choices=get_hdfs_aggregation_choices(),
        required=False,
        default=None,
        allow_null=True,
        help_text=_("聚合方式。留空时取该指标的默认聚合方式（资源与耗时类多为均值，计数与连接数类为峰值）"),
    )
    start_time = serializers.DateTimeField(
        required=False,
        default=None,
        allow_null=True,
        help_text=_("开始时间，格式 2026-01-08T16:33:38+08:00，默认为 end_time 前 5 分钟"),
    )
    end_time = serializers.DateTimeField(
        required=False,
        default=None,
        allow_null=True,
        help_text=_("结束时间，格式 2026-01-08T16:33:38+08:00，默认为当前时间"),
    )
    step = serializers.CharField(
        required=False,
        default=DEFAULT_STEP,
        help_text=_("采样步长，如 '1m'、'5m'、'1h'。查询时间跨度较大时应放大步长以控制返回数据量"),
    )

    def validate_step(self, value):
        """入口级 step 格式校验，非法值返回 400 而不是 500。

        复用 common 的 parse_step_to_seconds 作为权威解析器，刻意不在本模块复制
        STEP_PATTERN 正则（避免两份正则漂移）。common 构造器本身不校验 step，
        非法值会一路穿透到 execute_promql 才抛裸 ValueError，被兜成 500。
        """
        try:
            step_seconds = parse_step_to_seconds(value)
        except ValueError:
            raise serializers.ValidationError(
                _("step 格式非法: {}，需形如 '1m'、'5m'、'1h'、'1d'（单位仅支持 s/m/h/d，且不小于 {}s）").format(value, MIN_STEP_SECONDS)
            )
        # 拒绝小于最小步长的取值：与 HDFS exporter 采集周期对齐，更小步长无意义；
        # 同时天然挡住 "0s" 这类会在点数估算处除零的值
        if step_seconds < MIN_STEP_SECONDS:
            raise serializers.ValidationError(
                _("step 不能小于 {}s（HDFS exporter 采集周期为 {} 秒）").format(MIN_STEP_SECONDS, MIN_STEP_SECONDS)
            )
        return value


class HdfsSeriesItemSerializer(serializers.Serializer):
    """单条时序数据"""

    dimensions = serializers.DictField(help_text=_("维度标签"))
    target = serializers.CharField(help_text=_("目标标识"))
    datapoints = serializers.ListField(help_text=_("时序数据点列表，每项为 [value, timestamp]"))
    unit = serializers.CharField(help_text=_("单位"), allow_blank=True, required=False, default="")


class HdfsMetricsOutputSerializer(serializers.Serializer):
    """HDFS 指标时序查询出参"""

    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    metric_name = serializers.CharField(help_text=_("指标名"))
    description = serializers.CharField(help_text=_("指标中文含义"))
    unit = serializers.ChoiceField(
        choices=get_hdfs_unit_choices(),
        help_text=_("数值单位。percent 表示服务端已换算为百分比（无需再做除法）；" "second 为秒、ms 为毫秒，两者不要混用；" "unverified 表示单位未经确认，不要据此换算或横向比较"),
    )
    aggregation = serializers.CharField(help_text=_("实际生效的聚合方式"), allow_null=True)
    instance_roles = serializers.ListField(help_text=_("实际查询的节点角色"))
    applicable_roles = serializers.ListField(help_text=_("该指标的全部适用角色"))
    note = serializers.CharField(help_text=_("补充说明"), required=False, allow_blank=True)
    promql = serializers.JSONField(
        help_text=_(
            "实际执行的 PromQL 语句。NameNode 专属指标会额外带 "
            "'and on(cluster_domain, instance_host) (... == 1)' 子句，"
            "即只保留当前 Active NameNode 的时间线"
        )
    )
    series = HdfsSeriesItemSerializer(many=True, help_text=_("时序数据列表"))


class HdfsPerformanceSummaryInputSerializer(serializers.Serializer):
    """HDFS 集群性能摘要入参"""

    cluster_domain = serializers.CharField(required=True, help_text=_("HDFS 集群访问域名"))
    days = serializers.IntegerField(
        required=False,
        default=SUMMARY_DEFAULT_DAYS,
        min_value=1,
        max_value=SUMMARY_MAX_DAYS,
        help_text=_("查询最近多少天，默认 {} 天，最大 {} 天").format(SUMMARY_DEFAULT_DAYS, SUMMARY_MAX_DAYS),
    )


class HdfsMetricSummaryItemSerializer(serializers.Serializer):
    """摘要中单个指标的统计结果"""

    description = serializers.CharField(help_text=_("指标中文含义"))
    unit = serializers.CharField(help_text=_("数值单位"), allow_blank=True)
    max = serializers.FloatField(help_text=_("峰值"), required=False)
    avg = serializers.FloatField(help_text=_("均值"), required=False)
    health = serializers.CharField(help_text=_("健康状态: normal/warning/fatal/unknown，按峰值与阈值比较得出"), required=False)
    warning_threshold = serializers.FloatField(
        help_text=_("既定预警阈值，为空表示该指标无对应阈值、不做判定"), required=False, allow_null=True
    )
    fatal_threshold = serializers.FloatField(help_text=_("既定致命阈值，为空表示该指标无对应阈值、不做判定"), required=False, allow_null=True)
    message = serializers.CharField(help_text=_("补充说明"), required=False, allow_blank=True)
    error = serializers.CharField(help_text=_("该指标查询失败的原因"), required=False, allow_blank=True)


class HdfsPerformanceSummaryOutputSerializer(serializers.Serializer):
    """HDFS 集群性能摘要出参"""

    cluster_domain = serializers.CharField(help_text=_("集群访问域名"))
    time_range = serializers.CharField(help_text=_("查询时间范围"))
    step = serializers.CharField(help_text=_("采样步长"))
    groups = serializers.DictField(help_text=_("按系统资源/容量与内存/数据块/元数据分组的指标摘要，" "每组含 name(分组中文名) 与 metrics(指标名到统计结果)"))
    abnormal_metrics = serializers.ListField(help_text=_("命中预警或致命阈值的指标列表，可直接作为排障入口"))
