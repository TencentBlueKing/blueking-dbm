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

from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_meta.models import Cluster
from backend.db_meta.models.dumper import DumperSubscribeConfig
from backend.db_meta.models.extra_process import ExtraProcessInstance


class DumperInstanceListFilter(filters.FilterSet):
    ip = filters.CharFilter(field_name="ip", lookup_expr="icontains", label=_("实例IP"))
    dumper_id = filters.CharFilter(field_name="dumper_id", method="filter_dumper_id", label=_("dumper id"))
    source_cluster = filters.CharFilter(field_name="source_cluster", method="filter_source_cluster", label=_("源集群"))
    receiver_type = filters.CharFilter(field_name="type", method="filter_receiver_type", label=_("接收端类型"))
    start_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte")
    end_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte")

    def filter_dumper_id(self, queryset, name, value):
        return queryset.filter(extra_config__dumper_id__icontains=value)

    def filter_source_cluster(self, queryset, name, value):
        cluster_ids = list(Cluster.objects.filter(immute_domain__icontains=value).values_list("id", flat=True))
        return queryset.filter(cluster_id__in=cluster_ids)

    def filter_receiver_type(self, queryset, name, value):
        bk_biz_id = self.request.parser_context["kwargs"]["bk_biz_id"]
        config_ids = list(
            DumperSubscribeConfig.objects.filter(bk_biz_id=bk_biz_id, receiver_type=value).values_list("id", flat=True)
        )
        return queryset.filter(extra_config__dumper_config_id__in=config_ids)

    class Meta:
        model = ExtraProcessInstance
        fields = ["ip", "dumper_id", "source_cluster", "receiver_type", "start_time", "end_time"]
