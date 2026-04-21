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

from blueapps.account.models import User

from backend.bk_web import viewsets
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")


class BaseOpenAPIViewSet(viewsets.SystemViewSet):
    """
    openapi 视图基类

    支持多父类权限合并：当子类同时继承多个具有权限配置的父类时，
    会自动收集并执行所有父类的权限检查。
    """

    def get_permissions(self) -> list:
        # 默认访问openapi的客户端都通过了网关jwt认证
        jwt_permission = [] if self.request.is_bk_jwt() else [RejectPermission()]

        # 调用 MRO 中 BaseOpenAPIViewSet 之后的父类的 get_permissions，避免递归调用自身
        other_permissions = super(BaseOpenAPIViewSet, self).get_permissions()

        # 合并时整体去重，避免 jwt_permission 与 other_permissions 中出现重复类型
        seen = set()
        result = []
        for perm in [*jwt_permission, *other_permissions]:
            perm_type = type(perm)
            if perm_type not in seen:
                seen.add(perm_type)
                result.append(perm)

        return result

    @classmethod
    def get_or_create_user(cls, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return User.objects.create(username=username)
