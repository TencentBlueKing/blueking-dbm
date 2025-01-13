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
import functools
import operator

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from backend.configuration.models import DBAdministrator


class ReportListFilter(filters.FilterSet):
    manage = filters.CharFilter(
        field_name="manage", method="filter_manage", label=_("处理类型"), help_text=_("todo待我处理/assist待我协助")
    )
    dba = filters.CharFilter(field_name="dba", method="filter_dba", label=_("DBA"), help_text=_("DBA过滤"))
    cluster = filters.CharFilter(field_name="cluster", method="filter_cluster", label=_("集群名"))

    def filter_manage(self, queryset, name, value):
        username = self.request.user.username
        db_type = self.request.path.strip("/").split("/")[1]
        manage_bizs, assist_bizs = DBAdministrator.get_manage_bizs(db_type, username)
        # 待我处理
        if value == "todo":
            return queryset.filter(bk_biz_id__in=manage_bizs)
        # 待我协助
        elif value == "assist":
            return queryset.filter(bk_biz_id__in=assist_bizs)
        # 其他情况忽略
        return queryset

    def filter_cluster(self, queryset, name, value):
        cluster = value.split(",")
        if len(cluster) == 1:
            return queryset.filter(cluster__icontains=cluster[0])
        else:
            return queryset.filter(cluster__in=cluster)

    def filter_dba(self, queryset, name, value):
        users = value.split(",")
        db_type = self.request.path.strip("/").split("/")[1]
        first_dba_filters = functools.reduce(operator.or_, [Q(db_type=db_type, users__0=user) for user in users])
        manage_bizs = DBAdministrator.objects.filter(first_dba_filters).values_list("bk_biz_id", flat=True)
        return queryset.filter(bk_biz_id__in=list(manage_bizs))


class ReportFilterBackend(DjangoFilterBackend):
    filterset_base = ReportListFilter
