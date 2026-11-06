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
from blueapps.account.models import User
from rest_framework.response import Response

from backend import env
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.exceptions import GetSystemInfoError, PermissionDeniedError
from backend.iam_app.handlers.backends import IAMV3Backend
from backend.iam_app.handlers.permission import Permission
from backend.tests.mock_data import constant

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup_users(test_username):
    """创建测试用户"""
    User.objects.get_or_create(username=test_username, defaults={"is_superuser": False})
    User.objects.get_or_create(username="admin", defaults={"is_superuser": True})


class TestPermission:
    """测试Permission类"""

    def test_init_with_request(self, mock_request):
        """测试使用request初始化"""
        perm = Permission(request=mock_request)
        assert perm.username == mock_request.user.username
        assert perm.bk_token == ""

    def test_init_with_username(self, test_username):
        """测试使用username初始化"""
        perm = Permission(username=test_username)
        assert perm.username == test_username

    def test_get_system_info(self, test_username, mock_iam_client):
        """测试获取系统信息"""
        perm = Permission(username=test_username)
        perm.backend = IAMV3Backend(mock_iam_client)

        info = perm.get_system_info()

        assert info["id"] == env.BK_IAM_SYSTEM_ID

    def test_get_system_info_failure(self, test_username, mock_iam_client):
        """测试获取系统信息失败"""
        mock_iam_client._client.query.return_value = (False, "error message", {})
        perm = Permission(username=test_username)
        perm.backend = IAMV3Backend(mock_iam_client)

        with pytest.raises(GetSystemInfoError, match="error message"):
            perm.get_system_info()

    def test_get_system_info_request_error(self, test_username, mock_iam_client):
        """IAM请求异常时同样抛出GetSystemInfoError"""
        mock_iam_client._client.query.side_effect = RuntimeError("iam down")
        perm = Permission(username=test_username)
        perm.backend = IAMV3Backend(mock_iam_client)

        with pytest.raises(GetSystemInfoError):
            perm.get_system_info()

    def test_setup_meta(self):
        """测试设置元数据"""
        Permission.setup_meta()
        Permission.setup_meta()  # 测试幂等性

    def test_make_resource_instance(self):
        """测试创建资源实例"""
        resource = Permission.make_resource_instance("biz", str(constant.BK_BIZ_ID))
        assert resource.type == "biz"
        assert resource.id == str(constant.BK_BIZ_ID)

    def test_check_resource_is_local_business(self, test_cluster_for_iam):
        """测试检查业务资源是否本地"""
        resource = ResourceEnum.MYSQL.create_instance(str(test_cluster_for_iam.id))
        result = IAMV3Backend.check_resource_is_local([resource])
        assert result is True

    def test_batch_make_resource_instance(self):
        """测试批量创建资源实例"""
        resources_data = [{"type": "biz", "id": str(constant.BK_BIZ_ID)}]
        resources = Permission.batch_make_resource_instance(resources_data)
        assert len(resources) > 0

    def test_make_request(self, test_username):
        """测试创建IAM请求"""
        perm = Permission(username=test_username)
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        request = perm.make_request(ActionEnum.DB_MANAGE, [resource])

        assert request.subject.id == test_username

    def test_make_multi_request(self, test_username):
        """测试创建多动作IAM请求"""
        perm = Permission(username=test_username)
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        multi_request = perm.make_multi_request([ActionEnum.DB_MANAGE, ActionEnum.GLOBAL_MANAGE], [resource])

        assert multi_request.subject.id == test_username
        assert len(multi_request.actions) == 2

    def test_is_allowed_success(self, test_username, mock_iam_backend):
        """测试权限验证成功"""
        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        result = perm.is_allowed(ActionEnum.DB_MANAGE, [resource])

        assert result is True

    def test_is_allowed_denied(self, test_username, mock_iam_backend):
        """测试权限验证失败"""
        mock_iam_backend.is_allowed.return_value = False

        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        with pytest.raises(PermissionDeniedError):
            perm.is_allowed(ActionEnum.DB_MANAGE, [resource], is_raise_exception=True)
        mock_iam_backend.get_apply_url.assert_called_once()

    def test_multi_actions_is_allowed(self, test_username, mock_iam_backend):
        """测试多动作权限验证"""
        mock_iam_backend.multi_actions_is_allowed.return_value = {"db_manage": True, "global_manage": False}

        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        result = perm.multi_actions_is_allowed([ActionEnum.DB_MANAGE, ActionEnum.GLOBAL_MANAGE], [resource])

        assert result["db_manage"] is True
        assert result["global_manage"] is False

    def test_batch_is_allowed(self, test_username, mock_iam_backend, test_app_cache):
        """测试批量权限验证"""
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))
        mock_iam_backend.batch_is_allowed.return_value = {str(constant.BK_BIZ_ID): {"db_manage": True}}

        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend

        result = perm.batch_is_allowed(
            [ActionEnum.DB_MANAGE],
            [[resource]],
        )

        assert str(constant.BK_BIZ_ID) in result

    def test_policy_query(self, test_username, mock_iam_backend):
        """测试策略查询"""
        obj_list = [str(constant.BK_BIZ_ID), "99999"]
        mock_iam_backend.policy_query.return_value = [str(constant.BK_BIZ_ID)]

        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend

        policy = perm.policy_query(ActionEnum.DB_MANAGE, obj_list)

        # 只返回有权限的对象
        assert isinstance(policy, list)
        assert str(constant.BK_BIZ_ID) in policy

    def test_make_application(self, mock_iam_client):
        """测试创建权限申请"""
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        app = IAMV3Backend(mock_iam_client).make_application([ActionEnum.DB_MANAGE.id], [[resource]])

        assert app.system_id == env.BK_IAM_SYSTEM_ID
        assert [action.id for action in app.actions] == [ActionEnum.DB_MANAGE.id]

    def test_get_apply_url(self, mock_iam_client):
        """测试获取申请URL"""
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        url = IAMV3Backend(mock_iam_client).get_apply_url([ActionEnum.DB_MANAGE.id], [[resource]])

        assert url == "http://apply.url"

    def test_get_apply_url_request_error(self, mock_iam_client):
        """IAM请求异常时回落到权限中心首页"""
        mock_iam_client.get_apply_url.side_effect = RuntimeError("iam down")
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        url = IAMV3Backend(mock_iam_client).get_apply_url([ActionEnum.DB_MANAGE.id], [[resource]])

        assert url == env.IAM_APP_URL

    def test_get_apply_data(self, test_username):
        """测试获取申请数据"""
        perm = Permission(username=test_username)
        resource = ResourceEnum.BUSINESS.create_instance(str(constant.BK_BIZ_ID))

        data, url = perm.get_apply_data([ActionEnum.DB_MANAGE], [[resource]])

        assert len(data) > 0

    def test_grant_creator_actions(self, test_username, mock_iam_backend, test_cluster_for_iam):
        """测试授权创建者。V3走属性授权、V4走角色实例授权，差异由后端消化"""
        perm = Permission(username=test_username)
        perm.backend = mock_iam_backend
        resource = ResourceEnum.MYSQL.create_instance(str(test_cluster_for_iam.id))

        result = perm.grant_creator_actions(resource, test_username)

        assert result is not None
        mock_iam_backend.grant_creator_actions.assert_called_once_with(resource, test_username)

    @patch("backend.iam_app.handlers.permission.Permission")
    def test_insert_permission_field(self, mock_perm_class, test_username, test_app_cache):
        """测试插入权限字段"""
        mock_perm_instance = MagicMock()
        mock_perm_instance.batch_is_allowed.return_value = {str(constant.BK_BIZ_ID): {"db_manage": True}}
        mock_perm_class.return_value = mock_perm_instance

        response = Response(data=[{"id": constant.BK_BIZ_ID}])

        Permission.insert_permission_field(
            response,
            actions=[ActionEnum.DB_MANAGE],
            resource_meta=ResourceEnum.BUSINESS,
            id_field=lambda item: item["id"],
        )

        assert mock_perm_class.called

    @patch("backend.iam_app.handlers.permission.Permission")
    def test_insert_external_permission_field(self, mock_perm_class, mock_request, test_app_cache):
        """测试外部插入权限字段"""
        mock_perm_instance = MagicMock()
        mock_perm_instance.multi_actions_is_allowed.return_value = {"db_manage": True}
        mock_perm_class.return_value = mock_perm_instance

        response = Response(data={"count": 10})

        Permission.insert_external_permission_field(
            response,
            actions=[ActionEnum.DB_MANAGE],
            resource_meta=ResourceEnum.BUSINESS,
            resource_id=str(constant.BK_BIZ_ID),
        )

        assert mock_perm_class.called

    def test_decorator_permission_field(self):
        """测试装饰器插入权限字段"""

        @Permission.decorator_permission_field(
            actions=[ActionEnum.DB_MANAGE],
            resource_meta=ResourceEnum.BUSINESS,
            id_field=lambda item: item["id"],
        )
        def test_view(request):
            return Response(data=[{"id": constant.BK_BIZ_ID}])

        assert callable(test_view)

    def test_decorator_external_permission_field(self):
        """测试装饰器外部插入权限字段"""

        @Permission.decorator_external_permission_field(
            actions=[ActionEnum.DB_MANAGE],
            resource_meta=ResourceEnum.BUSINESS,
        )
        def test_view(request):
            return Response(data={"count": 10})

        assert callable(test_view)
