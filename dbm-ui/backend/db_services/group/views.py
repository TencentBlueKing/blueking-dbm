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

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import (
    PaginatedResponseSwaggerAutoSchema,
    ResponseSwaggerAutoSchema,
    common_swagger_auto_schema,
)
from backend.db_meta.models import Group
from backend.db_services.group.handlers import GroupHandler
from backend.db_services.group.serializers import GroupMoveInstancesSerializer, GroupSerializer
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, get_request_key_id

SWAGGER_TAG = _("分组")


class GroupViewSet(viewsets.AuditedModelViewSet):
    """
    分组视图
    """

    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    pagination_class = AuditedLimitOffsetPagination

    def _get_custom_permissions(self):
        bk_biz_id = get_request_key_id(self.request, key="bk_biz_id", default=0)
        if int(bk_biz_id):
            return [DBManagePermission()]

        return []

    def get_queryset(self):
        queryset = super().get_queryset()
        bk_biz_id = self.request.query_params.get("bk_biz_id")
        if self.action == "list" and bk_biz_id:
            queryset = queryset.filter(bk_biz_id=bk_biz_id)

        return queryset

    @common_swagger_auto_schema(
        operation_summary=_("分组详情"),
        responses={status.HTTP_200_OK: GroupSerializer(label=_("分组详情"))},
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        """单据实例详情"""
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("分组列表"),
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("创建新分组"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: GroupSerializer(label=_("创建新分组"))},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新分组信息"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: GroupSerializer(label=_("更新分组信息"))},
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除分组"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: GroupSerializer(label=_("删除分组"))},
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        Group.objects.filter(id=int(kwargs["pk"])).delete()
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("移动实例到新组"),
        auto_schema=ResponseSwaggerAutoSchema,
        request_body=GroupMoveInstancesSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=GroupMoveInstancesSerializer)
    def move_instances(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            GroupHandler.move_instances(
                new_group=validated_data["new_group_id"], instances=validated_data["instance_ids"]
            )
        )
