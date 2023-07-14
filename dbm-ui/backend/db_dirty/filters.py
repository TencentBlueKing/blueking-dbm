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
    ticket_type = filters.ChoiceFilter(
        field_name="ticket__ticket_type", choices=TicketType.get_choices(), label=_("单据类型")
    )
    ticket_id = filters.NumberFilter(field_name="ticket__id", label=_("单据ID"))
    task_id = filters.CharFilter(field_name="flow__flow_obj_id", lookup_expr="exact", label=_("任务ID"))
    operator = filters.CharFilter(field_name="ticket__creator", lookup_expr="icontains", label=_("操作者"))
    ip_list = filters.CharFilter(field_name="ip_list", method="filter_ip_list", label=_("过滤IP"))

    def filter_ip_list(self, queryset, name, value):
        ip_list = value.split(",")
        return queryset.filter(ip__in=ip_list)

    class Meta:
        model = DirtyMachine
        fields = ["ticket_type", "ticket_id", "task_id", "operator", "ip_list"]
