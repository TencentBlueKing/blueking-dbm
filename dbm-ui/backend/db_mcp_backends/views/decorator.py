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
from functools import wraps

from drf_yasg import openapi
from openapi_schema_to_json_schema import to_json_schema
from rest_framework.decorators import action

from backend.db_mcp_backends.views.mcp_discovery import mcp_handlers


def mcp_api(scope: str, name: str, description: str, request_schema: openapi.Schema, response_schema: openapi.Schema):
    def decorator(view_func):
        request_json_schema = to_json_schema(request_schema)
        response_json_schema = to_json_schema(response_schema)

        # scope = view_func.__qualname__.split(".")[0].lower()
        # print(view_func.__module__)
        # print(view_func.__qualname__)

        mcp_handlers.append(
            {
                "name": f"handlers/{scope}/{name}",
                "description": description,
                "input_schema": request_json_schema,
                "output_schema": response_json_schema,
            }
        )

        @action(url_path=f"handlers/{scope}/{name}", detail=False, methods=["POST"])
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
