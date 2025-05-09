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
from functools import wraps

from django.http import HttpRequest
from rest_framework.decorators import action

from backend import env
from backend.db_proxy.reverse_api.get_ip_from_request import get_bk_cloud_id, get_client_ip

logger = logging.getLogger("root")


def reverse_api(url_path):
    def actual_decorator(func):
        setattr(func, "is_reverse_api", True)

        @action(url_path=url_path, detail=False, methods=["GET"])
        @wraps(func)
        def wrapped_func(obj, request: HttpRequest, *args, **kwargs):
            if env.DEBUG_REVERSE_API:
                return func(obj, request, *args, **kwargs)

            if not request.GET._mutable:
                request.GET._mutable = True

            bk_cloud_id = get_bk_cloud_id(request)
            client_ip = get_client_ip(request)

            for k, v in list(request.GET.items()):
                if k != "port":
                    request.GET.pop(key=k)

            request.GET["bk_cloud_id"] = bk_cloud_id
            request.GET["ip"] = client_ip
            request.GET._mutable = False
            return func(obj, request, *args, **kwargs)

        return wrapped_func

    return actual_decorator
