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
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from backend.db_meta import api

logger = logging.getLogger("root")


@swagger_auto_schema(
    methods=["post"],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "proxies": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.TYPE_STRING),
            "master_instance": openapi.Schema(type=openapi.TYPE_STRING),
            "slave_instance": openapi.Schema(type=openapi.TYPE_STRING),
            "immute_domain": openapi.Schema(type=openapi.TYPE_STRING),
            "name": openapi.Schema(type=openapi.TYPE_STRING, description="Optional"),
            "bk_biz_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional"),
            "db_module_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional"),
            "slave_domain": openapi.Schema(type=openapi.TYPE_STRING, description="Optional"),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def fake_create_tendbha_cluster(request: Request):
    try:
        return JsonResponse({"msg": "", "code": 0, "data": api.fake.fake_create_tendbha_cluster(**request.data)})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})


@swagger_auto_schema(
    methods=["post"],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "storage_instance": openapi.Schema(type=openapi.TYPE_STRING),
            "immute_domain": openapi.Schema(type=openapi.TYPE_STRING),
            "name": openapi.Schema(type=openapi.TYPE_STRING, description="Optional"),
            "bk_biz_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional"),
            "db_module_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Optional"),
        },
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def fake_create_tendbsingle(request: Request):
    try:
        return JsonResponse({"msg": "", "code": 0, "data": api.fake.fake_create_tendbsingle(**request.data)})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def fake_reset_tendbha_cluster(request: Request):
    try:
        return JsonResponse({"msg": "", "code": 0, "data": api.fake.fake_reset_tendbha_cluster(**request.data)})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def fake_reset_tendbcluster_cluster(request: Request):
    try:
        return JsonResponse({"msg": "", "code": 0, "data": api.fake.fake_reset_tendbcluster_cluster(**request.data)})
    except Exception as e:  # pylint: disable=broad-except
        return JsonResponse({"msg": "{}".format(e), "code": 1, "data": ""})
