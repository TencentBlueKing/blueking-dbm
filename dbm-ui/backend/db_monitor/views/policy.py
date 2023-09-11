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
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet

from ...configuration.constants import PLAT_BIZ_ID
from .. import constants
from ..models import MonitorPolicy
from ..serializers import (
    MonitorPolicyCloneSerializer,
    MonitorPolicyEmptySerializer,
    MonitorPolicyListSerializer,
    MonitorPolicySerializer,
    MonitorPolicyUpdateSerializer,
)


class MonitorPolicyListFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("策略名"))
    updater = filters.CharFilter(lookup_expr="exact", label=_("更新人"))
    creator = filters.CharFilter(lookup_expr="creator", label=_("创建人"))
    db_type = filters.CharFilter(lookup_expr="exact", label=_("db类型"))
    target_keyword = filters.CharFilter(lookup_expr="icontains", label=_("目标关键字检索"))
    is_enabled = filters.BooleanFilter(label=_("是否启用"))

    bk_biz_id = filters.NumberFilter(method="filter_bk_biz_id", label=_("业务ID"))

    # 如果只需要开区间，可以简化配置，这里的注释留作学习示例
    # (create_at_after, create_at_before): create_at_after=2023-09-05 14:29:00&create_at_before=2023-09-05 14:30:05
    # create_at = filters.DateTimeFromToRangeFilter("create_at")
    # 拆分rangeFilter，支持两端闭区间
    create_at_before = filters.DateTimeFilter(field_name="create_at", lookup_expr="lte")
    create_at_after = filters.DateTimeFilter(field_name="create_at", lookup_expr="gte")

    # 需要利用Q查询
    notify_groups = filters.CharFilter(method="filter_notify_groups", label=_("告警组"))

    def filter_notify_groups(self, queryset, name, value):
        """过滤多个告警组: value=1,2,3"""

        if name != "notify_groups":
            return queryset

        qs = Q()
        for group in map(lambda x: int(x), value.split(",")):
            qs = qs | Q(notify_groups__contains=group)

        return queryset.filter(qs)

    def filter_bk_biz_id(self, queryset, name, value):
        """默认包含平台告警策略"""
        return queryset.filter(bk_biz_id__in=[PLAT_BIZ_ID, value])

    class Meta:
        model = MonitorPolicy
        fields = [
            "bk_biz_id",
            "name",
            "db_type",
            "updater",
            "creator",
            "create_at_before",
            "create_at_after",
            "is_enabled",
            "target_keyword",
            "notify_groups",
        ]


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        tags=[constants.SWAGGER_TAG], responses={status.HTTP_200_OK: MonitorPolicyListSerializer()}
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        tags=[constants.SWAGGER_TAG], responses={status.HTTP_200_OK: MonitorPolicySerializer()}
    ),
)
@method_decorator(
    name="update",
    decorator=common_swagger_auto_schema(tags=[constants.SWAGGER_TAG]),
)
@method_decorator(
    name="destroy",
    decorator=common_swagger_auto_schema(tags=[constants.SWAGGER_TAG]),
)
@method_decorator(
    name="create",
    decorator=common_swagger_auto_schema(tags=[constants.SWAGGER_TAG]),
)
class MonitorPolicyViewSet(AuditedModelViewSet):
    """监控策略管理"""

    queryset = MonitorPolicy.objects.order_by("-create_at")

    http_method_names = ["get", "post", "delete"]

    # filter_fields = {
    #     "name": ["exact", "contains"],
    #     "bk_biz_id": ["exact", "in"],
    #     "db_type": ["exact", "in"],
    #     "is_enabled": ["exact"],
    #     "policy_status": ["exact", "in"],
    #     "create_at": ["lte", "gte"],
    # }
    filter_class = MonitorPolicyListFilter
    ordering_fields = ("-create_at",)

    def get_serializer_class(self):
        if self.action == "list":
            return MonitorPolicyListSerializer
        return MonitorPolicySerializer

    @common_swagger_auto_schema(
        operation_summary=_("启用策略"), tags=[constants.SWAGGER_TAG], request_body=MonitorPolicyEmptySerializer()
    )
    @action(methods=["POST"], detail=True, serializer_class=MonitorPolicyEmptySerializer)
    def enable(self, request, *args, **kwargs):
        return Response(self.get_object().enable())

    @common_swagger_auto_schema(
        operation_summary=_("停用策略"), tags=[constants.SWAGGER_TAG], request_body=MonitorPolicyEmptySerializer()
    )
    @action(methods=["POST"], detail=True, serializer_class=MonitorPolicyEmptySerializer)
    def disable(self, request, *args, **kwargs):
        return Response(self.get_object().disable())

    @common_swagger_auto_schema(
        operation_summary=_("克隆策略"), tags=[constants.SWAGGER_TAG], request_body=MonitorPolicyCloneSerializer()
    )
    @action(methods=["POST"], detail=False, serializer_class=MonitorPolicyCloneSerializer)
    def clone_strategy(self, request, *args, **kwargs):
        return Response(MonitorPolicy.clone(self.validated_data, request.user.username))

    @common_swagger_auto_schema(
        operation_summary=_("更新策略"), tags=[constants.SWAGGER_TAG], request_body=MonitorPolicyUpdateSerializer()
    )
    @action(methods=["POST"], detail=True, serializer_class=MonitorPolicyUpdateSerializer)
    def update_strategy(self, request, *args, **kwargs):
        return Response(self.get_object().update(self.validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("恢复默认策略"), tags=[constants.SWAGGER_TAG], request_body=MonitorPolicyEmptySerializer()
    )
    @action(methods=["POST"], detail=True, serializer_class=MonitorPolicyEmptySerializer)
    def reset(self, request, *args, **kwargs):
        return Response(self.get_object().reset())
