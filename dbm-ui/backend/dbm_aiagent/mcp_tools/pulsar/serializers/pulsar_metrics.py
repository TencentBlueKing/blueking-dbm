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


class PulsarMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_types = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "指标类型列表，可选值：\n"
            "积压指标: msg_backlog\n"
            "Broker CPU: broker_cpu_usage_avg, broker_cpu_usage_max\n"
            "BookKeeper CPU: bookkeeper_cpu_usage_avg, bookkeeper_cpu_usage_max\n"
            "内存指标: broker_memory_usage_max, bookkeeper_memory_usage_max\n"
            "磁盘指标: bookkeeper_disk_usage_max, broker_disk_usage_max\n"
            "磁盘IO: bookkeeper_disk_io_util_max\n"
            "网络指标: broker_net_recv, broker_net_sent\n"
            "不传则查询所有指标"
        ),
        required=False,
    )
    start_time = serializers.DateTimeField(
        help_text=_("开始时间，格式: YYYY-MM-DD HH:MM:SS，默认7天前"),
        required=False,
        allow_null=True,
    )
    end_time = serializers.DateTimeField(
        help_text=_("结束时间，格式: YYYY-MM-DD HH:MM:SS，默认当前时间"),
        required=False,
        allow_null=True,
    )


class PulsarDetailMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_name = serializers.CharField(
        help_text=_(
            "维度明细指标名称，可选值：\n"
            "topic维度: topic_msg_backlog(各topic积压量)\n"
            "namespace维度: namespace_msg_backlog(各namespace积压量)\n"
            "broker维度: broker_cpu_usage\n"
            "bookkeeper维度: bookkeeper_cpu_usage\n"
            "磁盘维度: bookkeeper_disk_usage_detail, broker_disk_usage_detail(按挂载点)"
        )
    )
    top_n = serializers.IntegerField(
        help_text=_("返回TopN条目，默认10"),
        required=False,
        default=10,
        min_value=1,
        max_value=100,
    )
    start_time = serializers.DateTimeField(
        help_text=_("开始时间，格式: YYYY-MM-DD HH:MM:SS，默认1小时前"),
        required=False,
        allow_null=True,
    )
    end_time = serializers.DateTimeField(
        help_text=_("结束时间，格式: YYYY-MM-DD HH:MM:SS，默认当前时间"),
        required=False,
        allow_null=True,
    )


class PulsarPerformanceSummaryInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    days = serializers.IntegerField(
        help_text=_("查询最近N天的数据，默认7天"),
        required=False,
        default=7,
        min_value=1,
        max_value=30,
    )


class MetricStatisticsSerializer(serializers.Serializer):
    min = serializers.FloatField(help_text=_("最小值"))
    max = serializers.FloatField(help_text=_("最大值"))
    avg = serializers.FloatField(help_text=_("平均值"))
    latest = serializers.FloatField(help_text=_("最新值"), allow_null=True)
    count = serializers.IntegerField(help_text=_("数据点数量"))


class MetricDataSerializer(serializers.Serializer):
    description = serializers.CharField(help_text=_("指标描述"))
    data_points = serializers.ListField(
        child=serializers.ListField(),
        help_text=_("时间序列数据点 [[value, timestamp], ...]"),
    )
    statistics = MetricStatisticsSerializer(help_text=_("统计信息"))


class PulsarMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    start_time = serializers.CharField(help_text=_("查询开始时间"))
    end_time = serializers.CharField(help_text=_("查询结束时间"))
    time_range_days = serializers.IntegerField(help_text=_("时间范围(天)"))
    metrics = serializers.DictField(
        child=MetricDataSerializer(),
        help_text=_("监控指标数据，key为指标类型，value为指标数据"),
    )


class DetailMetricItemSerializer(serializers.Serializer):
    label = serializers.CharField(help_text=_("维度标签值，如topic名/namespace名/broker实例"))
    latest_value = serializers.FloatField(help_text=_("最新值"))
    statistics = serializers.DictField(help_text=_("统计信息(min/max/avg/latest)"))


class PulsarDetailMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dimension = serializers.CharField(help_text=_("维度类型"))
    metric_name = serializers.CharField(help_text=_("指标名称"))
    metric_desc = serializers.CharField(help_text=_("指标描述"))
    items = serializers.ListSerializer(child=DetailMetricItemSerializer(), help_text=_("各维度条目，按最新值降序"))
    total_series_count = serializers.IntegerField(help_text=_("时间序列总数"))


class PulsarPerformanceSummaryOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    time_range = serializers.CharField(help_text=_("查询时间范围描述"))
    backlog_summary = serializers.DictField(help_text=_("消息积压摘要，含峰值/均值/最新值"))
    broker_resource_summary = serializers.DictField(help_text=_("Broker资源摘要，含CPU/内存/磁盘"))
    bookkeeper_resource_summary = serializers.DictField(help_text=_("BookKeeper资源摘要，含CPU/内存/磁盘/磁盘IO"))
