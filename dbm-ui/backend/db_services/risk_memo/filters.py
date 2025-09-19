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
from django_filters import rest_framework as filters

from backend.configuration.models import DBAdministrator
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskMemoFollowUp


class RiskMemoListFilter(filters.FilterSet):
    content = filters.CharFilter(field_name="content", method="filter_content", label=_("跟进内容"))
    follow_user = filters.CharFilter(field_name="follow_user", method="filter_follow_user", label=_("跟进人"))
    is_assist = filters.BooleanFilter(field_name="is_assist", method="filter_is_assist", label=_("是否协助"))

    class Meta:
        model = RiskMemo
        fields = {
            "name": ["icontains"],
            "bk_biz_id": ["exact"],
            "level": ["exact"],
            "status": ["exact"],
            "db_type": ["exact"],
            "description": ["icontains"],
            "biz_inpact": ["exact"],
            "is_special": ["exact"],
            "duration_time": ["exact", "lt", "gt"],
            "creator": ["exact"],
        }

    def filter_content(self, queryset, name, value):
        risks = RiskMemoFollowUp.objects.filter(content__icontains=value).values_list("id", flat=True)
        return queryset.filter(id__in=risks)

    def filter_follow_user(self, queryset, name, value):
        risks = RiskMemoFollowUp.objects.filter(creator__icontains=value).values_list("id", flat=True)
        return queryset.filter(id__in=risks)

    def filter_is_assist(self, queryset, name, value):
        user = self.request.user.username
        qs = Q()
        if value:
            assists = (
                DBAdministrator.objects.filter(users__contains=user)
                .exclude(users__0=user)
                .values("bk_biz_id", "db_type", "users")
            )
        else:
            # 主负责的业务（第一个 DBA）
            assists = DBAdministrator.objects.filter(users__0=user).values("bk_biz_id", "db_type", "users")

        for assist in assists:
            qs |= Q(bk_biz_id=assist["bk_biz_id"], db_type=assist["db_type"], creator__in=assist["users"])
        return queryset.filter(qs)


class RiskMemoFollowUpListFilter(filters.FilterSet):
    class Meta:
        model = RiskMemoFollowUp
        fields = {
            "risk": ["exact"],
        }


class RiskOpRecordListFilter(filters.FilterSet):
    op_time = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte", label=_("操作时间"))
    oper_type = filters.CharFilter(field_name="oper_type", lookup_expr="exact", label=_("操作类型"))
    creator = filters.CharFilter(field_name="creator", lookup_expr="exact", label=_("操作人"))
    risk = filters.CharFilter(field_name="risk", lookup_expr="exact", label=_("risk"))
