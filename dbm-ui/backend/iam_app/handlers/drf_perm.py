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
from typing import List

from bkoauth.jwt_client import JWTClient
from django.utils.translation import ugettext as _
from iam import Resource
from rest_framework import permissions

from backend import env
from backend.flow.models import FlowTree
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import BusinessResourceMeta
from backend.iam_app.handlers.permission import Permission
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


class IAMPermission(permissions.BasePermission):
    """
    作为drf-iam鉴权的基类
    """

    def __init__(self, actions: List[ActionMeta], resources: List[Resource] = None) -> None:
        self.actions = actions
        self.resources = resources or []

    def has_permission(self, request, view):
        # 如果是超级用户或忽略鉴权，则跳过鉴权
        if request.user.is_superuser or env.BK_IAM_SKIP:
            return True

        # 如果没有动作请求，则跳过鉴权
        if not self.actions:
            return True

        iam = Permission(request=request)
        # iam.batch_is_allowed(actions=self.actions, resources=[self.resources], is_raise_exception=True)
        for action in self.actions:
            iam.is_allowed(action=action, resources=self.resources, is_raise_exception=True)

        return True

    def has_object_permission(self, request, view, obj):
        """
        这个方法由子类各自去实现, 通常是子类构造出resource
        """

        return self.has_permission(request, view)


class BusinessIAMPermission(IAMPermission):
    """
    业务相关动作的鉴权
    """

    def __init__(self, actions: List[ActionMeta], resources: List[Resource] = None, bk_biz_id: int = None) -> None:
        self.bk_biz_id = bk_biz_id
        super().__init__(actions, resources)

    def _fetch_biz_id(self, request, view):
        # 从view.kwargs, request.data, request.query_params中尝试获取业务id
        bk_biz_id = self.bk_biz_id or view.kwargs.get("bk_biz_id", 0)
        if not bk_biz_id:
            bk_biz_id = request.data.get("bk_biz_id", 0) or request.query_params.get("bk_biz_id", 0)

        return bk_biz_id

    def has_permission(self, request, view):
        bk_biz_id = self._fetch_biz_id(request, view)
        if not bk_biz_id:
            return True

        self.resources = [BusinessResourceMeta.create_instance(str(bk_biz_id))]
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # 判断当前对象obj是否有bk_biz_id
        obj_bk_biz_id = obj.bk_biz_id if hasattr(obj, "bk_biz_id") else 0
        bk_biz_id = self.bk_biz_id or obj_bk_biz_id
        if bk_biz_id:
            self.resources = [BusinessResourceMeta.create_instance(str(bk_biz_id))]
            return super().has_object_permission(request, view, obj)

        # 否则从view/POST/GET中获取bk_biz_id
        return self.has_permission(request, view)


class ViewBusinessIAMPermission(BusinessIAMPermission):
    """
    业务查看——鉴权
    """

    def __init__(self, bk_biz_id: int = None):
        super().__init__([ActionEnum.VIEW_BUSINESS], bk_biz_id=bk_biz_id)


class DBManageIAMPermission(BusinessIAMPermission):
    """
    数据库管理Permission类
    """

    def __init__(self, bk_biz_id: int = None):
        super().__init__([ActionEnum.DB_MANAGE], bk_biz_id=bk_biz_id)

    def _fetch_key_id(self, request, view, key):
        key_id = view.kwargs.get(key) or request.data.get(key) or request.query_params.get(key)
        return key_id


class GlobalManageIAMPermission(IAMPermission):
    """
    平台管理Permission类
    """

    def __init__(self):
        super().__init__([ActionEnum.GLOBAL_MANAGE])


class TaskFlowIAMPermission(DBManageIAMPermission):
    def _fetch_biz_id(self, request, view):
        bk_biz_id = super()._fetch_biz_id(request, view)
        if not bk_biz_id:
            root_id = self._fetch_key_id(request, view, key="root_id")
            if root_id:
                bk_biz_id = FlowTree.objects.get(root_id=root_id).bk_biz_id

        return bk_biz_id


class TicketIAMPermission(DBManageIAMPermission):
    def _fetch_biz_id(self, request, view):
        bk_biz_id = super()._fetch_biz_id(request, view)
        if not bk_biz_id:
            ticket_id = self._fetch_key_id(request, view, key="id")
            if ticket_id:
                bk_biz_id = Ticket.objects.get(id=ticket_id).bk_biz_id

        return bk_biz_id


class IsAuthenticatedOrAPIGateWayPermission(permissions.BasePermission):
    """
    用户认证或apigw鉴权
    """

    @classmethod
    def verify_jwt_valid(cls, request):
        request.jwt = JWTClient(request)
        if not request.jwt.is_valid:
            logger.error(_("JWT鉴权错误，错误信息: {}").format(request.jwt.error_message))
            return False

        return True

    def has_authenticated_permission(self, request, view):
        return permissions.IsAuthenticated().has_permission(request, view)

    def has_permission(self, request, view):
        if not self.has_authenticated_permission(request, view):
            return self.verify_jwt_valid(request)

        return True
