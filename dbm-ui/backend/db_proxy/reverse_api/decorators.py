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

from rest_framework.decorators import action
from rest_framework.request import Request

from backend.db_proxy.reverse_api.helper import get_client_ip

logger = logging.getLogger("root")


def reverse_api(url_path, method=None):
    if method is None:
        method = "GET"

    def actual_decorator(func):
        setattr(func, "is_reverse_api", True)
        setattr(func, "reverse_api_method", method.lower())

        @action(url_path=url_path, detail=False, methods=[method.upper()])
        @wraps(func)
        def wrapped_func(obj, request: Request, *args, **kwargs):
            bk_cloud_id = request.query_params.get("bk_cloud_id")
            port_list = request.query_params.getlist("port")
            client_ip = get_client_ip(request)

            wrapped_param = {
                "bk_cloud_id": bk_cloud_id,
                "ip": client_ip,
                "port_list": port_list,
            }
            if method.lower() == "post":
                wrapped_param["data"] = request.data

            return func(obj, **wrapped_param)

        return wrapped_func

    return actual_decorator
