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


class MongoSlowlogOverviewInputSerializer(serializers.Serializer):
    """MongoDB 慢查询按 ns/queryHash 聚合概览输入（cluster_domain、instance_host、instance 至少填其一）"""

    cluster_domain = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("集群域名"))
    instance_host = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("实例主机"))
    instance = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("实例"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))

    def validate(self, attrs):
        if not (attrs.get("cluster_domain") or attrs.get("instance_host") or attrs.get("instance")):
            raise serializers.ValidationError(_("cluster_domain, instance_host and instance cannot all be empty"))
        return attrs


class MongoSlowlogListInputSerializer(serializers.Serializer):
    """MongoDB 慢查询列表输入（cluster_domain 与 instance 至少填其一）"""

    cluster_domain = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("集群域名"))
    instance = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("实例"))
    start_time = serializers.DateTimeField(help_text=_("开始时间"))
    end_time = serializers.DateTimeField(help_text=_("结束时间"))
    ns = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("命名空间过滤"))
    queryHash = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("queryHash 过滤"))

    def validate(self, attrs):
        if not (attrs.get("cluster_domain") or attrs.get("instance")):
            raise serializers.ValidationError(_("cluster_domain and instance cannot both be empty"))
        return attrs


class MongoSlowlogEntrySerializer(serializers.Serializer):
    """MongoDB慢查询日志条目"""

    create_time = serializers.CharField(help_text=_("执行时间"))
    duration_ms = serializers.FloatField(help_text=_("执行耗时（毫秒）"))
    op = serializers.CharField(help_text=_("操作类型"))
    ns = serializers.CharField(help_text=_("命名空间"))
    instance_addr = serializers.CharField(help_text=_("实例地址"))
    instance_role = serializers.CharField(help_text=_("实例角色"))
    queryHash = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("queryHash"))


class MongoSlowlogResponseSerializer(serializers.Serializer):
    """MongoDB慢查询响应序列化器"""

    total_count = serializers.IntegerField(help_text=_("慢查询日志总数"))
    slowlog_entries = MongoSlowlogEntrySerializer(many=True, help_text=_("慢查询日志列表"))


class MongoSlowlogOverviewResponseSerializer(serializers.Serializer):
    """MongoDB 慢查询按 ns/queryHash 聚合概览响应"""

    by_ns = serializers.DictField(
        child=serializers.DictField(child=serializers.IntegerField()),
        help_text=_("按命名空间分桶，每桶内 queryHash -> 条数"),
    )
