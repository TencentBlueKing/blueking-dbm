# -*- coding:utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_services.dbbase.resources.query_base import build_q_for_domain_by_cluster
from backend.db_services.redis.hot_key_analysis.models import RedisHotKeyRecord, RedisHotKeyRecordDetail


class RedisHotKeyAnalysisFilter(filters.FilterSet):
    operator = filters.CharFilter(field_name="creator", lookup_expr="icontains", label=_("操作者"))
    create_at__lte = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte", label=_("创建时间早于"))
    create_at__gte = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte", label=_("创建时间晚于"))
    instance_addresses = filters.CharFilter(
        field_name="ins_list", method="filter_instance_addresses", label=_("过滤IP/实例")
    )
    immute_domain = filters.CharFilter(field_name="immute_domain", method="filter_domains", label=_("过滤域名"))
    cluster_ids = filters.CharFilter(field_name="cluster_id", method="filter_cluster_ids", label=_("过滤集群"))

    def filter_instance_addresses(self, queryset, name, value):
        query_filters = Q()
        if value:
            instance_filters = Q()
            instances = value.split(",")
            for instance in instances:
                instance_filters |= Q(ins_list__icontains=instance)
            query_filters &= instance_filters
        return queryset.filter(query_filters)

    def filter_cluster_ids(self, queryset, name, value):
        return queryset.filter(cluster_id__in=value.split(","))

    def filter_immute_domain(self, queryset, name, value):
        return queryset.filter(build_q_for_domain_by_cluster(domains=value.split(",")))

    class Meta:
        model = RedisHotKeyRecord
        fields = ["operator", "cluster_ids", "create_at__lte", "create_at__gte", "immute_domain", "instance_addresses"]


class RedisHotKeyDetailsFilter(filters.FilterSet):
    instance_addresses = filters.CharFilter(field_name="ins", method="filter_instance_addresses", label=_("过滤IP/实例"))
    key = filters.CharFilter(field_name="key", lookup_expr="icontains", label=_("过滤key"))

    def filter_instance_addresses(self, queryset, name, value):
        query_filters = Q()
        if value:
            instance_filters = Q()
            instances = value.split(",")
            for instance in instances:
                instance_filters |= Q(ins__icontains=instance)
            query_filters &= instance_filters
        return queryset.filter(query_filters)

    class Meta:
        model = RedisHotKeyRecordDetail
        fields = ["instance_addresses", "key"]
