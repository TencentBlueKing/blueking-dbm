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
from unittest.mock import patch

import pytest
from django.conf import settings
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.components.dbconfig.constants import LevelName
from backend.db_services.dbconfig.views import ConfigViewSet
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock

logger = logging.getLogger("test")
client = APIClient()
pytestmark = pytest.mark.django_db


class TestConfigViewSet:
    """
    ConfigViewSet的相关api测试类
    """

    def __init__(self):
        patch.object(settings, "MIDDLEWARE", [])

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_list_config_names(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = reverse("config-list-config-names")
        response = client.get(url, data={"meta_cluster_type": "tendbsingle", "conf_type": "dbconf", "version": "1.0"})
        print(response)
        assert list(response.data)[0]["info"] == "dbconf-tendbsingle-1.0"

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_list_platform_configs(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = "/apis/configs/list_platform_configs/"
        response = client.get(url, data={"meta_cluster_type": "tendbsingle", "conf_type": "dbconf"})
        assert len(list(response.data)) == 3

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_get_platform_config(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = "/apis/configs/get_platform_config/"
        response = client.get(
            url, data={"meta_cluster_type": "tendbsingle", "conf_type": "dbconf", "version": "MySQL-5.7"}
        )
        assert response.data["version"] == "MySQL-5.7"

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_list_biz_configs(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = "/apis/configs/list_biz_configs/"
        response = client.get(url, data={"meta_cluster_type": "tendbsingle", "conf_type": "dbconf", "bk_biz_id": 1})
        assert len(list(response.data)) == 3

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_get_level_config(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = "/apis/configs/get_level_config/"
        db_config_level_request = {
            "bk_biz_id": 1,
            "level_name": LevelName.PLAT,
            "level_value": 0,
            "level_info": {},
            "version": "MySQL-6.5",
            "meta_cluster_type": "tendbsingle",
        }
        response = client.post(url, data=db_config_level_request)
        assert response.data["version"] == "MySQL-6.5"

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_list_config_version_history(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        config_version_history_request = {
            "bk_biz_id": 1,
            "version": "MySQL-6.5",
            "level_name": "plat",
            "level_value": "123",
            "level_info": "",
            "meta_cluster_type": "tendbsingle",
        }
        url = "/apis/configs/list_config_version_history/"
        response = client.get(url, data=config_version_history_request)
        assert response.data["conf_file"] == "MySQL-6.5"

    @patch.object(ConfigViewSet, "permission_classes")
    @patch.object(ConfigViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_services.dbconfig.handlers.DBConfigApi", DBConfigApiMock)
    def test_get_config_version_detail(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        version_detail_request = {
            "bk_biz_id": 1,
            "version": "MySQL-6.5",
            "level_name": "plat",
            "level_value": "123",
            "level_info": "",
            "meta_cluster_type": "tendbsingle",
            "revision": "admin",
        }
        url = "/apis/configs/get_config_version_detail/"
        response = client.get(url, data=version_detail_request)
        assert response.data["revision"] == "admin"
