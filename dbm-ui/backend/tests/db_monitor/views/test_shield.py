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
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_monitor.views.shield import AlarmShieldView

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """移除中间件"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(autouse=True)
def setup_permissions():
    """设置权限"""
    from backend.tests.mock_data.iam_app.permission import PermissionMock

    patch.object(AlarmShieldView, "permission_classes", [AllowAny]).start()
    patch.object(AlarmShieldView, "get_permissions", lambda x: []).start()
    patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
    yield


class TestAlarmShieldView:
    """测试告警屏蔽视图"""

    @patch("backend.components.BKMonitorV3Api.list_shield")
    def test_list_shield(self, mock_list_shield):
        """测试告警屏蔽列表"""
        # Mock BKMonitorV3Api返回
        mock_list_shield.return_value = {
            "shield_list": [
                {
                    "id": 1,
                    "category": "scope",
                    "description": "test_shield",
                    "begin_time": "2023-01-01 00:00:00",
                    "end_time": "2023-12-31 23:59:59",
                    "is_enabled": True,
                }
            ],
            "total": 1,
        }

        # 发送请求
        url = "/apis/monitor/alarm_shield/?bk_biz_id=1&limit=10&offset=0"
        response = client.get(url)

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "shield_list" in result["data"]
        assert "total" in result["data"]

    @patch("backend.components.BKMonitorV3Api.get_shield")
    def test_retrieve_shield(self, mock_get_shield):
        """测试获取告警屏蔽详情"""
        # Mock BKMonitorV3Api返回
        mock_get_shield.return_value = {
            "id": 1,
            "category": "scope",
            "description": "test_shield",
            "begin_time": "2023-01-01 00:00:00",
            "end_time": "2023-12-31 23:59:59",
        }

        # 发送请求
        url = "/apis/monitor/alarm_shield/1/"
        response = client.get(url)

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert result["data"]["id"] == 1

    @patch("backend.components.BKMonitorV3Api.add_shield")
    def test_create_shield(self, mock_add_shield):
        """测试创建告警屏蔽"""
        # Mock BKMonitorV3Api返回
        mock_add_shield.return_value = {"id": 1, "message": "success"}

        # 发送请求
        url = "/apis/monitor/alarm_shield/"
        data = {
            "bk_biz_id": 1,
            "category": "scope",
            "dimension_config": {
                "scope_type": "instance",
                "dimension_conditions": [{"key": "appid", "value": [1]}],
            },
            "begin_time": "2023-01-01 00:00:00",
            "end_time": "2023-12-31 23:59:59",
            "description": "test shield",
            "shield_notice": False,
        }
        response = client.post(url, data=data, format="json")

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "id" in result["data"]

    @patch("backend.components.BKMonitorV3Api.disable_shield")
    def test_disable_shield(self, mock_disable_shield):
        """测试解除告警屏蔽"""
        # Mock BKMonitorV3Api返回
        mock_disable_shield.return_value = {"message": "success"}

        # 发送请求
        url = "/apis/monitor/alarm_shield/1/disable/"
        response = client.post(url)

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0

    @patch("backend.components.BKMonitorV3Api.get_shield")
    @patch("backend.components.BKMonitorV3Api.edit_shield")
    def test_update_shield(self, mock_edit_shield, mock_get_shield):
        """测试更新告警屏蔽"""
        # Mock BKMonitorV3Api返回
        mock_get_shield.return_value = {
            "id": 1,
            "bk_biz_id": 1,
            "category": "scope",
            "description": "old description",
        }
        mock_edit_shield.return_value = {"id": 1, "message": "success"}

        # 发送请求
        url = "/apis/monitor/alarm_shield/1/"
        data = {
            "begin_time": "2023-01-01 00:00:00",
            "end_time": "2023-12-31 23:59:59",
            "description": "updated shield",
            "cycle_config": {"begin_time": "", "end_time": "", "type": 1},
            "shield_notice": False,
        }
        response = client.put(url, data=data, format="json")

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "id" in result["data"]
