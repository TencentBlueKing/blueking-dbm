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
from types import FunctionType
from typing import Any

from blueapps.account.models import User
from drf_spectacular.openapi import AutoSchema
from rest_framework.permissions import AllowAny

from backend import env
from backend.bk_web import viewsets


class McpToolsViewSetMeta(type):
    def __new__(cls, name, base, attrs):
        if env.DEBUG_MCP:
            attrs["user_verified_required"] = False
            attrs["app_verified_required"] = False
            attrs["default_permission_class"] = []

            def get_permissions(cls_instance):
                return [AllowAny()]

            def _get_login_exempt_view_func(cls_obj):
                fs = []
                for x, y in cls_obj.__dict__.items():
                    if isinstance(y, FunctionType):
                        m = getattr(y, "is_mcp_tool", False)
                        if m:
                            fs.append(x)

                return {"post": fs}

            def initialize_request(self, request, *args, **kwargs):
                """
                重写 initialize_request 方法，动态注入用户信息
                在 DEBUG_MCP 模式下，从DEBUG_MCP_USERNAME注入到 request.user
                """
                # 使用 type(self) 来动态获取当前类，确保正确调用父类方法
                request = super(viewsets.SystemViewSet, self).initialize_request(request, *args, **kwargs)
                request.user = User.objects.get(username=env.DEBUG_MCP_USERNAME)
                return request

            attrs["get_permissions"] = get_permissions
            attrs["_get_login_exempt_view_func"] = classmethod(_get_login_exempt_view_func)
            attrs["initialize_request"] = initialize_request

        return super().__new__(cls, name, base, attrs)


class McpToolsViewSet(viewsets.SystemViewSet, metaclass=McpToolsViewSetMeta):
    """MCP 工具视图基类，所有的MCP工具视图都继承自这个类"""

    # 设置 schema_class 为 drf-spectacular 的 AutoSchema
    # 这样 generate_resources_yaml 命令可以正确识别并使用 drf-spectacular 生成 schema
    schema_class = AutoSchema

    # MCP 工具需要同时开启用户认证和应用认证，默认为True
    # 这里user_verified_required 和 app_verified_required 比如和视图函数一致
    # 如果确实无需某个认证，则类定义和 mcp_tools_api_decorator 都要改写为False
    user_verified_required = True
    app_verified_required = True

    def get_param(self, pname) -> Any:
        return self.params_validate(self.get_serializer_class())[pname]
