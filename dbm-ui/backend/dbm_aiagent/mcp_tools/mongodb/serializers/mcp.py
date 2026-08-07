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

META_ACTION_LIST_CLUSTERS = "list_clusters"
META_ACTION_CLUSTER_OVERVIEW = "cluster_overview"
META_ACTION_LIST_MONGOS = "list_mongos"
META_ACTION_LIST_SHARDS = "list_shards"

META_ACTIONS = (
    META_ACTION_LIST_CLUSTERS,
    META_ACTION_CLUSTER_OVERVIEW,
    META_ACTION_LIST_MONGOS,
    META_ACTION_LIST_SHARDS,
)

METRIC_QPS = "qps"
METRIC_CONNECTIONS = "connections"
METRIC_LOCKS = "locks"
METRIC_CPU_USAGE = "cpu_usage"
METRIC_CHOICES = (METRIC_QPS, METRIC_CONNECTIONS, METRIC_LOCKS, METRIC_CPU_USAGE)

SLOWLOG_MODE_OVERVIEW = "overview"
SLOWLOG_MODE_LIST = "list"


class MongoFlexibleOutputSerializer(serializers.Serializer):
    """响应结构随 action/mode/metric 变化，详见工具描述。"""

    detail = serializers.CharField(required=False, allow_blank=True, help_text=_("结构因参数而异"))


class MongoQueryMetaInputSerializer(serializers.Serializer):
    """DBM 平台登记的元数据（ORM），不含监控 TS 发现。"""

    action = serializers.ChoiceField(choices=META_ACTIONS, help_text=_("元数据查询动作"))
    bk_biz_id = serializers.IntegerField(required=False, help_text=_("业务ID，action=list_clusters 时必填"))
    cluster_domain = serializers.CharField(
        required=False, allow_blank=True, default="", help_text=_("集群域名，拓扑类 action 必填")
    )

    def validate(self, attrs):
        action = attrs["action"]
        if action == META_ACTION_LIST_CLUSTERS and attrs.get("bk_biz_id") is None:
            raise serializers.ValidationError(_("action=list_clusters 时 bk_biz_id 必填"))
        if (
            action
            in (
                META_ACTION_CLUSTER_OVERVIEW,
                META_ACTION_LIST_MONGOS,
                META_ACTION_LIST_SHARDS,
            )
            and not (attrs.get("cluster_domain") or "").strip()
        ):
            raise serializers.ValidationError(_("该 action 需要 cluster_domain"))
        return attrs


class MongoListByHostsInputSerializer(serializers.Serializer):
    """按 IP 反查所属集群（仅挂 mongodb-mcp，不进入 public market）。"""

    ips = serializers.ListField(
        child=serializers.IPAddressField(protocol="both"),
        help_text=_("主机IP地址列表"),
        required=True,
        allow_empty=False,
    )


class MongoGetMetaInfoInputSerializer(serializers.Serializer):
    """从监控时序 label 发现实例元信息（非 DBM ORM）。"""

    target = serializers.CharField(help_text=_("集群域名 / IP / IP:PORT"))


class MongoQueryAlarmInputSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(
        required=False, allow_blank=True, default="", help_text=_("集群域名（与 bk_biz_id 二选一）")
    )
    bk_biz_id = serializers.IntegerField(required=False, help_text=_("业务ID（与 cluster_domain 二选一）"))

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        has_domain = bool((attrs.get("cluster_domain") or "").strip())
        has_biz = attrs.get("bk_biz_id") is not None
        if has_domain == has_biz:
            raise serializers.ValidationError(_("cluster_domain 与 bk_biz_id 必须二选一"))
        return attrs


class MongoQuerySlowlogInputSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=(SLOWLOG_MODE_OVERVIEW, SLOWLOG_MODE_LIST),
        default=SLOWLOG_MODE_OVERVIEW,
        help_text=_("overview=按 ns/queryHash 聚合；list=明细列表"),
    )
    cluster_domain = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("集群域名"))
    instance_host = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("实例主机"))
    instance = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("实例 ip:port"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    ns = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("命名空间过滤，仅 list"))
    queryHash = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("queryHash 过滤，仅 list"))

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        if attrs["mode"] == SLOWLOG_MODE_LIST:
            if not (attrs.get("cluster_domain") or attrs.get("instance")):
                raise serializers.ValidationError(_("mode=list 时 cluster_domain 与 instance 不能同时为空"))
        else:
            if not (attrs.get("cluster_domain") or attrs.get("instance_host") or attrs.get("instance")):
                raise serializers.ValidationError(
                    _("mode=overview 时 cluster_domain / instance_host / instance 不能同时为空")
                )
        return attrs


class MongoQueryMetricInputSerializer(serializers.Serializer):
    metric = serializers.ChoiceField(choices=METRIC_CHOICES, help_text=_("指标类型"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    instance_host = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("可选。实例主机 IP"))

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("开始时间必须小于结束时间"))
        return attrs


class MongoQueryMetricOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    metric = serializers.CharField(help_text=_("指标类型：qps/connections/locks/cpu_usage"))
    summary = serializers.DictField(
        required=False,
        help_text=_("指标汇总：global（全局峰值/均值）、total（合成 total 系列）、per_series（Top 系列）、truncated"),
    )
    reminder = serializers.CharField(required=False, allow_blank=True, help_text=_("提示信息"))
    error = serializers.CharField(required=False, allow_blank=True, help_text=_("错误信息"))
    token_count = serializers.IntegerField(required=False, help_text=_("估算 token 数"))
