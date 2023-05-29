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
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import FilterSet, filters

from backend.db_package.models import Package


class PackageListFilter(FilterSet):
    keyword = filters.CharFilter(method="filter_keyword")
    pkg_type = filters.CharFilter(field_name="pkg_type", lookup_expr="exact", label=_("介质类型"))
    db_type = filters.CharFilter(field_name="db_type", lookup_expr="exact", label=_("DB类型"))

    class Meta:
        model = Package

        fields = ("keyword", "db_type", "pkg_type", "version")

    def filter_keyword(self, queryset, name, value):
        if name == "keyword":
            queryset = queryset.filter(Q(name__icontains=value) | Q(version__icontains=value))

        return queryset
