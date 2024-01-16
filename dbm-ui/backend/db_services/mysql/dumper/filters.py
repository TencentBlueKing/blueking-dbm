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
from django_mysql.models.functions import JSONExtract

from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig


class DumperConfigListFilter(filters.FilterSet):
    db_name = filters.CharFilter(field_name="db_name", method="filter_db_name", label=_("库名"))
    table_name = filters.CharFilter(field_name="table_name", method="filter_table_name", label=_("表名"))

    def filter_db_name(self, queryset, name, value):
        return queryset.annotate(db_name=JSONExtract("repl_tables", "$[*].db_name")).filter(db_name__contains=value)

    def filter_table_name(self, queryset, name, value):
        return queryset.annotate(table_names=JSONExtract("repl_tables", "$[*].table_names[*]")).filter(
            table_names__contains=value
        )

    class Meta:
        model = DumperSubscribeConfig
        fields = ["db_name", "table_name"]


class DumperInstanceListFilter(filters.FilterSet):
    config_name = filters.CharFilter(field_name="config_name", method="filter_config_name", label=_("dumper订阅规则"))
    ip = filters.CharFilter(field_name="ip", lookup_expr="icontains", label=_("实例IP"))
    address = filters.CharFilter(field_name="address", method="filter_address", label=_("实例IP:Port"))
    dumper_id = filters.CharFilter(field_name="dumper_id", method="filter_dumper_id", label=_("dumper id"))
    source_cluster = filters.CharFilter(field_name="source_cluster", method="filter_source_cluster", label=_("源集群"))
    protocol_type = filters.CharFilter(field_name="protocol_type", method="filter_protocol_type", label=_("接收端类型"))
    add_type = filters.CharFilter(field_name="add_type", method="filter_add_type", label=_("同步方式"))
    target_address = filters.CharFilter(field_name="target_address", method="filter_target_address", label=_("接收端地址"))
    start_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte")
    end_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte")

    def filter_config_name(self, queryset, name, value):
        bk_biz_id = self.request.parser_context["kwargs"]["bk_biz_id"]
        try:
            dumper_config = DumperSubscribeConfig.objects.get(bk_biz_id=bk_biz_id, name=value)
            return queryset.filter(id__in=dumper_config.dumper_process_ids)
        except DumperSubscribeConfig.DoesNotExist:
            return queryset

    def filter_address(self, queryset, name, value):
        try:
            ip, port = value.split(":")
            return queryset.filter(ip=ip, listen_port=port)
        except ValueError:
            return queryset

    def filter_dumper_id(self, queryset, name, value):
        return queryset.filter(extra_config__dumper_id=value)

    def filter_source_cluster(self, queryset, name, value):
        cluster_ids = list(Cluster.objects.filter(immute_domain__icontains=value).values_list("id", flat=True))
        return queryset.filter(cluster_id__in=cluster_ids)

    def filter_protocol_type(self, queryset, name, value):
        protocol_types = value.split(",")
        return queryset.filter(extra_config__protocol_type__in=protocol_types)

    def filter_target_address(self, queryset, name, value):
        return queryset.filter(extra_config__target_address__icontains=value)

    def filter_add_type(self, queryset, name, value):
        add_types = value.split(",")
        return queryset.filter(extra_config__add_type__in=add_types)

    class Meta:
        model = ExtraProcessInstance
        fields = [
            "config_name",
            "ip",
            "address",
            "dumper_id",
            "source_cluster",
            "protocol_type",
            "start_time",
            "end_time",
            "add_type",
        ]
