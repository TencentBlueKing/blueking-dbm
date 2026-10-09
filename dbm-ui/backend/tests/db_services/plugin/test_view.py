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
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.permissions import BasePermission

from backend.bk_web import viewsets
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission, RejectPermission

pytestmark = pytest.mark.django_db


# ==================== 辅助类 ====================


class FakePermA(BasePermission):
    """用于测试的假权限 A"""

    def has_permission(self, request, view):
        return True


class FakePermB(BasePermission):
    """用于测试的假权限 B"""

    def has_permission(self, request, view):
        return True


def make_viewset(is_jwt: bool, parent_permissions: list = None):
    """
    构造一个 BaseOpenAPIViewSet 子类实例，并 mock request.is_bk_jwt()。

    :param is_jwt: 模拟是否通过网关 JWT 认证
    :param parent_permissions: 父类 get_permissions 返回的权限实例列表
    :return: 已绑定 mock request 的 viewset 实例
    """

    class ParentViewSet(viewsets.SystemViewSet):
        """模拟一个带有 get_permissions 的父类"""

        def get_permissions(self):
            return parent_permissions or []

    class TestViewSet(BaseOpenAPIViewSet, ParentViewSet):
        pass

    viewset = TestViewSet()
    mock_request = MagicMock()
    mock_request.is_bk_jwt.return_value = is_jwt
    viewset.request = mock_request
    # 模拟 action，避免 _get_custom_permissions 报错
    viewset.action = "list"
    return viewset


# ==================== 测试类 ====================


class TestBaseOpenAPIViewSetPermissions:
    """测试 BaseOpenAPIViewSet.get_permissions() 的权限合并逻辑"""

    def test_with_jwt_no_parent_permissions(self):
        """通过 JWT 认证，父类无额外权限 → 权限列表为空"""
        viewset = make_viewset(is_jwt=True, parent_permissions=[])
        perms = viewset.get_permissions()

        perm_types = [type(p) for p in perms]
        assert RejectPermission not in perm_types, "JWT 认证通过时不应包含 RejectPermission"

    def test_without_jwt_no_parent_permissions(self):
        """未通过 JWT 认证，父类无额外权限 → 只有 RejectPermission"""
        viewset = make_viewset(is_jwt=False, parent_permissions=[])
        perms = viewset.get_permissions()

        perm_types = [type(p) for p in perms]
        assert RejectPermission in perm_types, "未通过 JWT 认证时应包含 RejectPermission"

    def test_with_jwt_with_parent_permissions(self):
        """通过 JWT 认证，父类有额外权限 → 只有父类权限，无 RejectPermission"""
        viewset = make_viewset(is_jwt=True, parent_permissions=[FakePermA(), FakePermB()])
        perms = viewset.get_permissions()

        perm_types = [type(p) for p in perms]
        assert RejectPermission not in perm_types, "JWT 认证通过时不应包含 RejectPermission"
        assert FakePermA in perm_types, "应包含父类权限 FakePermA"
        assert FakePermB in perm_types, "应包含父类权限 FakePermB"

    def test_without_jwt_with_parent_permissions(self):
        """未通过 JWT 认证，父类有额外权限 → RejectPermission 在最前，后跟父类权限"""
        viewset = make_viewset(is_jwt=False, parent_permissions=[FakePermA(), FakePermB()])
        perms = viewset.get_permissions()

        perm_types = [type(p) for p in perms]
        assert perm_types[0] is RejectPermission, "RejectPermission 应排在权限列表第一位"
        assert FakePermA in perm_types, "应包含父类权限 FakePermA"
        assert FakePermB in perm_types, "应包含父类权限 FakePermB"

    def test_deduplication_of_same_permission_type(self):
        """父类返回重复权限类型时，应去重"""
        viewset = make_viewset(is_jwt=True, parent_permissions=[FakePermA(), FakePermA()])
        perms = viewset.get_permissions()

        perm_types = [type(p) for p in perms]
        assert perm_types.count(FakePermA) == 1, "相同权限类型应去重，只保留一个"

    def test_reject_permission_is_superuser_true(self):
        """RejectPermission：超级用户应返回 True（放行）"""
        perm = RejectPermission()
        mock_request = MagicMock()
        mock_request.user.is_superuser = True
        assert perm.has_permission(mock_request, None) is True

    def test_reject_permission_is_superuser_false(self):
        """RejectPermission：非超级用户应返回 False（拦截）"""
        perm = RejectPermission()
        mock_request = MagicMock()
        mock_request.user.is_superuser = False
        assert perm.has_permission(mock_request, None) is False

    def test_cmdb_apigw_viewset_with_jwt_with_action_perm(self):
        """CMDBApiGwViewSet 通过 JWT 认证，create_module 使用 default_permission_class → 应包含 DBManagePermission"""
        from backend.db_services.plugin.cmdb.views import CMDBApiGwViewSet

        viewset = CMDBApiGwViewSet()
        mock_request = MagicMock()
        mock_request.is_bk_jwt.return_value = True
        viewset.request = mock_request
        viewset.action = "create_module"

        perms = viewset.get_permissions()
        perm_types = [type(p) for p in perms]
        assert RejectPermission not in perm_types, "JWT 认证通过时不应包含 RejectPermission"
        assert DBManagePermission in perm_types, "create_module 应使用 default_permission_class，包含 DBManagePermission"

    def test_cmdb_apigw_viewset_without_jwt(self):
        """CMDBApiGwViewSet 未通过 JWT 认证时，RejectPermission 应排在第一位"""
        from backend.db_services.plugin.cmdb.views import CMDBApiGwViewSet

        viewset = CMDBApiGwViewSet()
        mock_request = MagicMock()
        mock_request.is_bk_jwt.return_value = False
        viewset.request = mock_request
        viewset.action = "create_module"

        perms = viewset.get_permissions()
        perm_types = [type(p) for p in perms]
        assert perm_types[0] is RejectPermission, "未通过 JWT 认证时 RejectPermission 应排在第一位"
        assert DBManagePermission in perm_types, "create_module 应包含 DBManagePermission"


class TestTicketApiGwViewSetPermissions:
    """测试 TicketApiGwViewSet.get_permissions() 的权限合并逻辑"""

    def _make_viewset(self, is_jwt: bool, action: str, request_data: dict = None):
        """构造 TicketApiGwViewSet 实例"""
        from backend.db_services.plugin.ticket.views import TicketApiGwViewSet

        viewset = TicketApiGwViewSet()
        mock_request = MagicMock()
        mock_request.is_bk_jwt.return_value = is_jwt
        mock_request.data = request_data or {}
        viewset.request = mock_request
        viewset.action = action
        return viewset

    def test_batch_process_ticket_with_jwt(self):
        """batch_process_ticket：JWT 通过，TicketViewSet 配置为无需鉴权 → 不含 RejectPermission"""
        viewset = self._make_viewset(is_jwt=True, action="batch_process_ticket")
        perms = viewset.get_permissions()
        perm_types = [type(p) for p in perms]
        assert RejectPermission not in perm_types, "batch_process_ticket 无需鉴权，不应包含 RejectPermission"

    def test_batch_process_ticket_without_jwt(self):
        """batch_process_ticket：未通过 JWT → RejectPermission 排在第一位"""
        viewset = self._make_viewset(is_jwt=False, action="batch_process_ticket")
        perms = viewset.get_permissions()
        perm_types = [type(p) for p in perms]
        assert perm_types[0] is RejectPermission, "未通过 JWT 时 RejectPermission 应排在第一位"

    def test_create_with_jwt_registered_ticket_type(self):
        """create：JWT 通过，已注册的单据类型 → 返回 IAM 权限，不含 RejectPermission"""
        from backend.iam_app.handlers.drf_perm.ticket import CreateTicketOneResourcePermission
        from backend.ticket.builders import BuilderFactory

        # mock 一个已注册的 action（关联一种资源）
        mock_action = MagicMock()
        mock_action.related_resource_types = [MagicMock()]  # 只有一种资源，走 OneResource 分支

        with patch.dict(BuilderFactory.ticket_type__iam_action, {"MYSQL_SINGLE_APPLY": mock_action}):
            viewset = self._make_viewset(
                is_jwt=True,
                action="create",
                request_data={"ticket_type": "MYSQL_SINGLE_APPLY", "bk_biz_id": 1},
            )
            perms = viewset.get_permissions()
            perm_types = [type(p) for p in perms]
            assert RejectPermission not in perm_types, "JWT 通过且单据类型已注册时不应包含 RejectPermission"
            assert CreateTicketOneResourcePermission in perm_types, "已注册单资源单据类型应返回 CreateTicketOneResourcePermission"

    def test_create_with_jwt_unregistered_ticket_type(self):
        """create：JWT 通过，未注册的单据类型 → TicketViewSet 返回 RejectPermission"""
        from backend.ticket.builders import BuilderFactory

        # 确保该 key 不在注册表中
        with patch.dict(BuilderFactory.ticket_type__iam_action, {}, clear=False):
            # 使用一个肯定不存在的假类型
            viewset = self._make_viewset(
                is_jwt=True,
                action="create",
                request_data={"ticket_type": "FAKE_UNREGISTERED_TYPE"},
            )
            perms = viewset.get_permissions()
            perm_types = [type(p) for p in perms]
            assert RejectPermission in perm_types, "未注册的单据类型应返回 RejectPermission"

    def test_create_without_jwt_registered_ticket_type(self):
        """create：未通过 JWT，已注册的单据类型 → RejectPermission 排在第一位"""
        from backend.ticket.builders import BuilderFactory

        mock_action = MagicMock()
        mock_action.related_resource_types = [MagicMock()]

        with patch.dict(BuilderFactory.ticket_type__iam_action, {"MYSQL_SINGLE_APPLY": mock_action}):
            viewset = self._make_viewset(
                is_jwt=False,
                action="create",
                request_data={"ticket_type": "MYSQL_SINGLE_APPLY", "bk_biz_id": 1},
            )
            perms = viewset.get_permissions()
            perm_types = [type(p) for p in perms]
            assert perm_types[0] is RejectPermission, "未通过 JWT 时 RejectPermission 应排在第一位"

    def test_create_without_jwt_unregistered_ticket_type(self):
        """create：未通过 JWT，未注册的单据类型 → RejectPermission 排在第一位，且去重后只有一个"""
        from backend.ticket.builders import BuilderFactory

        with patch.dict(BuilderFactory.ticket_type__iam_action, {}, clear=False):
            viewset = self._make_viewset(
                is_jwt=False,
                action="create",
                request_data={"ticket_type": "FAKE_UNREGISTERED_TYPE"},
            )
            perms = viewset.get_permissions()
            perm_types = [type(p) for p in perms]
            assert perm_types[0] is RejectPermission, "未通过 JWT 时 RejectPermission 应排在第一位"
            assert perm_types.count(RejectPermission) == 1, "RejectPermission 应去重，只保留一个"

    def test_bkchat_process_todo_no_permission_required(self):
        """bkchat_process_todo 是回调接口，无论是否通过 JWT 均不含 RejectPermission"""
        from backend.iam_app.handlers.drf_perm.base import RejectPermission

        for is_jwt in [True, False]:
            viewset = self._make_viewset(is_jwt=is_jwt, action="bkchat_process_todo")
            perms = viewset.get_permissions()
            perm_types = [type(p) for p in perms]
            assert (
                RejectPermission not in perm_types
            ), f"bkchat_process_todo 无需鉴权，is_jwt={is_jwt} 时不应包含 RejectPermission"
