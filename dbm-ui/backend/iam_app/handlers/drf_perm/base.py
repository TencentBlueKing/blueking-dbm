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
from typing import Callable, Dict, List

from bk_audit.constants.log import DEFAULT_EMPTY_VALUE, DEFAULT_SENSITIVITY
from bk_audit.contrib.bk_audit.client import bk_audit_client
from bk_audit.log.exporters import BaseExporter
from bk_audit.log.models import AuditContext, AuditInstance
from iam import Resource
from rest_framework import permissions

from backend import env
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.permission import Permission

logger = logging.getLogger("root")


def get_request_key_id(request, key, default=None):
    if request.method == "GET":
        return request.query_params.get(key, default)
    else:
        return request.data.get(key, default)


class CommonInstance(object):
    def __init__(self, data):
        self.instance_id = data.get("id", DEFAULT_EMPTY_VALUE)
        self.instance_name = data.get("name", DEFAULT_EMPTY_VALUE)
        self.instance_sensitivity = data.get("sensitivity", DEFAULT_SENSITIVITY)
        self.instance_origin_data = data.get("origin_data", DEFAULT_EMPTY_VALUE)
        self.instance_data = data

    @property
    def instance(self):
        return AuditInstance(self)


class ConsoleExporter(BaseExporter):
    is_delay = False

    def export(self, events):
        for event in events:
            print(event.to_json_str())


bk_audit_client.add_exporter(ConsoleExporter())


class RejectPermission(permissions.BasePermission):
    """
    永假的权限，用于屏蔽那些拒绝访问的接口
    """

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser


class IAMPermission(permissions.BasePermission):
    """
    作为drf-iam鉴权的基类
    """

    resource_type = None

    def __init__(self, actions: List[ActionMeta], resources: List[Resource] = None) -> None:
        self.actions = actions
        self.resources = resources or []

    def has_permission(self, request, view):
        iam = Permission(request=request)
        context = AuditContext(request=request)
        # 查询类请求（简单定义为所有 GET 请求）不审计
        if request.method != "GET":
            # 审计操作类请求
            for action in self.actions:
                if not self.resources:
                    bk_audit_client.add_event(action=action, audit_context=context)
                for resource in self.resources:
                    bk_audit_client.add_event(
                        action=action,
                        resource_type=self.resource_type() if self.resource_type else resource,
                        audit_context=context,
                        instance=CommonInstance(resource.attribute),
                    )

        # 如果是超级用户或忽略鉴权，则跳过鉴权
        if request.user.is_superuser or env.BK_IAM_SKIP:
            return True

        # 如果没有动作请求，则跳过鉴权
        if not self.actions:
            return True

        for action in self.actions:
            iam.is_allowed(action=action, resources=self.resources, is_raise_exception=True)

        return True

    def has_object_permission(self, request, view, obj):
        """
        这个方法由子类各自去实现, 通常是子类构造出resource
        """

        return self.has_permission(request, view)


class ResourceActionPermission(IAMPermission):
    """
    关联资源(兼容无资源)动作的权限检查
    """

    def __init__(
        self, actions: List[ActionMeta], resource_meta: ResourceMeta = None, instance_ids_getter: Callable = None
    ):
        self.resource_meta = resource_meta
        self.instance_ids_getter = instance_ids_getter
        super(ResourceActionPermission, self).__init__(actions)

    def get_key_id(self, request, view, key, many=False):
        if hasattr(self, key):
            key_id = getattr(self, key)
        else:
            key_id = view.kwargs.get(key) or get_request_key_id(request, key)

        if many:
            key_id = [key_id] if key_id else []

        return key_id

    def get_instance_ids(self, request, view):
        lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field or self.resource_meta.lookup_field

        if self.instance_ids_getter is None:
            # Perform the lookup filtering.
            assert lookup_url_kwarg in view.kwargs, (
                "Expected view %s to be called with a URL keyword argument "
                'named "%s". Fix your URL conf, or set the `.lookup_field` '
                "attribute on the view correctly." % (self.__class__.__name__, lookup_url_kwarg)
            )
            instance_ids = [view.kwargs[lookup_url_kwarg]]
        else:
            instance_ids = self.instance_ids_getter(request, view)

        return instance_ids

    def has_permission(self, request, view):
        # 如果提前定义好资源类型/资源获取方式，才进行资源id创建
        # instance_ids_getter可能会决定action和resource meta
        if self.resource_meta or self.instance_ids_getter:
            instance_ids = self.get_instance_ids(request, view)
            # 如果无动作或者无关联资源，则无需鉴权
            if not self.actions or (self.resource_meta and not instance_ids):
                return True
            # 如果有资源定义，才进行资源创建
            if self.resource_meta:
                self.resources = [self.resource_meta.create_instance(instance_id) for instance_id in instance_ids]

        return super(ResourceActionPermission, self).has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class MoreResourceActionPermission(IAMPermission):
    """
    关联多个其他资源动作的权限检查
    """

    def __init__(
        self,
        actions: List[ActionMeta],
        resource_metas: List[ResourceMeta],
        instance_ids_getters: Dict[str, Callable] = None,
    ):
        self.resource_metas = resource_metas
        self.instance_ids_getters = instance_ids_getters
        super().__init__(actions)

    def get_instance_ids(self, request, view, resource):
        return self.instance_ids_getters[resource.id](request, view)

    def has_permission(self, request, view):
        for resource_meta in self.resource_metas:
            instance_ids = self.get_instance_ids(request, view, resource_meta)
            self.resources.extend([resource_meta.create_instance(instance_id) for instance_id in instance_ids])

        # 如果无关联资源/动作，则无需鉴权
        if not self.resources or not self.actions:
            return True

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return super().has_permission(request, view)


class DBManagePermission(ResourceActionPermission):
    """
    业务相关动作的鉴权
    """

    def __init__(
        self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None, bk_biz_id: int = None
    ) -> None:
        self.bk_biz_id = bk_biz_id
        self.actions = actions or [ActionEnum.DB_MANAGE]
        self.resource_meta = resource_meta or ResourceEnum.BUSINESS
        super().__init__(self.actions, self.resource_meta, instance_ids_getter=self.instance_biz_id_getter)

    def instance_biz_id_getter(self, request, view):
        return self.get_key_id(request, view, self.resource_meta.id, many=True)


class BizDBTypeResourceActionPermission(MoreResourceActionPermission):
    """
    关联业务-集群类型资源动作的鉴权
    """

    def __init__(self, actions: List[ActionMeta], instance_biz_getter: Callable, instance_dbtype_getter: Callable):
        resource_metas = [ResourceEnum.BUSINESS, ResourceEnum.DBTYPE]
        instance_ids_getters = {
            ResourceEnum.BUSINESS.id: instance_biz_getter,
            ResourceEnum.DBTYPE.id: instance_dbtype_getter,
        }
        super().__init__(actions, resource_metas, instance_ids_getters)


class IsAuthenticatedPermission(permissions.BasePermission):
    """
    用户认证
    """

    def has_authenticated_permission(self, request, view):
        return permissions.IsAuthenticated().has_permission(request, view)

    def has_permission(self, request, view):
        return permissions.IsAuthenticated().has_permission(request, view)
