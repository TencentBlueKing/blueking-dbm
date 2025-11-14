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
from drf_spectacular.openapi import AutoSchema

from backend.bk_web import viewsets


class McpToolsViewSet(viewsets.SystemViewSet):
    """MCP 工具视图基类，所有的MCP工具视图都继承自这个类"""

    # 设置 schema_class 为 drf-spectacular 的 AutoSchema
    # 这样 generate_resources_yaml 命令可以正确识别并使用 drf-spectacular 生成 schema
    schema_class = AutoSchema

    # MCP 工具需要同时开启用户认证和应用认证，默认为True
    # 这里user_verified_required 和 app_verified_required 比如和视图函数一致
    # 如果确实无需某个认证，则类定义和 mcp_tools_api_decorator 都要改写为False
    user_verified_required = True
    app_verified_required = True
