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
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.models.function_controller import FunctionController
from backend.configuration.serializers import FunctionControllerSerializer

tags = [_("功能开关")]


class FunctionControllerViewSet(viewsets.AuditedModelViewSet):
    """功能开关视图"""

    serializer_class = FunctionControllerSerializer
    queryset = FunctionController.objects.all()

    def _get_custom_permissions(self):
        return []

    @common_swagger_auto_schema(
        operation_summary=_("功能开关列表"),
        responses={status.HTTP_200_OK: FunctionControllerSerializer(_("功能开关"), many=True)},
        tags=tags,
    )
    def list(self, request, *args, **kwargs):
        return Response(FunctionController.get_all_function_controllers())
