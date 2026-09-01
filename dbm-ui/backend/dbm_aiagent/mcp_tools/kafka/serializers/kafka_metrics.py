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


class KafkaMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_types = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "指标类型列表，可选值：\n"
            "流量指标: producer_traffic, consumer_traffic, producer_msg_rate\n"
            "CPU指标: cpu_usage_avg, cpu_usage_max\n"
            "内存指标: memory_usage_avg, memory_usage_max, jvm_heap_usage\n"
            "磁盘指标: disk_usage, disk_io_read, disk_io_write\n"
            "网络指标: network_in, network_out\n"
            "性能指标: request_queue_size, response_queue_size, under_replicated_partitions, "
            "offline_partitions, isr_shrinks, isr_expands\n"
            "延迟指标: produce_request_time, fetch_request_time\n"
            "日志指标: log_flush_rate, log_size\n"
            "请求速率: produce_request_rate, fetch_request_rate, "
            "failed_produce_request_rate, failed_fetch_request_rate\n"
            "连接与负载: tcp_established, system_load1\n"
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


class KafkaPerformanceSummaryInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    days = serializers.IntegerField(
        help_text=_("查询最近N天的数据，默认7天"),
        required=False,
        default=7,
        min_value=1,
        max_value=30,
    )


class KafkaMetricStatisticsSerializer(serializers.Serializer):
    min = serializers.FloatField(help_text=_("最小值"))
    max = serializers.FloatField(help_text=_("最大值"))
    avg = serializers.FloatField(help_text=_("平均值"))
    latest = serializers.FloatField(help_text=_("最新值"), allow_null=True)
    count = serializers.IntegerField(help_text=_("数据点数量"))


class KafkaMetricDataSerializer(serializers.Serializer):
    description = serializers.CharField(help_text=_("指标描述"))
    data_points = serializers.ListField(
        child=serializers.ListField(),
        help_text=_("时间序列数据点 [[value, timestamp], ...]"),
    )
    statistics = KafkaMetricStatisticsSerializer(help_text=_("统计信息"))


class KafkaMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    start_time = serializers.CharField(help_text=_("查询开始时间"))
    end_time = serializers.CharField(help_text=_("查询结束时间"))
    time_range_days = serializers.IntegerField(help_text=_("时间范围(天)"))
    metrics = serializers.DictField(
        child=KafkaMetricDataSerializer(),
        help_text=_("监控指标数据，key为指标类型，value为指标数据"),
    )


class TrafficSummarySerializer(serializers.Serializer):
    producer_peak_bytes_per_sec = serializers.FloatField(help_text=_("生产峰值流量(字节/秒)"))
    producer_avg_bytes_per_sec = serializers.FloatField(help_text=_("生产平均流量(字节/秒)"))
    consumer_peak_bytes_per_sec = serializers.FloatField(help_text=_("消费峰值流量(字节/秒)"))
    consumer_avg_bytes_per_sec = serializers.FloatField(help_text=_("消费平均流量(字节/秒)"))


class ResourceSummarySerializer(serializers.Serializer):
    cpu_avg_percent = serializers.FloatField(help_text=_("CPU平均利用率(%)"))
    cpu_peak_percent = serializers.FloatField(help_text=_("CPU峰值利用率(%)"))
    memory_peak_percent = serializers.FloatField(help_text=_("内存峰值利用率(%)"))
    disk_peak_percent = serializers.FloatField(help_text=_("磁盘峰值使用率(%)"))


class HealthSummarySerializer(serializers.Serializer):
    max_under_replicated_partitions = serializers.IntegerField(help_text=_("最大副本不足分区数"))
    max_offline_partitions = serializers.IntegerField(help_text=_("最大离线分区数"))


class KafkaPerformanceSummaryOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    time_range = serializers.CharField(help_text=_("时间范围描述"))
    traffic_summary = TrafficSummarySerializer(help_text=_("流量摘要"))
    resource_summary = ResourceSummarySerializer(help_text=_("资源摘要"))
    health_summary = HealthSummarySerializer(help_text=_("健康状态摘要"))


class KafkaDetailMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_name = serializers.ChoiceField(
        choices=[
            ("topic_traffic_in", "Topic生产流量TopN"),
            ("topic_traffic_out", "Topic消费流量TopN"),
            ("topic_message_rate", "Topic消息速率TopN"),
            ("topic_log_size", "Topic数据量TopN"),
            ("consumer_group_lag", "消费组积压TopN"),
            ("broker_traffic_in", "Broker生产流量"),
            ("broker_traffic_out", "Broker消费流量"),
            ("broker_produce_request_rate", "Broker生产请求速率"),
            ("broker_fetch_request_rate", "Broker消费请求速率"),
            ("broker_cpu_usage", "Broker CPU使用率"),
            ("broker_tcp_established", "Broker TCP连接数"),
            ("disk_usage_detail", "磁盘使用率按挂载点"),
        ],
        help_text=_(
            "指标名称，支持topic/broker/consumer_group/disk维度的明细查询。"
            "topic维度: topic_traffic_in, topic_traffic_out, topic_message_rate, topic_log_size; "
            "消费组维度: consumer_group_lag; "
            "broker维度: broker_traffic_in, broker_traffic_out, broker_produce_request_rate, "
            "broker_fetch_request_rate, broker_cpu_usage, broker_tcp_established; "
            "磁盘维度: disk_usage_detail"
        ),
    )
    top_n = serializers.IntegerField(
        help_text=_("返回TopN条目数，默认10，范围1-100"),
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


class DetailMetricStatisticsSerializer(serializers.Serializer):
    min = serializers.FloatField(help_text=_("最小值"))
    max = serializers.FloatField(help_text=_("最大值"))
    avg = serializers.FloatField(help_text=_("平均值"))
    latest = serializers.FloatField(help_text=_("最新值"), allow_null=True)


class KafkaDetailMetricItemSerializer(serializers.Serializer):
    label = serializers.CharField(help_text=_("维度标签(topic名/broker地址/消费组名/挂载点)"))
    latest_value = serializers.FloatField(help_text=_("最新值"))
    statistics = DetailMetricStatisticsSerializer(help_text=_("统计信息"))


class KafkaDetailMetricsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    dimension = serializers.CharField(help_text=_("维度类型(topic/broker/consumer_group/disk)"))
    metric_name = serializers.CharField(help_text=_("指标名称"))
    metric_desc = serializers.CharField(help_text=_("指标描述"))
    items = KafkaDetailMetricItemSerializer(many=True, help_text=_("维度明细列表，按latest_value降序"))
    total_series_count = serializers.IntegerField(help_text=_("总时间序列数量"))
