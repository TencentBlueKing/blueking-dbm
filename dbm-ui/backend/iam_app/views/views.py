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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.iam_app.handlers.permission import Permission
from backend.iam_app.serializers import IamActionResourceRequestSerializer

SWAGGER_TAG = "iam"


class IAMViewSet(viewsets.SystemViewSet):
    serializer_class = None
    permission_classes = ()

    @common_swagger_auto_schema(operation_summary=_("获取系统权限中心信息"), tags=[SWAGGER_TAG])
    @action(methods=["GET"], detail=False)
    def get_system_info(self, request, *args, **kwargs):
        result = Permission(username=request.user.username).get_system_info()
        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("检查当前用户对该动作是否有权限"), request_body=IamActionResourceRequestSerializer(), tags=[SWAGGER_TAG]
    )
    @action(detail=False, methods=["POST"], serializer_class=IamActionResourceRequestSerializer)
    def check_allowed(self, request, *args, **kwargs):
        action_ids = self.validated_data.get("action_ids", [])
        resources = self.validated_data.get("resources", [])

        result = []
        client = Permission(username=request.user.username)
        resources = client.batch_make_resource_instance(resources)
        for action_id in action_ids:
            is_allowed = client.is_allowed(action_id, resources)
            result.append({"action_id": action_id, "is_allowed": is_allowed})

        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("获取权限申请数据"), request_body=IamActionResourceRequestSerializer(), tags=[SWAGGER_TAG]
    )
    @action(detail=False, methods=["POST"], serializer_class=IamActionResourceRequestSerializer)
    def get_apply_data(self, request, *args, **kwargs):
        action_ids = self.validated_data.get("action_ids", [])
        resources = self.validated_data.get("resources", [])
        client = Permission(username=request.user.username)
        resources = client.batch_make_resource_instance(resources)
        apply_data, apply_url = client.get_apply_data(action_ids, resources)
        return Response({"permission": apply_data, "apply_url": apply_url})
