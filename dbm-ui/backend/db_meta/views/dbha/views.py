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


@swagger_auto_schema(methods=["get"])
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def cities(request: Request):
    try:
        return JsonResponse({"code": 0, "msg": "", "data": api.dbha.cities()})
    except Exception as e:
        return JsonResponse({"code": 1, "msg": "{}".format(e), "data": ""})


@swagger_auto_schema(
    methods=["get"],
    manual_parameters=[
        openapi.Parameter(
            name="logical_city_ids",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_INTEGER),
            collectionFormat="multi",
        ),
        openapi.Parameter(
            name="addresses",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            collectionFormat="multi",
        ),
        openapi.Parameter(
            name="statuses",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_STRING),
            collectionFormat="multi",
        ),
        openapi.Parameter(name="bk_cloud_id", in_=openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
    ],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def instances(request: Request):
    try:
        return JsonResponse({"code": 0, "msg": "", "data": api.dbha.instances(**request.query_params)})
    except Exception as e:
        return JsonResponse({"code": 1, "msg": "{}".format(e), "data": ""})


@swagger_auto_schema(
    methods=["patch"],
    request_body=openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "ip": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_IPV4),
                "port": openapi.Schema(type=openapi.TYPE_INTEGER),
                "status": openapi.Schema(type=openapi.TYPE_STRING),
                "bk_cloud_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    ),
)
@api_view(["PATCH"])
@permission_classes([AllowAny])
@csrf_exempt
def update_status(request: Request):
    try:
        api.dbha.update_status(request.data)
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})


@swagger_auto_schema(
    methods=["post"],
    request_body=openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "instance1": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ip": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_IPV4),
                        "port": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
                "instance2": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ip": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_IPV4),
                        "port": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
                "bk_cloud_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def swap_role(request: Request):
    try:
        api.dbha.swap_role(request.data)
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def entry_detail(request: Request):
    try:
        api.dbha.entry_detail(request.data)
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def tendis_cluster_swap(request: Request):
    try:
        api.dbha.tendis_cluster_swap(request.data)
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})


@swagger_auto_schema(
    methods=["post"],
    request_body=openapi.Schema(
        type=openapi.TYPE_ARRAY,
        items=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "instance1": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ip": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_IPV4),
                        "port": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
                "instance2": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "ip": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_IPV4),
                        "port": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
                "bk_cloud_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    ),
)
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def swap_ctl_role(request: Request):
    try:
        api.dbha.swap_ctl_role(request.data)
        return JsonResponse({"code": 0, "data": "", "msg": ""})
    except Exception as e:
        return JsonResponse({"code": 1, "data": "", "msg": "{}".format(e)})
