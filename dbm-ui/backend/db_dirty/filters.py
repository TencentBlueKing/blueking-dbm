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

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.filters import BaseInFilter, NumberFilter

from backend.db_dirty.models import DirtyMachine, MachineEvent
from backend.db_meta.models import Cluster
from backend.ticket.constants import TodoStatus
from backend.ticket.models import Todo


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class MachineEventFilter(filters.FilterSet):
    operator = filters.CharFilter(field_name="creator", method="filter_operator", label=_("操作者"))
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", label=_("业务"))
    ticket_id = filters.CharFilter(field_name="ticket_id", method="filter_ticket_id", label=_("单据id"))
    create_at__lte = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte", label=_("创建时间早于"))
    create_at__gte = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte", label=_("创建时间晚于"))
    events = filters.CharFilter(field_name="events", method="filter_events", label=_("过滤事件"))
    ips = filters.CharFilter(field_name="ips", method="filter_ips", label=_("过滤IP"))
    domain = filters.CharFilter(field_name="domain", method="filter_domain", label=_("过滤集群"))

    def filter_ips(self, queryset, name, value):
        return queryset.filter(ip__in=value.split(","))

    def filter_events(self, queryset, name, value):
        return queryset.filter(event__in=value.split(","))

    def filter_domain(self, queryset, name, value):
        cluster_ids = Cluster.objects.filter(immute_domain__icontains=value).values_list("id", flat=True)
        return queryset.filter(ticket__clusteroperaterecord__cluster_id__in=cluster_ids)

    def filter_operator(self, queryset, name, value):
        return queryset.filter(creator__in=value.split(","))

    def filter_ticket_id(self, queryset, name, value):
        return queryset.filter(ticket__id__in=[int(ticket_id) for ticket_id in value.split(",")])

    class Meta:
        model = MachineEvent
        fields = ["operator", "bk_biz_id", "events", "ips", "create_at__lte", "create_at__gte", "domain", "ticket_id"]


class DirtyMachinePoolFilter(filters.FilterSet):
    bk_host_ids = filters.CharFilter(field_name="bk_host_id", method="filter_host_ids", label=_("过滤主机ID"))
    ips = filters.CharFilter(field_name="ip", method="filter_ips", label=_("过滤IP"))
    city = filters.CharFilter(field_name="city", method="filter_city", label=_("城市"))
    sub_zone = filters.CharFilter(field_name="sub_zone", method="filter_sub_zone", label=_("园区"))
    rack_id = filters.CharFilter(field_name="rack_id", method="filter_rack_id", label=_("机架"))
    device_class = filters.CharFilter(field_name="device_class", method="filter_device_class", label=_("机型"))
    os_name = filters.CharFilter(field_name="os_name", method="filter_os_name", label=_("操作系统"))
    update_at__lte = filters.DateTimeFilter(field_name="update_at", lookup_expr="lte", label=_("更新时间早于"))
    update_at__gte = filters.DateTimeFilter(field_name="update_at", lookup_expr="gte", label=_("更新时间晚于"))
    pool = filters.CharFilter(field_name="pool", method="filter_pool", label=_("池类型"))
    updator = filters.CharFilter(field_name="updator", method="filter_updator", label=_("转入人"))
    is_todo = filters.BooleanFilter(method="filter_is_todo", label=_("是否是待办"))
    todo_type = filters.CharFilter(method="filter_todo_type", label=_("待办类型"))

    def filter_ips(self, queryset, name, value):
        return queryset.filter(ip__in=value.split(","))

    def filter_host_ids(self, queryset, name, value):
        return queryset.filter(bk_host_id__in=value.split(","))

    def filter_pool(self, queryset, name, value):
        return queryset.filter(pool__in=value.split(","))

    def filter_city(self, queryset, name, value):
        return queryset.filter(city__in=value.split(","))

    def filter_sub_zone(self, queryset, name, value):
        return queryset.filter(sub_zone__in=value.split(","))

    def filter_rack_id(self, queryset, name, value):
        return queryset.filter(rack_id__in=value.split(","))

    def filter_device_class(self, queryset, name, value):
        return queryset.filter(device_class__in=value.split(","))

    def filter_os_name(self, queryset, name, value):
        return queryset.filter(os_name__in=value.split(","))

    def filter_updator(self, queryset, name, value):
        return queryset.filter(updator__in=value.split(","))

    def filter_is_todo(self, queryset, name, value):
        """处理 is_todo 过滤逻辑"""
        if not value:
            return queryset

        user = self.request.user.username
        todo_type = self.request.query_params.get("todo_type", "")
        if not todo_type:
            return queryset

        # 获取待办相关的主机ID
        todo_queryset = Todo.objects.filter(status=TodoStatus.TODO, type=todo_type, operators__contains=user)
        host_ids = [todo.context["host_id"] for todo in todo_queryset]

        return queryset.filter(bk_host_id__in=host_ids)

    def filter_todo_type(self, queryset, name, value):
        """todo_type 过滤器，只在 is_todo=True 时生效"""
        # 这个过滤器主要配合 is_todo 使用，单独使用时不生效
        return queryset

    class Meta:
        model = DirtyMachine
        fields = [
            "bk_host_ids",
            "ips",
            "city",
            "sub_zone",
            "rack_id",
            "device_class",
            "os_name",
            "update_at__lte",
            "update_at__gte",
            "pool",
            "updator",
            "is_todo",
            "todo_type",
        ]
