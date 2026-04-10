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
import re

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_meta.models import AppOperate


class AppOperateLogFilter(filters.FilterSet):
    bk_biz_id = filters.CharFilter(field_name="bk_biz_id", method="filter_bk_biz_id", label=_("业务ID列表(逗号分隔)"))
    db_type = filters.CharFilter(field_name="db_type", method="filter_db_type", label=_("db类型"))
    creator = filters.CharFilter(field_name="creator", method="filter_creator", label=_("操作人"))
    role = filters.CharFilter(field_name="role", method="filter_role", label=_("变更角色"))
    operate_type = filters.CharFilter(field_name="operate_type", method="filter_operate_type", label=_("操作类型"))
    change_person = filters.CharFilter(field_name="operate_type", method="filter_change_person", label=_("变更人员"))

    class Meta:
        model = AppOperate
        fields = {
            "create_at": ["gte", "lte"],
        }

    def filter_bk_biz_id(self, queryset, name, value):
        """处理多个业务ID的过滤，支持逗号分隔的字符串"""
        # 将逗号分隔的字符串转换为整数列表
        biz_ids = [int(x.strip()) for x in value.split(",") if x.strip()]
        return queryset.filter(bk_biz_id__in=biz_ids)

    def filter_db_type(self, queryset, name, value):
        db_types = [db_type for db_type in value.split(",")]
        return queryset.filter(db_type__in=db_types)

    def filter_creator(self, queryset, name, value):
        creators = [creator for creator in value.split(",")]
        return queryset.filter(creator__in=creators)

    def filter_role(self, queryset, name, value):
        roles = [role for role in value.split(",")]
        return queryset.filter(role__in=roles)

    def filter_operate_type(self, queryset, name, value):
        operate_types = [operate_type for operate_type in value.split(",")]
        return queryset.filter(operate_type__in=operate_types)

    def filter_change_person(self, queryset, name, value):
        if not value:
            return queryset
        person_list = [p.strip() for p in value.split(",") if p.strip()]
        if not person_list:
            return queryset

        q = Q()
        for person in person_list:
            escaped = re.escape(person)
            pattern = r"(^|,){}(,|$)".format(escaped)
            q |= Q(change_before__regex=pattern) | Q(change_after__regex=pattern)
        return queryset.filter(q)
