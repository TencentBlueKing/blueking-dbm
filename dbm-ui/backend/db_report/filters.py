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

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from backend.configuration.models import DBAdministrator


class ReportListFilter(filters.FilterSet):
    select_biz_id = filters.NumberFilter(field_name="bk_biz_id", label=_("业务ID"))
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
        return queryset.filter(bk_biz_id__in=value)

    def filter_time_range(self, queryset, name, value):
        """
        根据时间范围筛选，支持以下格式：
        - now -7d / now -24h
        - 7d / 24h (简写格式)
        - 7days / 24hours (完整格式)
        """
        now = timezone.now()
        # 解析时间范围参数
        delta = timezone.timedelta(hours=24)  # 默认使用最近24小时
        if value:
            try:
                # 统一处理输入格式
                time_input = value.strip().lower()
                # 检查是否为-0d或-0h格式
                if time_input in ["-0d", "-0h", "now -0d", "now -0h"]:
                    return queryset
                # 支持多种格式：
                # 1. "now -7d" 格式
                if time_input.startswith("now"):
                    parts = time_input.split()
                    if len(parts) >= 2:
                        time_str = parts[1]
                        delta = self._parse_time_delta(time_str)
                # 2. 直接时间格式 "7d", "24h"
                else:
                    delta = self._parse_time_delta(time_input)

            except (ValueError, IndexError):
                delta = timezone.timedelta(hours=24)

        start_time = now - delta
        return queryset.filter(create_at__gte=start_time)

    def _parse_time_delta(self, time_str):
        """解析时间字符串为timedelta对象"""
        # 匹配数字和单位
        pattern = r"^(-?\d+)([dh]|days?|hours?)$"
        match = re.match(pattern, time_str)

        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        number = int(match.group(1))
        unit = match.group(2)

        # 处理单位
        if unit in ["d", "day", "days"]:
            return timezone.timedelta(days=abs(number))
        elif unit in ["h", "hour", "hours"]:
            return timezone.timedelta(hours=abs(number))
        else:
            raise ValueError(f"Unsupported time unit: {unit}")


class DrillReportFilter(ReportListFilter):
    """继承 ReportListFilter，但排除 cluster 字段"""

    cluster = None


class ReportFilterBackend(DjangoFilterBackend):
    filterset_base = ReportListFilter


class DrillReportFilterBackend(DjangoFilterBackend):
    filterset_base = DrillReportFilter
