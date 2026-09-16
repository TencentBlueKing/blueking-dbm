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
from rest_framework.test import APIRequestFactory

from backend.db_services.mysql.toolbox.views import TendbHaSlaveInstanceAddDomainSet, ToolboxViewSet
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.exceptions import PermissionDeniedError
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterEditPermission


def _build_post_request(payload, username="test_user"):
    request = MagicMock()
    request.method = "POST"
    request.data = payload
    request.query_params = {}
    request.parser_context = {"kwargs": {}}
    request.user = MagicMock(username=username, is_superuser=False)
    request.COOKIES = {}
    return request


class TestToolboxPermissionMapping:
    """两个写接口必须按集群资源鉴权，不能走无 bk_biz_id 的 DBManage fail-open"""

    def test_change_cluster_spec_uses_cluster_edit_permission(self):
        perms = ToolboxViewSet().get_permission_class_with_action("change_cluster_spec")
        assert len(perms) == 1
        assert isinstance(perms[0], ClusterEditPermission)

    def test_slave_ins_add_domain_uses_cluster_edit_permission(self):
        perms = TendbHaSlaveInstanceAddDomainSet().get_permission_class_with_action("slave_ins_add_domain")
        assert len(perms) == 1
        assert isinstance(perms[0], ClusterEditPermission)

    def test_other_toolbox_actions_keep_db_manage_default(self):
        perms = ToolboxViewSet().get_permission_class_with_action("query_higher_version_pkg_list")
        assert len(perms) == 1
        assert isinstance(perms[0], DBManagePermission)


@pytest.mark.django_db
class TestClusterEditPermissionBind:
    """ClusterEditPermission 以 cluster_id 绑定 IAM 集群资源，而不是客户端业务号"""

    def test_instance_ids_getter_binds_cluster_edit_action(self, dbha_cluster):
        request = _build_post_request({"cluster_id": dbha_cluster.id})
        view = MagicMock()
        view.kwargs = {}
        view.action = "change_cluster_spec"

        perm = ClusterEditPermission()
        cluster_ids = perm.instance_ids_getter(request, view)

        assert cluster_ids == [dbha_cluster.id]
        assert perm.actions == [ActionEnum.MYSQL_EDIT]
        assert perm.resource_meta == ResourceEnum.MYSQL

    def test_db_manage_permission_fail_open_without_bk_biz_id(self):
        """对照：无 bk_biz_id 时 DBManagePermission 会直接放行（本次修复要避开这条路径）"""
        request = _build_post_request({"cluster_id": 1})
        view = MagicMock()
        view.kwargs = {}
        view.action = "change_cluster_spec"

        perm = DBManagePermission()
        with patch("backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP", False):
            assert perm.has_permission(request, view) is True

    def test_cluster_edit_permission_does_not_fail_open(self, dbha_cluster):
        """无 bk_biz_id 但仍应按集群资源走 IAM，拒绝时不得放行"""
        request = _build_post_request({"cluster_id": dbha_cluster.id})
        view = MagicMock()
        view.kwargs = {}
        view.action = "change_cluster_spec"

        perm = ClusterEditPermission()
        denied = PermissionDeniedError("mysql_edit", {}, "http://apply.url")
        with patch("backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP", False):
            with patch("backend.iam_app.handlers.drf_perm.base.Permission") as mock_perm_cls:
                mock_iam = MagicMock()
                mock_iam.is_allowed.side_effect = denied
                mock_perm_cls.return_value = mock_iam

                with pytest.raises(PermissionDeniedError):
                    perm.has_permission(request, view)

                mock_iam.is_allowed.assert_called_once()
                call_kwargs = mock_iam.is_allowed.call_args.kwargs
                assert call_kwargs["action"] == ActionEnum.MYSQL_EDIT
                resources = call_kwargs["resources"]
                assert resources
                assert str(resources[0].id) == str(dbha_cluster.id)


@pytest.mark.django_db
class TestToolboxAuthApiRequest:
    """通过真实视图 check_permissions 验证接口鉴权生效"""

    def test_change_cluster_spec_check_permissions_denies(self, dbha_cluster):
        factory = APIRequestFactory()
        wsgi_request = factory.post(
            "/apis/mysql/toolbox/change_cluster_spec/",
            {
                "cluster_id": dbha_cluster.id,
                "cluster_type": "tendbha",
                "spec_id": 1,
                "machine_type": "backend",
            },
            format="json",
        )
        wsgi_request.user = MagicMock(username="test_user", is_superuser=False)
        wsgi_request.COOKIES = {}

        view = ToolboxViewSet()
        view.action = "change_cluster_spec"
        view.kwargs = {}
        view.request = wsgi_request
        view.format_kwarg = None
        # DRF Request.data 来自 parser，这里用已绑定 cluster_id 的权限检查
        drf_request = MagicMock()
        drf_request.method = "POST"
        drf_request.data = {
            "cluster_id": dbha_cluster.id,
            "cluster_type": "tendbha",
            "spec_id": 1,
            "machine_type": "backend",
        }
        drf_request.query_params = {}
        drf_request.parser_context = {"kwargs": {}}
        drf_request.user = wsgi_request.user
        drf_request.COOKIES = {}

        denied = PermissionDeniedError("mysql_edit", {}, "http://apply.url")
        with patch("backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP", False):
            with patch("backend.iam_app.handlers.drf_perm.base.Permission") as mock_perm_cls:
                mock_iam = MagicMock()
                mock_iam.is_allowed.side_effect = denied
                mock_perm_cls.return_value = mock_iam

                with pytest.raises(PermissionDeniedError):
                    view.check_permissions(drf_request)

                mock_iam.is_allowed.assert_called_once()
                assert mock_iam.is_allowed.call_args.kwargs["action"] == ActionEnum.MYSQL_EDIT

    def test_slave_ins_add_domain_check_permissions_denies(self, dbha_cluster):
        view = TendbHaSlaveInstanceAddDomainSet()
        view.action = "slave_ins_add_domain"
        view.kwargs = {}
        view.format_kwarg = None

        drf_request = MagicMock()
        drf_request.method = "POST"
        drf_request.data = {
            "cluster_id": dbha_cluster.id,
            "slave_ip": "127.0.0.2",
            "slave_port": 3306,
            "domain_name": "slave.example.db",
        }
        drf_request.query_params = {}
        drf_request.parser_context = {"kwargs": {}}
        drf_request.user = MagicMock(username="test_user", is_superuser=False)
        drf_request.COOKIES = {}

        denied = PermissionDeniedError("mysql_edit", {}, "http://apply.url")
        with patch("backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP", False):
            with patch("backend.iam_app.handlers.drf_perm.base.Permission") as mock_perm_cls:
                mock_iam = MagicMock()
                mock_iam.is_allowed.side_effect = denied
                mock_perm_cls.return_value = mock_iam

                with pytest.raises(PermissionDeniedError):
                    view.check_permissions(drf_request)

                mock_iam.is_allowed.assert_called_once()
                assert mock_iam.is_allowed.call_args.kwargs["action"] == ActionEnum.MYSQL_EDIT
