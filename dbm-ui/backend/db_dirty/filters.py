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
from django_filters.filters import BaseInFilter, NumberFilter

from backend.db_dirty.models import DirtyMachine, MachineEvent


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class MachineEventFilter(filters.FilterSet):
    operator = filters.CharFilter(field_name="creator", lookup_expr="icontains", label=_("操作者"))
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", label=_("业务"))
    event = filters.CharFilter(field_name="event", lookup_expr="exact", label=_("事件类型"))
    ips = filters.CharFilter(field_name="ip", method="filter_ips", label=_("过滤IP"))

    def filter_ips(self, queryset, name, value):
        return queryset.filter(ip__in=value.split(","))

    class Meta:
        model = MachineEvent
        fields = ["operator", "bk_biz_id", "event", "ips"]


class DirtyMachinePoolFilter(filters.FilterSet):
    ips = filters.CharFilter(field_name="ip", method="filter_ips", label=_("过滤IP"))
    city = filters.CharFilter(field_name="city", lookup_expr="icontains", label=_("城市"))
    sub_zone = filters.CharFilter(field_name="sub_zone", lookup_expr="icontains", label=_("园区"))
    rack_id = filters.CharFilter(field_name="rack_id", lookup_expr="icontains", label=_("机架"))
    device_class = filters.CharFilter(field_name="device_class", lookup_expr="icontains", label=_("机型"))
    os_name = filters.CharFilter(field_name="os_name", lookup_expr="icontains", label=_("操作系统"))

    def filter_ips(self, queryset, name, value):
        return queryset.filter(ip__in=value.split(","))

    class Meta:
        model = DirtyMachine
        fields = {"bk_biz_id": ["exact"], "creator": ["exact"], "pool": ["exact"]}
