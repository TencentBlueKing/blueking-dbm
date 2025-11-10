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
import json

from django.http import JsonResponse
from drf_yasg import openapi
from rest_framework.request import Request

from backend.db_mcp_backends.views.base import BaseMCPView
from backend.db_mcp_backends.views.decorator import mcp_api


class MCPToolDemoViewSet(BaseMCPView):
    @mcp_api(
        scope="demo",
        name="add",
        description="add",
        request_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "a": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
                "b": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
            },
            required=["a", "b"],
        ),
        response_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"result": openapi.Schema(type=openapi.TYPE_INTEGER, description="")},
            required=["result"],
        ),
    )
    def add(self, request: Request, *args, **kwargs):
        body = json.loads(request.body.decode("utf-8"))
        a = body.get("a")
        b = body.get("b")
        return JsonResponse({"code": 0, "data": {"result": a + b}, "message": ""})

    @mcp_api(
        scope="demo",
        name="sub",
        description="sub",
        request_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "a": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
                "b": openapi.Schema(type=openapi.TYPE_INTEGER, description=""),
            },
            required=["a", "b"],
        ),
        response_schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"result": openapi.Schema(type=openapi.TYPE_INTEGER, description="")},
            required=["result"],
        ),
    )
    def sub(self, request: Request, *args, **kwargs):
        body = json.loads(request.body.decode("utf-8"))
        a = body.get("a")
        b = body.get("b")
        return JsonResponse({"code": 0, "data": {"result": a - b}, "message": ""})
