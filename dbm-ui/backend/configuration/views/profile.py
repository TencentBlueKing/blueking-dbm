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
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.models import Profile
from backend.configuration.serializers import ProfileSerializer
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.permission import Permission

SWAGGER_TAG = _("个人配置")


class ProfileViewSet(viewsets.SystemViewSet):
    serializer_class = ProfileSerializer

    def _get_custom_permissions(self):
        return []

    @common_swagger_auto_schema(operation_summary=_("查询个人配置列表"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def get_profile(self, request, *args, **kwargs):
        username = request.user.username
        # 鉴权资源管理和平台管理
        client = Permission()
        resource_manage = client.is_allowed(action=ActionEnum.RESOURCE_MANAGE, resources=[])
        global_manage = client.is_allowed(action=ActionEnum.GLOBAL_MANAGE, resources=[])
        return Response(
            {
                "resource_manage": resource_manage,
                "global_manage": global_manage,
                "username": username,
                "profile": list(Profile.objects.filter(username=username).values("label", "values")),
            }
        )

    @common_swagger_auto_schema(operation_summary=_("新增/更新个人配置"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=ProfileSerializer)
    def upsert_profile(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        Profile.objects.update_or_create(
            defaults={"values": validated_data["values"]},
            username=request.user.username,
            label=validated_data["label"],
        )
        return Response()
