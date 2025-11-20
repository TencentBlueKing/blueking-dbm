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
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from backend.flow.models import FlowTree


class TaskFlowFilter(filters.FilterSet):

    db_type = filters.CharFilter(field_name="db_type", method="filter_db_type", label=_("db类型"))
    root_ids = filters.CharFilter(field_name="root_ids", method="filter_root_ids", label=_("id"))

    class Meta:
        model = FlowTree
        fields = {
            "uid": ["exact", "in"],
            "root_id": ["exact", "in"],
            "bk_biz_id": ["exact", "in"],
            "status": ["exact", "in"],
            "ticket_type": ["exact", "in"],
            "created_at": ["gte", "lte"],
            "created_by": ["exact", "in"],
        }

    def filter_db_type(self, queryset, name, value):
        db_types = [db_type for db_type in value.split(",")]
        return queryset.filter(db_type__in=db_types)

    def filter_root_ids(self, queryset, name, value):
        return queryset.filter(root_id__in=value.split(","))
