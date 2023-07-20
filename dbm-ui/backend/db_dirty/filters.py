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

from backend.db_dirty.models import DirtyMachine
from backend.ticket.constants import TicketType


class DirtyMachineFilter(filters.FilterSet):
    ticket_types = filters.CharFilter(field_name="ticket__ticket_type", method="filter_ticket_types", label=_("单据类型"))
    ticket_ids = filters.CharFilter(field_name="ticket__id", method="filter_ticket_ids", label=_("单据ID"))
    task_ids = filters.CharFilter(field_name="flow__flow_obj_id", method="filter_task_ids", label=_("任务ID"))
    operator = filters.CharFilter(field_name="ticket__creator", lookup_expr="icontains", label=_("操作者"))
    ip_list = filters.CharFilter(field_name="ip_list", method="filter_ip_list", label=_("过滤IP"))

    def filter_ip_list(self, queryset, name, value):
        return queryset.filter(ip__in=value.split(","))

    def filter_ticket_ids(self, queryset, name, value):
        return queryset.filter(ticket__id__in=value.split(","))

    def filter_ticket_types(self, queryset, name, value):
        return queryset.filter(ticket__ticket_type__in=value.split(","))

    def filter_task_ids(self, queryset, name, value):
        return queryset.filter(flow__flow_obj_id__in=value.split(","))

    class Meta:
        model = DirtyMachine
        fields = ["ticket_types", "ticket_ids", "task_ids", "operator", "ip_list"]
