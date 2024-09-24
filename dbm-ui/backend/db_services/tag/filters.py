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

from backend.db_meta.models import Tag


class TagListFilter(filters.FilterSet):
    key = filters.CharFilter(field_name="key", lookup_expr="icontains", label=_("键"))
    value = filters.CharFilter(field_name="value", lookup_expr="icontains", label=_("值"))
    ids = filters.CharFilter(field_name="ids", method="filter_ids", label=_("tag id列表"))

    class Meta:
        model = Tag
        fields = {
            "bk_biz_id": ["exact"],
            "type": ["exact"],
        }

    def filter_ids(self, queryset, name, value):
        ids = list(map(int, value.split(",")))
        return queryset.filter(id__in=ids)
