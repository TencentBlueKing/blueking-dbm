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
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from rest_framework import filters
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_monitor import serializers
from backend.db_monitor.models.alarm import DutyRule
from backend.db_monitor.serializers import DutyRuleSerializer
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission

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

    queryset = DutyRule.objects.all().order_by("-update_at")
    serializer_class = DutyRuleSerializer
    pagination_class = AuditedLimitOffsetPagination
    filter_backends = [filters.SearchFilter]
    filter_fields = {"db_type": ["exact"], "name": ["exact"]}
    search_fields = ["name"]

    @staticmethod
    def inst_getter(request, view):
        if view.action in ["list", "create"]:
            return [get_request_key_id(request, key="db_type")]
        if view.action in ["update", "partial_update", "destroy"]:
            return [view.kwargs.get("pk")]

    def _get_custom_permissions(self):
        if self.action == "list":
            return [ResourceActionPermission([ActionEnum.DUTY_RULE_LIST], ResourceEnum.DBTYPE, self.inst_getter)]
        elif self.action == "create":
            return [ResourceActionPermission([ActionEnum.DUTY_RULE_CREATE], ResourceEnum.DBTYPE, self.inst_getter)]
        elif self.action in ["update", "partial_update"]:
            return [ResourceActionPermission([ActionEnum.DUTY_RULE_UPDATE], ResourceEnum.DUTY_RULE, self.inst_getter)]
        elif self.action == "destroy":
            return [ResourceActionPermission([ActionEnum.DUTY_RULE_DESTROY], ResourceEnum.DUTY_RULE, self.inst_getter)]
        elif self.action in ["priority_distinct"]:
            return []

        return [ResourceActionPermission([ActionEnum.GLOBAL_MANAGE])]

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        actions=ActionEnum.get_actions_by_resource(ResourceEnum.DUTY_RULE.id),
        resource_meta=ResourceEnum.DUTY_RULE,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(operation_summary=_("轮值规则优先级统计"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def priority_distinct(self, request, *args, **kwargs):
        return Response(DutyRule.priority_distinct())
