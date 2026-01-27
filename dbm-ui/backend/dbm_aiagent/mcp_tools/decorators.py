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
import inspect
import logging
import os
from collections import defaultdict
from functools import wraps
from typing import Callable, Optional, Type

from apigw_manager.drf.utils import gen_apigateway_resource_config
from apigw_manager.plugin.config import build_bk_header_rewrite
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from backend import env
from backend.dbm_aiagent.mcp_tools.constants import DBMMcpTools
from backend.dbm_aiagent.utils import get_class_from_qualname
from backend.ticket.models import Ticket

logger = logging.getLogger("root")

# 全局注册表：存储 MCP 工具名称到 operation_id 列表的映射
MCP_TOOLS_REGISTRY: defaultdict[str, list[str]] = defaultdict(list)


def _extract_agent_type_and_mcp_type(func: Callable) -> tuple[str, str]:
    """
    从函数所在的模块路径中提取 agent_type 和 mcp_type
    """
    # 获取函数的模块文件路径
    func_file = inspect.getfile(func)
    # 转换为相对于项目根目录的路径
    # 假设项目根目录包含 backend 目录
    abs_path = os.path.abspath(func_file)
    # 查找 backend/dbm_aiagent/mcp_tools 在路径中的位置
    path_parts = abs_path.replace("\\", "/").split("/")

    try:
        # 找到目录的索引
        backend_idx = path_parts.index("backend")
        dbm_aiagent_idx = path_parts.index("dbm_aiagent", backend_idx)
        mcp_tools_idx = path_parts.index("mcp_tools", dbm_aiagent_idx)

        # agent_type 和 mcp_type 应该在 mcp_tools 之后
        agent_type = path_parts[mcp_tools_idx + 1]
        mcp_type = path_parts[mcp_tools_idx + 2].split(".")[0]
        return agent_type, mcp_type
    except (ValueError, IndexError) as e:
        raise ValueError(_("无法从函数路径中提取 agent_type 和 mcp_type: {}").format(func_file)) from e


def mcp_tools_api_decorator(
    description: str,
    request_slz: Type[serializers.Serializer],
    response_slz: Type[serializers.Serializer],
    tags: list[str],
    mcp: list[DBMMcpTools],
    methods: list[str] = ("POST",),
    name_prefix: str = None,
    reference_view: Optional[Callable] = None,
    permission_classes: Optional[list[Type]] = None,
    mcp_auth_parser: Optional[Callable] = None,
    is_public: bool = False,
    allow_apply_permission: bool = False,
    resource_permission_required: bool = True,
    match_subpath: bool = False,
    user_verified_required: bool = False,
    app_verified_required: bool = True,
):
    """
    MCP 工具 API 装饰器
    自动为视图函数添加 extend_schema 装饰器，并支持引用其他视图函数的鉴权和处理逻辑。
    @params description: API 描述
    @params request_slz: 请求参数序列化器类
    @params response_slz: 响应序列化器类
    @params methods: 支持HTTP 方法列表
    @params tags: 标签列表
    @params mcp: MCP工具列表，表示当前API属于哪些MCP工具
    @params reference_view: 引用的视图函数，实际执行时会调用该视图的鉴权和处理逻辑
    @params permission_classes: 使用装饰器提供的权限类进行鉴权（普通视图优先）
    @params auth_parser: 当使用mcp专用permission_class时，使用提供的parser函数解析request参数进行鉴权
    @params is_public: 是否公开
    @params allow_apply_permission: 是否允许申请权限
    @params resource_permission_required: 是否校验资源权限
    @params match_subpath: 匹配所有子路径
    @params user_verified_required: 是否校验用户身份(考虑 mcp 也有后台调用，默认都已应用态接口开放)
    @params app_verified_required: 是否校验应用身份
    @returns 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        setattr(func, "is_mcp_tool", True)
        # 先用 rest-action 装饰
        func = action(methods=methods, detail=False, serializer_class=request_slz)(func)

        # 提取 agent_type 和 mcp_type，生成 operation_id
        agent_type, mcp_type = _extract_agent_type_and_mcp_type(func)
        if not name_prefix:
            operation_id = f"mcp_{agent_type}_{mcp_type}_{func.__name__}"
        else:
            operation_id = f"{name_prefix}_{func.__name__}"

        # 注册 operation_id 到 MCP 工具的映射（按 MCP 工具分组存储）
        for mcp_tool in mcp or []:
            MCP_TOOLS_REGISTRY[mcp_tool].append(operation_id)

        # 自动添加 mcp-tools tag
        tags.append("mcp-tools")
        # 创建 extend_schema 装饰器
        schema_decorator = extend_schema(
            operation_id=operation_id,
            description=description,
            # parameters=[request_slz] if request_slz else None,
            request=request_slz,
            responses={200: response_slz} if response_slz else None,
            methods=methods,
            tags=tags,
            exclude=False,
            extensions=gen_apigateway_resource_config(
                enable_mcp=True,  # 固定为 True
                is_public=is_public,
                allow_apply_permission=allow_apply_permission,
                user_verified_required=user_verified_required,
                app_verified_required=app_verified_required,
                resource_permission_required=resource_permission_required,
                description_en=description,
                match_subpath=match_subpath,
                plugin_configs=[
                    build_bk_header_rewrite(set={"X-Bkdbm-Mcp-Tag": ",".join(tags)}, remove=[]),
                ],
            ),
        )

        def resolve_permission_classes(view_instance, action_name: str, is_reference: bool = False) -> list:
            if env.DEBUG_MCP:
                return []

            if is_reference or permission_classes is None:
                try:
                    return view_instance.get_permission_class_with_action(action_name)
                except Exception:  # pylint: disable=broad-except
                    raise ValueError(_("无法获取引用视图类权限类：{}").format(func.__name__))

            return permission_classes

        def check_permissions(view_instance, request, permission_class_list):
            for permission_class in permission_class_list or []:
                permission = permission_class() if isinstance(permission_class, type) else permission_class
                setattr(permission, "mcp_auth_parser", mcp_auth_parser)
                if not permission.has_permission(request, view_instance):
                    raise PermissionDenied(detail=_("用户权限不足：{}").format(permission.__class__.__name__))

        # 指定视图函数，包装函数以调用 reference_view 的逻辑
        if reference_view:
            # 确保视图函数名称和原引用视图函数名称一致
            if func.__name__ != reference_view.__name__:
                raise ValueError(_("视图函数名称 '{}' 必须与引用视图函数名称 '{}' 一致").format(func.__name__, reference_view.__name__))

            # 获取 reference_view 所属的视图类（都是未绑定方法，直接使用 __qualname__）
            reference_view_class = get_class_from_qualname(reference_view)
            if not reference_view_class:
                raise ValueError(_("无法获取引用视图类：{} 请检查是否存在").format(reference_view.__name__))

            @wraps(func)
            def wrapper(self, request, *args, **kwargs):
                if self.action != reference_view.__name__:
                    raise ValueError(_("视图函数:{}与引用视图函数{}不一致").format(self.action, reference_view.__name__))

                # 创建临时视图实例用于获取引用视图权限类
                temp_view_instance = None
                try:
                    temp_view_instance = reference_view_class()
                except Exception:  # pylint: disable=broad-except
                    logger.warning(_("无法实例化引用视图：{}").format(reference_view.__name__))

                # 获取引用视图权限类进行鉴权
                resolved_permission_classes = resolve_permission_classes(
                    temp_view_instance, self.action, is_reference=True
                )
                check_permissions(self, request, resolved_permission_classes)

                # 调用 reference_view 的处理逻辑
                return reference_view(self, request, *args, **kwargs)

            decorated_func = schema_decorator(wrapper)
            setattr(decorated_func, "is_mcp_tool", True)
            return decorated_func
        else:
            # 普通视图函数
            @wraps(func)
            def wrapper(self, request, *args, **kwargs):
                resolved_permission_classes = resolve_permission_classes(self, self.action)
                check_permissions(self, request, resolved_permission_classes)
                return func(self, request, *args, **kwargs)

            decorated_func = schema_decorator(wrapper)
            setattr(decorated_func, "is_mcp_tool", True)
            return decorated_func

    return decorator


def bill_response_wrapper(func):
    def wrapper(*args, **kwargs):
        re = func(*args, **kwargs)

        if isinstance(re, Ticket):
            return [{"bill_id": re.pk, "bill_url": re.url}]
        elif isinstance(re, list) and all(isinstance(x, Ticket) for x in re):
            return [{"bill_id": ele.pk, "bill_url": ele.url} for ele in re]
        else:
            raise Exception("unexpected exception in bill wrapper")

    return wrapper
