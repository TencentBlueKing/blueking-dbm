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
from backend.ticket.models import ClusterOperateRecord, Ticket


class TicketListFilter(filters.FilterSet):
    remark = filters.CharFilter(field_name="remark", lookup_expr="icontains", label=_("备注"))
    cluster = filters.CharFilter(field_name="cluster", method="filter_cluster", label=_("集群域名"))
    ids = filters.CharFilter(field_name="ids", method="filter_ids", label=_("单据ID列表"))

    class Meta:
        model = Ticket
        fields = {
            "id": ["exact", "in"],
            "bk_biz_id": ["exact"],
            "ticket_type": ["exact", "in"],
            "status": ["exact", "in"],
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
