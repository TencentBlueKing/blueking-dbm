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
from functools import wraps

from django.utils.translation import ugettext_lazy as _
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
from backend.configuration.models.ip_whitelist import IPWhitelist
from backend.configuration.serializers import (
    DeleteIPWhitelistSerializer,
    IPWhitelistSerializer,
    ListIPWhitelistSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = _("IP白名单")


def decorator_permission_field():
    def wrapper(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            response = view_func(*args, **kwargs)
            bk_biz_id = get_request_key_id(args[1], key="bk_biz_id")

            response.data.setdefault("permission", {})
            result = Permission().is_allowed(action=ActionEnum.GLOBAL_IP_WHITELIST_MANAGE, resources=[])
            response.data["permission"].update({ActionEnum.GLOBAL_IP_WHITELIST_MANAGE.id: result})
            # 默认嵌入全局白名单管理权限，如果有业务，再嵌入业务下的白名单管理权限
            if bk_biz_id:
                Permission.insert_external_permission_field(
                    response,
                    actions=[ActionEnum.IP_WHITELIST_MANAGE],
                    resource_meta=ResourceEnum.BUSINESS,
                    resource_id=bk_biz_id,
                )

            return response

        return wrapped_view

    return wrapper


class IPWhitelistViewSet(viewsets.AuditedModelViewSet):
    """
    IP白名单视图
    """

    queryset = IPWhitelist.objects.all()
    serializer_class = IPWhitelistSerializer
    pagination_class = AuditedLimitOffsetPagination

    @staticmethod
    def instance_getter(request, view):
        # 批量删除的白名单一定在一个业务下
        if view.action == "batch_delete":
            return [IPWhitelist.objects.filter(pk__in=request.data["ids"]).first().bk_biz_id]
        elif view.action in ["destroy", "update"]:
            return [IPWhitelist.objects.get(pk=request.data["id"]).bk_biz_id]
        else:
            return [get_request_key_id(request, key="bk_biz_id", default=0)]

    def _get_custom_permissions(self):
        if self.action in ["retrieve", "iplist"]:
            return []

        bk_biz_id = self.instance_getter(self.request, self)[0]
        if int(bk_biz_id):
            return [
                ResourceActionPermission([ActionEnum.IP_WHITELIST_MANAGE], ResourceEnum.BUSINESS, self.instance_getter)
            ]
        else:
            return [ResourceActionPermission([ActionEnum.GLOBAL_IP_WHITELIST_MANAGE])]

    def get_serializer_class(self):
        if self.action == "list":
            return ListIPWhitelistSerializer

        return self.serializer_class

    @common_swagger_auto_schema(
        operation_summary=_("IP白名单详情"),
        responses={status.HTTP_200_OK: IPWhitelistSerializer(label=_("IP白名单详情"))},
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        """单据实例详情"""
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("IP白名单列表"),
        request_body=ListIPWhitelistSerializer,
        auto_schema=PaginatedResponseSwaggerAutoSchema,
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ListIPWhitelistSerializer)
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["bk_biz_id"],
        actions=[ActionEnum.GLOBAL_IP_WHITELIST_MANAGE, ActionEnum.IP_WHITELIST_MANAGE],
        resource_meta=ResourceEnum.BUSINESS,
    )
    def iplist(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        limit, offset = validated_data["limit"], validated_data["offset"]
        count, iplist = IPWhitelist.list_ip_whitelist(validated_data, limit, offset)
        return Response({"count": count, "results": iplist})

    @common_swagger_auto_schema(
        operation_summary=_("创建IP白名单"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: IPWhitelistSerializer(label=_("创建IP白名单"))},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("更新IP白名单"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: IPWhitelistSerializer(label=_("更新IP白名单"))},
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("删除IP白名单"),
        auto_schema=ResponseSwaggerAutoSchema,
        responses={status.HTTP_200_OK: IPWhitelistSerializer(label=_("更新IP白名单"))},
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("批量删除IP白名单"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=DeleteIPWhitelistSerializer)
    def batch_delete(self, request, *args, **kwargs):
        ids = self.params_validate(self.get_serializer_class())["ids"]
        return Response(IPWhitelist.batch_delete(ids))
