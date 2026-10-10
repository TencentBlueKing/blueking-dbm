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


class EsMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_types = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "指标类型列表，可选值：\n"
            "健康状态: cluster_health_status(0=green,1=yellow,2=red)\n"
            "数据规模: indices_docs_primary, indices_store_size\n"
            "写入检索: indexing_rate, search_rate, indexing_latency, search_latency\n"
            "线程池: thread_pool_queue_max, thread_pool_rejected_max(5分钟窗口拒绝增量峰值)\n"
            "JVM: jvm_heap_usage_max\n"
            "热节点CPU: hot_cpu_usage_avg, hot_cpu_usage_max\n"
            "冷节点CPU: cold_cpu_usage_avg, cold_cpu_usage_max\n"
            "Master/Client CPU: master_cpu_usage_max, client_cpu_usage_max\n"
            "内存: hot_memory_usage_max, cold_memory_usage_max\n"
            "磁盘: hot_disk_usage_max, cold_disk_usage_max\n"
            "磁盘IO: hot_disk_io_util_max\n"
            "网络: client_net_recv, client_net_sent\n"
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


class EsDetailMetricsInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric_name = serializers.ChoiceField(
        choices=[
            ("index_docs_topn", "索引文档数TopN"),
            ("index_store_size_topn", "索引存储大小TopN"),
            ("index_indexing_rate_topn", "索引写入速率TopN"),
            ("index_search_rate_topn", "索引检索速率TopN"),
            ("hot_node_cpu_usage", "热节点CPU使用率明细"),
            ("cold_node_cpu_usage", "冷节点CPU使用率明细"),
            ("master_node_cpu_usage", "Master节点CPU使用率明细"),
            ("client_node_cpu_usage", "Client节点CPU使用率明细"),
            ("node_jvm_heap_usage", "节点JVM堆内存使用率明细"),
            ("hot_disk_usage_detail", "热节点磁盘按挂载点"),
            ("cold_disk_usage_detail", "冷节点磁盘按挂载点"),
            ("thread_pool_rejected_topn", "线程池5分钟窗口拒绝增量TopN"),
            ("thread_pool_queue_topn", "线程池队列TopN"),
        ],
        help_text=_(
            "维度明细指标名称，支持按index/node/disk/thread_pool维度查询。"
            "索引维度: index_docs_topn, index_store_size_topn, "
            "index_indexing_rate_topn, index_search_rate_topn; "
            "节点维度: hot_node_cpu_usage, cold_node_cpu_usage, "
            "master_node_cpu_usage, client_node_cpu_usage, "
            "node_jvm_heap_usage(按节点名聚合，instance 可能为空); "
            "磁盘维度: hot_disk_usage_detail, cold_disk_usage_detail; "
            "线程池维度: thread_pool_rejected_topn(5分钟窗口拒绝增量), thread_pool_queue_topn"
        ),
    )
    top_n = serializers.IntegerField(
        help_text=_("返回TopN条目数，仅对尾点非空的条目按最新值排序后统一截取，默认10，范围1-100"),
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


class EsPerformanceSummaryInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    days = serializers.IntegerField(
        help_text=_("查询最近N天的数据，默认7天"),
        required=False,
        default=7,
        min_value=1,
        max_value=30,
    )


class EsMetricStatisticsSerializer(serializers.Serializer):
    min = serializers.FloatField(help_text=_("最小值"))
    max = serializers.FloatField(help_text=_("最大值"))
    avg = serializers.FloatField(help_text=_("平均值"))
    latest = serializers.FloatField(help_text=_("尾点最新值；若尾点为空则返回空"), allow_null=True)
    count = serializers.IntegerField(help_text=_("数据点数量"))


class EsMetricAggregateStatisticsSerializer(serializers.Serializer):
    max = serializers.FloatField(help_text=_("聚合后的最大值"))
    series_count = serializers.IntegerField(help_text=_("时间序列数量"))
    min = serializers.FloatField(help_text=_("聚合后的最小值，仅单条series时返回"), required=False)
    avg = serializers.FloatField(help_text=_("聚合后的平均值，仅单条series时返回"), required=False)
    latest = serializers.FloatField(
        help_text=_("聚合后的尾点最新值，仅单条series时返回；若尾点为空则返回空"),
        allow_null=True,
        required=False,
    )
    count = serializers.IntegerField(help_text=_("聚合后的数据点数量，仅单条series时返回"), required=False)


class EsMetricSeriesSerializer(serializers.Serializer):
    dimensions = serializers.DictField(help_text=_("时间序列维度标签"))
    data_points = serializers.ListField(
        child=serializers.ListField(),
        help_text=_("单条时间序列数据点 [[value, timestamp], ...]"),
    )
    statistics = EsMetricStatisticsSerializer(
        help_text=_("单条时间序列统计信息；若整条series无非空点则为空"),
        required=False,
        allow_null=True,
    )


class EsMetricDataSerializer(serializers.Serializer):
    description = serializers.CharField(help_text=_("指标描述"))
    series = serializers.ListSerializer(
        child=EsMetricSeriesSerializer(),
        help_text=_("按维度标签区分的多条时间序列；查询失败时为空列表"),
        required=False,
    )
    aggregate_statistics = EsMetricAggregateStatisticsSerializer(
        help_text=_("聚合统计信息；多条series时仅返回 series_count 和 max；若所有series均无非空点或查询失败则为空"),
        required=False,
        allow_null=True,
    )
    error = serializers.CharField(help_text=_("查询错误信息"), required=False)


class EsMetricsOutputSerializer(serializers.Serializer):
    error = serializers.CharField(help_text=_("错误信息；前置校验失败时返回"), required=False)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    start_time = serializers.CharField(help_text=_("查询开始时间"), required=False)
    end_time = serializers.CharField(help_text=_("查询结束时间"), required=False)
    time_range_days = serializers.IntegerField(help_text=_("时间范围(天)"), required=False)
    metrics = serializers.DictField(
        child=EsMetricDataSerializer(),
        help_text=_("监控指标数据，key为指标类型，value为带维度标签的时间序列数据"),
        required=False,
    )


class EsDetailMetricItemSerializer(serializers.Serializer):
    label = serializers.CharField(help_text=_("维度标签值，如索引名/节点名/挂载点/线程池类型"))
    instance = serializers.CharField(
        help_text=_("实例地址，非实例维度或未返回实例标签时为空，例如 node_jvm_heap_usage 按节点名聚合时可能为空"),
        allow_null=True,
        required=False,
    )
    latest_value = serializers.FloatField(help_text=_("最新值"))
    statistics = serializers.DictField(help_text=_("统计信息(min/max/avg/latest)"))


class EsDetailMetricsOutputSerializer(serializers.Serializer):
    error = serializers.CharField(help_text=_("错误信息；前置校验失败或查询异常时返回"), required=False)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    dimension = serializers.CharField(help_text=_("维度类型"), required=False)
    metric_name = serializers.CharField(help_text=_("指标名称"), required=False)
    metric_desc = serializers.CharField(help_text=_("指标描述"), required=False)
    items = serializers.ListSerializer(
        child=EsDetailMetricItemSerializer(),
        help_text=_("各维度条目，仅包含尾点非空的series，并按最新值降序截取TopN"),
        required=False,
    )
    total_series_count = serializers.IntegerField(
        help_text=_("参与当前TopN排序的时间序列总数，仅统计尾点非空的series，且为截断前数量"),
        required=False,
    )


class EsPerformanceSummaryOutputSerializer(serializers.Serializer):
    error = serializers.CharField(help_text=_("错误信息；前置校验失败时返回"), required=False)
    cluster_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    time_range = serializers.CharField(help_text=_("查询时间范围描述"), required=False)
    health_summary = serializers.DictField(help_text=_("集群健康摘要(latest_status/worst_status/状态码)"), required=False)
    data_summary = serializers.DictField(help_text=_("数据规模摘要(文档数/存储大小)"), required=False)
    request_summary = serializers.DictField(help_text=_("请求速率与延迟摘要(indexing/search)"), required=False)
    thread_pool_summary = serializers.DictField(
        help_text=_("线程池摘要(queue_peak，以及5分钟窗口拒绝增量峰值字段rejected_peak)"),
        required=False,
    )
    datanode_resource_summary = serializers.DictField(
        help_text=_("数据节点资源摘要(热/冷节点CPU、内存、磁盘、磁盘IO，以及仅统计data node的JVM)"),
        required=False,
    )
    master_resource_summary = serializers.DictField(help_text=_("Master资源摘要(CPU)"), required=False)
