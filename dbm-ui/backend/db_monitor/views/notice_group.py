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
from collections import Counter

import django_filters
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import CCApi, CmsiApi
from backend.configuration.constants import PLAT_BIZ_ID
from backend.db_monitor import serializers
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_monitor.serializers import NoticeGroupSerializer
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = _("监控告警组")


class MonitorPolicyListFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("告警组名称"))
    bk_biz_id = django_filters.NumberFilter(method="filter_bk_biz_id", label=_("业务ID"))

    def filter_bk_biz_id(self, queryset, name, value):
        """
        内置告警组优先使用业务配置，
        """
        biz_built_in_group = queryset.filter(bk_biz_id=value, is_built_in=True)
        db_types = set(list(biz_built_in_group.values_list("db_type", flat=True)))
        plat_built_in_group_ids = (
            queryset.filter(bk_biz_id=PLAT_BIZ_ID, is_built_in=True)
            .exclude(db_type__in=db_types)
            .values_list("id", flat=True)
        )
        return queryset.filter(Q(bk_biz_id=value) | Q(id__in=plat_built_in_group_ids)).order_by("is_built_in")

    class Meta:
        model = NoticeGroup
        fields = ["bk_biz_id", "name", "db_type"]


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(operation_summary=_("查询监控告警组列表"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="create",
    decorator=common_swagger_auto_schema(
        operation_summary=_("新建监控告警组"), tags=[SWAGGER_TAG], request_body=serializers.NoticeGroupCreateSerializer()
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(operation_summary=_("获取监控告警组"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="update",
    decorator=common_swagger_auto_schema(
        operation_summary=_("更新监控告警组"), tags=[SWAGGER_TAG], request_body=serializers.NoticeGroupUpdateSerializer()
    ),
)
@method_decorator(
    name="destroy",
    decorator=common_swagger_auto_schema(operation_summary=_("删除监控告警组"), tags=[SWAGGER_TAG]),
)
class MonitorNoticeGroupViewSet(viewsets.AuditedModelViewSet):
    """
    监控告警组视图
    """

    queryset = NoticeGroup.objects.all()
    serializer_class = NoticeGroupSerializer
    filter_class = MonitorPolicyListFilter

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        notify_groups = MonitorPolicy.objects.exclude(notify_groups=[]).values_list("notify_groups", flat=True)
        context["group_used"] = dict(Counter([item for group in notify_groups for item in group]))
        return context

    @common_swagger_auto_schema(operation_summary=_("查询通知类型"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def get_msg_type(self, request, *args, **kwargs):
        return Response(CmsiApi.get_msg_type())
