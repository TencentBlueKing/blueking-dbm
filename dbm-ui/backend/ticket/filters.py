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
from django.db.models import Exists, OuterRef, Q
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_meta.models import Cluster
from backend.ticket.constants import TODO_RUNNING_STATUS, TicketStatus
from backend.ticket.models import ClusterOperateRecord, InstanceOperateRecord, Ticket, Todo


class TicketListFilter(filters.FilterSet):
    ids = filters.CharFilter(field_name="ids", method="filter_ids", label=_("单据ID列表"))
    remark = filters.CharFilter(field_name="remark", lookup_expr="icontains", label=_("备注"))
    status = filters.CharFilter(field_name="status", method="filter_status", label=_("单据状态"))
    cluster = filters.CharFilter(field_name="cluster", method="filter_cluster", label=_("集群域名"))
    todo = filters.CharFilter(field_name="todo", method="filter_todo", label=_("代办状态"))
    ordering = filters.CharFilter(field_name="ordering", method="order_ticket", label=_("排序字段"))
    is_assist = filters.BooleanFilter(field_name="is_assist", method="filter_is_assist", label=_("是否协助"))

    class Meta:
        model = Ticket
        fields = {
            "id": ["exact", "in"],
            "bk_biz_id": ["exact"],
            "ticket_type": ["exact", "in"],
            "create_at": ["gte", "lte"],
            "creator": ["exact"],
        }

    def filter_cluster(self, queryset, name, value):
        clusters = Cluster.objects.filter(immute_domain__icontains=value).values_list("id", flat=True)
        records = ClusterOperateRecord.objects.filter(cluster_id__in=clusters).values_list("id", flat=True)
        return queryset.filter(clusteroperaterecord__in=records)

    def filter_ids(self, queryset, name, value):
        ids = list(map(int, value.split(",")))
        return queryset.filter(id__in=ids)

    def filter_todo(self, queryset, name, value):
        user = self.request.user.username
        if value == "running":
            subquery = Todo.objects.filter(
                Q(operators__contains=user) | Q(helpers__contains=user),
                status__in=TODO_RUNNING_STATUS,
                ticket_id=OuterRef("id"),
            )
            todo_filter = Exists(subquery)
        else:
            subquery = Todo.objects.filter(done_by=user, ticket_id=OuterRef("id"))
            todo_filter = Exists(subquery)
        return queryset.filter(todo_filter)

    def filter_is_assist(self, queryset, name, value):
        user = self.request.user.username
        # 根据 value 的值选择不同的字段
        field = "helpers" if value else "operators"
        subquery = Todo.objects.filter(
            **{f"{field}__contains": user}, status__in=TODO_RUNNING_STATUS, ticket_id=OuterRef("id")
        )
        todo_filter = Exists(subquery)
        return queryset.filter(todo_filter)

    def filter_status(self, queryset, name, value):
        status = value.split(",")
        status_filter = Q()
        # 如果有待确认，则解析为：running + 包含正在运行的todo
        if TicketStatus.INNER_TODO in status:
            subquery = Todo.objects.filter(status__in=TODO_RUNNING_STATUS, ticket_id=OuterRef("id"))
            status_filter |= Q(status=TicketStatus.RUNNING) & Q(Exists(subquery))
            status.remove(TicketStatus.INNER_TODO.value)
        # 如果有待执行，则解析为：running + 不包含正在运行的todo
        if TicketStatus.RUNNING in status:
            subquery = Todo.objects.filter(status__in=TODO_RUNNING_STATUS, ticket_id=OuterRef("id"))
            status_filter |= Q(status=TicketStatus.RUNNING) & ~Q(Exists(subquery))
            status.remove(TicketStatus.RUNNING.value)
        # 其他状态，直接in即可
        status_filter |= Q(status__in=status)
        return queryset.filter(status_filter)

    def order_ticket(self, queryset, name, value):
        return queryset.order_by(value)


class OpRecordListFilter(filters.FilterSet):
    start_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte", label=_("开始时间"))
    end_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte", label=_("开始时间"))
    op_type = filters.CharFilter(field_name="op_type", method="filter_op_type", label=_("操作类型"))
    op_status = filters.CharFilter(field_name="op_status", method="filter_op_status", label=_("操作状态"))

    def filter_op_type(self, queryset, name, value):
        return queryset.filter(ticket__ticket_type=value)

    def filter_op_status(self, queryset, name, value):
        return queryset.filter(ticket__status=value)


class ClusterOpRecordListFilter(OpRecordListFilter):
    cluster_id = filters.NumberFilter(field_name="cluster_id", lookup_expr="exact", label=_("集群ID"))

    class Meta:
        model = ClusterOperateRecord
        fields = ["start_time", "end_time", "op_type", "op_status"]


class InstanceOpRecordListFilter(OpRecordListFilter):
    instance_id = filters.NumberFilter(field_name="instance_id", lookup_expr="exact", label=_("实例ID"))

    class Meta:
        model = InstanceOperateRecord
        fields = ["start_time", "end_time", "op_type", "op_status"]
