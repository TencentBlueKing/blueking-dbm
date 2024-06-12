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

from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig


class TendbOpenAreaConfigListFilter(filters.FilterSet):
    config_name = filters.CharFilter(field_name="config_name", lookup_expr="icontains", label=_("模板名称"))
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", label=_("业务ID"))
    cluster_type = filters.CharFilter(field_name="cluster_type", method="filter_cluster_type", label=_("集群类型"))
    ticket_types = filters.CharFilter(field_name="ticket__ticket_type", method="filter_ticket_types", label=_("单据类型"))

    class Meta:
        model = TendbOpenAreaConfig
        fields = ["config_name", "bk_biz_id"]

    def filter_cluster_type(self, queryset, name, value):
        return queryset.filter(cluster_type__in=value.split(","))
