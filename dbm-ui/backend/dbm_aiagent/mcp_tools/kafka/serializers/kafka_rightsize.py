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


class KafkaClusterRightsizeInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(
        help_text=_("业务ID。传了只评估该业务（需业务管理权限）；不传则评估所有业务（仅DBA可用）"), required=False, min_value=1
    )
    city = serializers.CharField(help_text=_("城市，如 上海。不传则不按城市过滤"), required=False, allow_blank=True)
    days = serializers.IntegerField(
        help_text=_("峰值统计窗口（天），默认30天，范围1-30天"), required=False, default=30, min_value=1, max_value=30
    )
    disk_target_percent = serializers.FloatField(
        help_text=_("缩容后磁盘使用率目标上限(%)，默认60"), required=False, default=60, min_value=10, max_value=95
    )
    net_watermark_percent = serializers.FloatField(
        help_text=_("缩容后单机网卡带宽使用率上限(%)，默认50"), required=False, default=50, min_value=10, max_value=95
    )
    cpu_guard_percent = serializers.FloatField(
        help_text=_("当前峰值CPU利用率超过该值时不建议缩容(%)，默认40"), required=False, default=40, min_value=1, max_value=100
    )
    min_nodes = serializers.IntegerField(
        help_text=_("缩容后至少保留的broker数量，默认3"), required=False, default=3, min_value=1, max_value=20
    )
    limit = serializers.IntegerField(
        help_text=_("最多返回多少个集群明细，默认20；汇总始终覆盖全部集群"), required=False, default=20, min_value=1, max_value=200
    )
    include_keep = serializers.BooleanField(help_text=_("是否返回判定为keep（不建议缩容）的集群，默认不返回"), required=False, default=False)


class RightsizeCurrentSerializer(serializers.Serializer):
    nodes = serializers.IntegerField(help_text=_("当前broker数量"))
    cpu_cores_per_node = serializers.IntegerField(help_text=_("单机CPU核数，取各broker最小值"))
    memory_gb_per_node = serializers.IntegerField(help_text=_("单机内存(GB)，取各broker最小值"))
    disk_gb_per_node = serializers.FloatField(help_text=_("单机数据盘容量(GB)，取各broker最小值，0表示未知"))
    bandwidth_mbps_per_node = serializers.FloatField(
        help_text=_("单机带宽(Mbps)，取各broker最小值，来自broker主机的带宽指标，任一台缺失则为空，表示未知"), allow_null=True
    )
    bandwidth_missing_ips = serializers.ListField(
        child=serializers.CharField(), help_text=_("没有取到有效带宽的broker IP（指标缺失、为0或为未配置的默认值）")
    )


class RightsizeObservedSerializer(serializers.Serializer):
    window_days = serializers.IntegerField(help_text=_("统计窗口(天)"))
    producer_peak_bytes_per_sec = serializers.FloatField(help_text=_("生产流量峰值(字节/秒)，客户端口径"), allow_null=True)
    consumer_peak_bytes_per_sec = serializers.FloatField(help_text=_("消费流量峰值(字节/秒)，客户端口径"), allow_null=True)
    host_net_peak_bits_per_sec = serializers.FloatField(
        help_text=_("所有broker主机网卡 出+入 流量之和的峰值(bit/秒)"), allow_null=True
    )
    cpu_peak_percent = serializers.FloatField(help_text=_("最忙broker的CPU利用率峰值(%)"), allow_null=True)
    log_size_gb = serializers.FloatField(help_text=_("各broker上所有副本日志大小之和的峰值(GB)，仅展示，不参与容量计算"), allow_null=True)
    disk_used_gb = serializers.FloatField(help_text=_("所有broker数据盘已用容量之和的峰值(GB)，含日志以外的残留数据，容量计算用这个值"), allow_null=True)
    reporting_brokers = serializers.DictField(
        child=serializers.IntegerField(),
        help_text=_("各决策指标(producer/cpu/host_net/disk)里，元数据中的broker有多少台在上报"),
    )
    missing_brokers = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text=_("各决策指标里没有在上报的broker IP，没有缺失的指标不出现；非空时判unclear(metrics_incomplete)"),
    )


class RightsizeReclaimSerializer(serializers.Serializer):
    cpu_cores = serializers.IntegerField(help_text=_("可回收CPU核数"))
    memory_gb = serializers.IntegerField(help_text=_("可回收内存(GB)"))
    disk_gb = serializers.FloatField(help_text=_("可回收磁盘(GB)"))


class RightsizeRecommendationSerializer(serializers.Serializer):
    target_nodes = serializers.IntegerField(help_text=_("建议缩容后的broker数量，仅rightsize/keep(已合理)时有值"), allow_null=True)
    binding_constraint = serializers.CharField(help_text=_("决定目标台数的约束：disk/network/min_nodes"), allow_null=True)
    nodes_by_disk = serializers.IntegerField(help_text=_("仅按磁盘容量需要的台数"), allow_null=True)
    nodes_by_network = serializers.IntegerField(help_text=_("仅按网络带宽需要的台数"), allow_null=True)
    projected_disk_percent = serializers.FloatField(help_text=_("缩容到目标台数后的磁盘使用率(%)"), allow_null=True)
    projected_net_percent = serializers.FloatField(help_text=_("缩容到目标台数后的单机带宽使用率(%)"), allow_null=True)
    reclaim_nodes = serializers.IntegerField(help_text=_("可回收的broker数量"))
    reclaim = RightsizeReclaimSerializer(help_text=_("可回收的资源"))


class RightsizeClusterSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    immute_domain = serializers.CharField(help_text=_("集群域名"))
    alias = serializers.CharField(help_text=_("集群别名"), allow_blank=True)
    region = serializers.CharField(help_text=_("集群所在城市"), allow_blank=True)
    verdict = serializers.CharField(
        help_text=_("判定：decommission(生产流量严格为0，可下线)/rightsize(可缩容)/keep(不建议缩容)/unclear(数据缺失，需人工查看)")
    )
    reasons = serializers.ListField(
        child=serializers.CharField(),
        help_text=_(
            "keep/unclear的原因：cpu_guard/already_right_sized/metrics_missing/metrics_incomplete/"
            "bandwidth_unknown/disk_capacity_unknown/no_broker"
        ),
    )
    flags = serializers.ListField(child=serializers.CharField(), help_text=_("提示，不影响判定：consumer_active(生产为0但仍有消费)"))
    current = RightsizeCurrentSerializer(help_text=_("当前规模"))
    observed = RightsizeObservedSerializer(help_text=_("窗口内的实测峰值"))
    recommendation = RightsizeRecommendationSerializer(help_text=_("建议"))


class RightsizeReclaimBucketSerializer(serializers.Serializer):
    clusters = serializers.IntegerField(help_text=_("集群数"))
    nodes = serializers.IntegerField(help_text=_("可回收broker数量"))
    cpu_cores = serializers.IntegerField(help_text=_("可回收CPU核数"))
    memory_gb = serializers.IntegerField(help_text=_("可回收内存(GB)"))
    disk_gb = serializers.FloatField(help_text=_("可回收磁盘(GB)"))


class RightsizeReclaimTotalSerializer(serializers.Serializer):
    nodes = serializers.IntegerField(help_text=_("可回收broker数量"))
    cpu_cores = serializers.IntegerField(help_text=_("可回收CPU核数"))
    memory_gb = serializers.IntegerField(help_text=_("可回收内存(GB)"))
    disk_gb = serializers.FloatField(help_text=_("可回收磁盘(GB)"))


class RightsizeReclaimableSerializer(serializers.Serializer):
    total = RightsizeReclaimTotalSerializer(help_text=_("下线+缩容合计"))
    decommission = RightsizeReclaimBucketSerializer(help_text=_("整集群下线可回收"))
    rightsize = RightsizeReclaimBucketSerializer(help_text=_("缩容可回收"))


class RightsizeBizSummarySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    clusters = serializers.IntegerField(help_text=_("评估的集群数"))
    actionable_clusters = serializers.IntegerField(help_text=_("可下线或可缩容的集群数"))
    nodes = serializers.IntegerField(help_text=_("可回收broker数量"))


class RightsizeSummarySerializer(serializers.Serializer):
    cluster_count = serializers.IntegerField(help_text=_("评估的集群总数"))
    by_verdict = serializers.DictField(child=serializers.IntegerField(), help_text=_("各判定结果的集群数"))
    reclaimable = RightsizeReclaimableSerializer(help_text=_("可回收资源汇总"))
    by_biz = RightsizeBizSummarySerializer(many=True, help_text=_("按业务汇总，按可回收broker数降序"))


class KafkaClusterRightsizeOutputSerializer(serializers.Serializer):
    params = serializers.DictField(help_text=_("本次评估使用的参数"))
    summary = RightsizeSummarySerializer(help_text=_("汇总，覆盖全部评估的集群"))
    returned_cluster_count = serializers.IntegerField(help_text=_("clusters里返回的集群数"))
    clusters = RightsizeClusterSerializer(many=True, help_text=_("集群明细，可下线/可缩容的在前，按可回收broker数降序"))
    query_errors = serializers.DictField(child=serializers.CharField(), help_text=_("监控查询失败的指标及原因，非空时相关集群会被判为unclear"))
