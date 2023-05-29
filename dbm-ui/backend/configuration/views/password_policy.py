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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.models.password_policy import PasswordPolicy
from backend.configuration.serializers import GetPasswordPolicySerializer, PasswordPolicySerializer
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission

SWAGGER_TAG = _("密码安全策略")


class PasswordPolicyViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == self.get_password_policy.__name__:
            return []

        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询密码安全策略"),
        query_serializer=GetPasswordPolicySerializer,
        responses={status.HTTP_200_OK: PasswordPolicySerializer},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetPasswordPolicySerializer)
    def get_password_policy(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        account_type = validated_data["account_type"]
        policy = PasswordPolicy.safe_get(account_type=account_type)
        return Response(getattr(policy, "policy", None))

    @common_swagger_auto_schema(
        operation_summary=_("更新密码安全策略"), request_body=PasswordPolicySerializer, tags=[SWAGGER_TAG]
    )
    @action(methods=["POST"], detail=False, serializer_class=PasswordPolicySerializer)
    def update_password_policy(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        PasswordPolicy.objects.update_or_create(account_type=validated_data["account_type"], defaults=validated_data)
        return Response()
