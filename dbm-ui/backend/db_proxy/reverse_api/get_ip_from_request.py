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

from backend.db_proxy.models import DBCloudProxy


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
        return ip
    else:
        raise Exception("client ip in HTTP_X_FORWARDED_FOR not found")


def get_nginx_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[1]
        return ip
    else:
        raise Exception("nginx ip in HTTP_X_FORWARDED_FOR not found")


def get_bk_cloud_id(request):
    nginx_ip = get_nginx_ip(request)
    bk_cloud_id = request.GET.get("bk_cloud_id")

    proxy = DBCloudProxy.objects.get(
        Q(internal_address=nginx_ip, bk_cloud_id=bk_cloud_id) | Q(external_address=nginx_ip, bk_cloud_id=bk_cloud_id)
    )
    return proxy.bk_cloud_id
