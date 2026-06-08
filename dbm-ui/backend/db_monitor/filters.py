# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.db.models import OuterRef, Q
from django.db.models.expressions import RawSQL
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_monitor.models import NoticeGroup


class NoticeGroupFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    db_type = filters.CharFilter(method="filter_db_type")
    is_built_in = filters.BooleanFilter(field_name="is_built_in")
    receivers = filters.CharFilter(method="filter_receivers", label=_("接收人ID (模糊查询)"))
    notice_ways = filters.CharFilter(method="filter_notice_ways", label=_("通知方式 (精准查询)"))

    class Meta:
        model = NoticeGroup
        fields = {
            "bk_biz_id": ["exact", "in"],
            "update_at": ["gte", "lte"],
        }

    def filter_db_type(self, queryset, name, value):
        if not value:
            return queryset.filter(db_type="")

        db_type_group = queryset.filter(db_type=value).first()
        group_id = getattr(db_type_group, "id", 0)
        return queryset.filter(Q(id=group_id) | Q(db_type=""))

    def filter_receivers(self, queryset, name, value):
        if not value:
            return queryset

        search_terms = [term.strip() for term in value.split(",") if term.strip()]
        if not search_terms:
            return queryset

        conditions = Q()
        for term in search_terms:
            param = f"%{term}%"
            sql = "JSON_SEARCH(receivers, 'all', %s, NULL, '$[*].id') IS NOT NULL"
            # 子查询：判断当前记录是否满足该 RawSQL 条件
            subquery = queryset.filter(pk=OuterRef("pk")).annotate(match=RawSQL(sql, (param,))).filter(match=True)
            conditions |= Q(pk__in=subquery)

        return queryset.filter(conditions)

    def filter_notice_ways(self, queryset, name, value):
        if not value:
            return queryset

        search_terms = [term.strip() for term in value.split(",") if term.strip()]
        if not search_terms:
            return queryset

        conditions = Q()
        for term in search_terms:
            sql = "JSON_SEARCH(details, 'all', %s, NULL, '$**.notice_ways[*].name') IS NOT NULL"
            subquery = queryset.filter(pk=OuterRef("pk")).annotate(match=RawSQL(sql, (term,))).filter(match=True)
            conditions |= Q(pk__in=subquery)

        return queryset.filter(conditions)
