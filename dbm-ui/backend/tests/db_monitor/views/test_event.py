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

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.models import DBAdministrator
from backend.db_monitor.views.event import AlertView

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

    patch.object(AlertView, "permission_classes", [AllowAny]).start()
    patch.object(AlertView, "get_permissions", lambda x: []).start()
    patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
    yield


class TestAlertView:
    """测试告警事件视图"""

    @patch("backend.components.BKMonitorV3Api.search_alert")
    def test_search_alert(self, mock_search_alert, django_db_blocker):
        """测试搜索告警事件"""
        # Mock BKMonitorV3Api返回
        mock_search_alert.return_value = {
            "alerts": [
                {
                    "id": "123",
                    "alert_name": "测试告警",
                    "tags": [
                        {"key": "appid", "value": "1"},
                        {"key": "cluster_domain", "value": "test.db"},
                    ],
                    "status": "ABNORMAL",
                    "severity": 1,
                }
            ],
            "total": 1,
            "overview": {},
            "aggs": [],
        }

        # 准备测试数据
        with django_db_blocker.unblock():
            DBAdministrator.objects.filter(bk_biz_id=1).delete()
            DBAdministrator.objects.create(
                bk_biz_id=1,
                db_type="mysql",
                users=["admin", "user1"],
            )

        # 构造请求数据
        start_time = datetime.now() - timedelta(days=1)
        end_time = datetime.now()
        url = "/apis/monitor/event/search/"
        data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "offset": 0,
            "limit": 10,
            "self_manage": False,
            "self_assist": False,
        }

        # 发送请求
        response = client.post(url, data=data, format="json")

        # 验证响应
        assert response.status_code == 200
        result = response.json()
        assert result["code"] == 0
        assert "alerts" in result["data"]
        assert "total" in result["data"]

        # 清理测试数据
        with django_db_blocker.unblock():
            DBAdministrator.objects.filter(bk_biz_id=1).delete()
