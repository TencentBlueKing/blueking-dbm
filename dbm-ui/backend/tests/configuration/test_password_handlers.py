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
from unittest.mock import patch

import pytest

from backend.configuration.constants import DBType
from backend.configuration.exceptions import PasswordPolicyBaseException
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, TenDBClusterSpiderRole


class TestDBPasswordHandler:
    """测试 DBPasswordHandler 类"""

    @patch("backend.configuration.handlers.password.DBPrivManagerApi.get_random_string")
    @patch("backend.configuration.handlers.password.base64_decode")
    def test_get_random_password(self, mock_decode, mock_api):
        """测试获取随机密码"""
        mock_api.return_value = "base64_encoded_password"
        mock_decode.return_value = "plain_password"

        password = DBPasswordHandler.get_random_password("high")
        assert password == "plain_password"
        mock_api.assert_called_once_with({"security_rule_name": "high"})

    @patch("backend.configuration.handlers.password.DBPrivManagerApi.check_password")
    @patch("backend.configuration.handlers.password.AsymmetricHandler.decrypt")
    @patch("backend.configuration.handlers.password.base64_encode")
    def test_verify_password_strength(self, mock_encode, mock_decrypt, mock_check):
        """测试验证密码强度"""
        mock_decrypt.return_value = "plain_password"
        mock_encode.return_value = "base64_password"
        mock_check.return_value = {"is_strength": True}

        result = DBPasswordHandler.verify_password_strength("encrypted_password", "high")
        assert result["is_strength"] is True
        mock_check.assert_called_once()

    @patch("backend.configuration.handlers.password.DBPrivManagerApi.check_password")
    @patch("backend.configuration.handlers.password.base64_encode")
    def test_verify_password_strength_with_echo(self, mock_encode, mock_check):
        """测试验证密码强度 - 回显密码"""
        mock_encode.return_value = "base64_password"
        mock_check.return_value = {"is_strength": True}

        result = DBPasswordHandler.verify_password_strength("plain_password", "high", echo=True)
        assert "password" in result

    @patch("backend.configuration.handlers.password.DBPrivManagerApi.get_mysql_admin_password")
    @patch("backend.configuration.handlers.password.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.configuration.handlers.password.base64_decode")
    def test_query_admin_password(self, mock_decode, mock_cloud, mock_api):
        """测试查询admin密码"""
        mock_api.return_value = {
            "count": 1,
            "items": [{"ip": "1.1.1.1", "port": 3306, "password": "encoded_pwd", "bk_cloud_id": 0}],
        }
        mock_cloud.return_value = {"0": {"bk_cloud_name": "Default"}}
        mock_decode.return_value = "plain_pwd"

        result = DBPasswordHandler.query_admin_password(
            limit=10, offset=0, bk_biz_id=1, instances=["1.1.1.1:3306"], db_type=DBType.MySQL.value
        )
        assert result["count"] == 1

    def test_query_admin_password_invalid_db_type(self):
        """测试查询admin密码 - 无效的DB类型"""
        with pytest.raises(PasswordPolicyBaseException):
            DBPasswordHandler.query_admin_password(limit=10, offset=0, db_type="invalid_db_type")

    def test_query_admin_password_invalid_instance_format(self):
        """测试查询admin密码 - 无效的实例格式"""
        with pytest.raises(PasswordPolicyBaseException):
            DBPasswordHandler.query_admin_password(
                limit=10, offset=0, instances=["1.1.1.1:3306:extra:invalid"], db_type=DBType.MySQL.value
            )

    def test_get_password_role_tendbcluster_spider_ctl(self):
        """测试获取密码角色 - TenDBCluster spider_ctl"""
        role = DBPasswordHandler._get_password_role(ClusterType.TenDBCluster, "spider_ctl")
        assert role == "tdbctl"

    def test_get_password_role_tendbcluster_spider(self):
        """测试获取密码角色 - TenDBCluster spider"""
        role = DBPasswordHandler._get_password_role(ClusterType.TenDBCluster, TenDBClusterSpiderRole.SPIDER_MASTER)
        assert role == "spider"

    def test_get_password_role_tendbcluster_storage(self):
        """测试获取密码角色 - TenDBCluster storage"""
        role = DBPasswordHandler._get_password_role(ClusterType.TenDBCluster, InstanceRole.REMOTE_MASTER.value)
        assert role == "storage"

    def test_get_password_role_backend_storage(self):
        """测试获取密码角色 - 后端存储"""
        role = DBPasswordHandler._get_password_role(ClusterType.TenDBHA, InstanceInnerRole.MASTER.value)
        assert role == "storage"

    def test_get_password_role_invalid(self):
        """测试获取密码角色 - 无效角色"""
        with pytest.raises(PasswordPolicyBaseException):
            DBPasswordHandler._get_password_role(ClusterType.TenDBHA, "invalid_role")

    @patch("backend.configuration.handlers.password.DBPrivManagerApi.get_password")
    @patch("backend.configuration.handlers.password.base64_decode")
    def test_batch_query_components_password(self, mock_decode, mock_api):
        """测试批量查询组件密码"""
        mock_api.return_value = {
            "items": [
                {"username": "admin", "component": "mysql", "password": "encoded1"},
                {"username": "root", "component": "redis", "password": "encoded2"},
            ]
        }
        mock_decode.side_effect = ["plain1", "plain2"]

        result = DBPasswordHandler.batch_query_components_password(
            [{"username": "admin", "component": "mysql"}, {"username": "root", "component": "redis"}]
        )
        assert result["admin"]["mysql"] == "plain1"
        assert result["root"]["redis"] == "plain2"

    @patch("backend.configuration.handlers.password.DBPasswordHandler.batch_query_components_password")
    def test_get_component_password(self, mock_batch_query):
        """测试获取组件密码"""
        mock_batch_query.return_value = {"admin": {"mysql": "test_password"}}
        password = DBPasswordHandler.get_component_password("admin", "mysql")
        assert password == "test_password"
