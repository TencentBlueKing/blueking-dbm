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
import re
from typing import Optional

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from backend.configuration.models import DBAdministrator

_UNLIMITED_TIME_RANGES = frozenset({"-0d", "-0h", "now -0d", "now -0h"})
_TIME_DELTA_PATTERN = re.compile(r"^(-?\d+)([dh]|days?|hours?)$")


def parse_time_range_delta(value: str) -> Optional[timezone.timedelta]:
    """解析 time_range 为 timedelta；返回 None 表示不限时间范围（-0d/-0h）。"""
    default_delta = timezone.timedelta(hours=24)
    if not value:
        return default_delta
    time_input = value.strip().lower()
    if time_input in _UNLIMITED_TIME_RANGES:
        return None
    try:
        if time_input.startswith("now"):
            parts = time_input.split()
            if len(parts) < 2:
                return default_delta
            time_str = parts[1]
        else:
            time_str = time_input
        match = _TIME_DELTA_PATTERN.match(time_str)
        if not match:
            return default_delta
        number = int(match.group(1))
        unit = match.group(2)
        if unit in ["d", "day", "days"]:
            return timezone.timedelta(days=abs(number))
        if unit in ["h", "hour", "hours"]:
            return timezone.timedelta(hours=abs(number))
    except (ValueError, IndexError):
        return default_delta
    return default_delta


def apply_min_time_range_filter(
    queryset,
    value: str,
    min_days: Optional[int] = None,
):
    """按 time_range 过滤 queryset；若配置了 min_days 且时间窗更短，则至少放宽至 min_days 天。"""
    delta = parse_time_range_delta(value)
    if delta is None:
        return queryset
    if min_days is not None:
        min_delta = timezone.timedelta(days=min_days)
        if delta < min_delta:
            delta = min_delta
    return queryset.filter(create_at__gte=timezone.now() - delta)


class ReportListFilter(filters.FilterSet):
    def __init__(self, *args, min_time_range_days: Optional[int] = None, **kwargs):
        self.min_time_range_days = min_time_range_days
        super().__init__(*args, **kwargs)

    select_biz_id = filters.NumberFilter(field_name="select_biz_id", method="filter_select_biz_id", label=_("业务ID"))
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", method="filter_bk_biz_id", label=_("业务ID"))
    manage = filters.CharFilter(
        field_name="manage", method="filter_manage", label=_("处理类型"), help_text=_("todo待我处理/assist待我协助")
    )
    dba = filters.CharFilter(field_name="dba", method="filter_dba", label=_("DBA"), help_text=_("DBA过滤"))
    cluster = filters.CharFilter(field_name="cluster", method="filter_cluster", label=_("集群名"))
    time_range = filters.CharFilter(field_name="time_range", method="filter_time_range", label=_("时间范围"))

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
        # 支持不同模型使用不同字段名存储集群信息
        model_fields = [f.name for f in queryset.model._meta.fields]
        if "cluster" in model_fields:
            cluster_field = "cluster"
        elif "domain" in model_fields:
            cluster_field = "domain"
        elif "cluster_domain" in model_fields:
            cluster_field = "cluster_domain"
        else:
            return queryset

        cluster = value.split(",")
        if len(cluster) == 1:
            return queryset.filter(**{f"{cluster_field}__icontains": cluster[0]})
        else:
            return queryset.filter(**{f"{cluster_field}__in": cluster})

    def filter_dba(self, queryset, name, value):
        users = value.split(",")
        db_type = self.request.path.strip("/").split("/")[1]
        first_dba_filters = functools.reduce(operator.or_, [Q(db_type=db_type, users__0=user) for user in users])
        manage_bizs = DBAdministrator.objects.filter(first_dba_filters).values_list("bk_biz_id", flat=True)
        return queryset.filter(bk_biz_id__in=list(manage_bizs))

    def filter_select_biz_id(self, queryset, name, value):
        return queryset.filter(bk_biz_id=value)

    def filter_bk_biz_id(self, queryset, name, value):
        return queryset.filter(bk_biz_id=value)

    def filter_time_range(self, queryset, name, value):
        """
        根据时间范围筛选，支持以下格式：
        - now -7d / now -24h
        - 7d / 24h (简写格式)
        - 7days / 24hours (完整格式)
        """
        return apply_min_time_range_filter(queryset, value, min_days=self.min_time_range_days)


class DrillReportFilter(ReportListFilter):
    """继承 ReportListFilter，但排除 cluster 字段"""

    cluster = None


class ReportFilterBackend(DjangoFilterBackend):
    filterset_base = ReportListFilter

    def get_filterset_kwargs(self, request, queryset, view):
        kwargs = super().get_filterset_kwargs(request, queryset, view)
        min_days = getattr(view, "min_time_range_days", None)
        if min_days is not None:
            kwargs["min_time_range_days"] = min_days
        return kwargs


class DrillReportFilterBackend(DjangoFilterBackend):
    filterset_base = DrillReportFilter
