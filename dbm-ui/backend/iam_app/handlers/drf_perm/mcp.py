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

from typing import Callable, List

from pydantic import TypeAdapter
from rest_framework import permissions

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools import typing
from backend.iam_app.dataclass import ResourceEnum, ResourceMeta
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission


class BaseMcpDetailPermission(ResourceActionPermission):
    """
    集群详情相关动作鉴权
    """

    mcp_auth_parser: Callable = None
    resource_checker: TypeAdapter = None

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从mcp装饰器获得getter
        if self.mcp_auth_parser is None:
            raise ValueError("MCP Permission must set mcp_auth_parser attr, but not found...")
        resources = self.mcp_auth_parser(request, view)

        # resource 存在和类型检查
        if self.resource_checker:
            try:
                self.resource_checker.validate_python(resources)
            except ValueError:
                raise ValueError("resource:{} check failed, confirm the field's type is correct".format(resources))

        if self.resource_checker and not resources:
            raise ValueError("resource check failed, confirm resource exists")

        return resources


class McpDBManagePermission(BaseMcpDetailPermission):
    """
    MCP工具业务管理相关动作鉴权
    鉴权字段：业务列表 List[int]
    """

    resource_checker = TypeAdapter(typing.BizIdList)

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        actions = [ActionEnum.DB_MANAGE]
        resource_meta = ResourceEnum.BUSINESS
        super().__init__(actions=actions, resource_meta=resource_meta)


class McpClusterManagePermission(BaseMcpDetailPermission):
    """
    MCP工具集群详情相关动作鉴权
    鉴权字段：集群列表 List[int]
    """

    resource_checker = TypeAdapter(typing.ClusterIdList)

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=actions, resource_meta=resource_meta)

    def instance_ids_getter(self, request, view):
        cluster_ids = super().instance_ids_getter(request, view)
        cluster_types = list(Cluster.objects.filter(id__in=cluster_ids).values_list("cluster_type", flat=True))

        # 集群类型对应组件必须相同
        db_types = [ClusterType.cluster_type_to_db_type(cluster_type) for cluster_type in cluster_types]
        if len(set(db_types)) > 1:
            raise ValueError("Cluster types must be the same, but got {}".format(set(db_types)))

        # 从获取到集群ID后，决定动作和资源类型
        self.resource_meta = ResourceEnum.cluster_type_to_resource_meta(cluster_types[0])
        self.actions = [ActionEnum.cluster_type_to_action(cluster_types[0], action_key="VIEW")]
        return cluster_ids


class McpTicketToolPermission(BaseMcpDetailPermission):
    """
    MCP创建工具箱单据相关动作鉴权，使用方式：
    1. 工具箱，action_key = MANAGE
    2. 禁用/下架集群 action_key = DESTROY
    鉴权字段：集群列表 List[int]
    """

    resource_checker = TypeAdapter(typing.TicketResourceList)

    def __init__(self, action_key: str = "MANAGE"):
        super().__init__()
        self.action_key = action_key

    def instance_ids_getter(self, request, view):
        cluster_ids = super().instance_ids_getter(request, view)
        # 通过了父类的checker，这里认为集群是同类且存在的
        cluster = Cluster.objects.get(id=cluster_ids[0])
        action = ActionEnum.cluster_type_to_action(cluster.cluster_type, action_key=self.action_key)
        self.actions = [action]
        self.resource_meta = action.related_resource_types[0]
        return cluster_ids


class McpIsDbaPermission(permissions.BasePermission):
    """
    是否是DBA权限来调用该MCP工具
    """

    def has_permission(self, request, view):
        username = request.user.username
        return DBAdministrator.is_dba(username)

    def has_object_permission(self, request, view, obj):
        username = request.user.username
        return DBAdministrator.is_dba(username)
