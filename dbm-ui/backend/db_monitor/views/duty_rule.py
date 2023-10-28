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
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_monitor import serializers
from backend.db_monitor.models.alarm import DutyRule
from backend.db_monitor.serializers import DutyRuleSerializer
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission

SWAGGER_TAG = _("告警轮值规则")


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(operation_summary=_("查询轮值规则列表"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="create",
    decorator=common_swagger_auto_schema(
        operation_summary=_("新建轮值规则"), tags=[SWAGGER_TAG], request_body=serializers.DutyRuleCreateSerializer()
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(operation_summary=_("获取轮值规则"), tags=[SWAGGER_TAG]),
)
@method_decorator(
    name="update",
    decorator=common_swagger_auto_schema(
        operation_summary=_("更新轮值规则"), tags=[SWAGGER_TAG], request_body=serializers.DutyRuleUpdateSerializer()
    ),
)
@method_decorator(
    name="partial_update",
    decorator=common_swagger_auto_schema(
        operation_summary=_("部分更新轮值规则"), tags=[SWAGGER_TAG], request_body=serializers.DutyRuleUpdateSerializer()
    ),
)
@method_decorator(
    name="destroy",
    decorator=common_swagger_auto_schema(operation_summary=_("删除轮值规则"), tags=[SWAGGER_TAG]),
)
class MonitorDutyRuleViewSet(viewsets.AuditedModelViewSet):
    """
    轮值规则视图
    """

    queryset = DutyRule.objects.all()
    serializer_class = DutyRuleSerializer
    pagination_class = AuditedLimitOffsetPagination
    filter_fields = {"db_type": ["exact"]}

    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(operation_summary=_("轮值规则优先级统计"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def priority_distinct(self, request, *args, **kwargs):
        return Response(DutyRule.priority_distinct())
