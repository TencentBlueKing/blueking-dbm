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
from django.db.models import Q
from rest_framework.request import Request

from backend import env
from backend.db_meta.models import Machine
from backend.db_proxy.constants import DB_CLOUD_MACHINE_EXPIRE_TIME, DB_CLOUD_PROXY_EXPIRE_TIME, ExtensionType
from backend.db_proxy.models import DBExtension
from backend.utils.redis import check_set_member_in_redis


def get_client_ip(request: Request):
    if env.DEBUG_REVERSE_API:
        return request.query_params.get("ip")

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
        return ip
    else:
        raise Exception("client ip in HTTP_X_FORWARDED_FOR not found")


def validate_nginx_ip(bk_cloud_id: int, request: Request):
    # TODO: 在容器化场景会有问题，因为此时nginx ip是一个域名
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        nginx_ip = x_forwarded_for.split(", ")[1]
    else:
        raise Exception("nginx ip in HTTP_X_FORWARDED_FOR not found")

    cache_key = f"cache_cloud_nginx_{bk_cloud_id}"
    check_nginx = lambda *args: DBExtension.objects.get(  # noqa: E731
        Q(bk_cloud_id=bk_cloud_id, extension=ExtensionType.NGINX)
        & (Q(details__ip=nginx_ip) | Q(details__bk_outer_ip=nginx_ip))
    )
    try:
        check_set_member_in_redis(cache_key, nginx_ip, check_nginx, DB_CLOUD_PROXY_EXPIRE_TIME)
    except DBExtension.DoesNotExist:
        raise DBExtension.DoesNotExist(f"DBCloudProxy not found for ip {nginx_ip}, bk_cloud_id {bk_cloud_id}")


def validate_machine_ip(bk_cloud_id: int, request: Request):
    client_ip = get_client_ip(request)
    cache_key = f"cache_cloud_machine_{bk_cloud_id}"
    check_machine = lambda *args: Machine.objects.get(ip=client_ip, bk_cloud_id=bk_cloud_id)  # noqa: E731
    try:
        check_set_member_in_redis(cache_key, client_ip, check_machine, DB_CLOUD_MACHINE_EXPIRE_TIME)
    except Machine.DoesNotExist:
        raise Machine.DoesNotExist(f"Machine not found for ip {client_ip}, bk_cloud_id {bk_cloud_id}")
