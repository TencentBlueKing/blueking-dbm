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
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from backend.db_monitor.mock_data import CREATE_POLICY
from backend.db_monitor.models import MonitorPolicy
from backend.db_monitor.views.policy import MonitorPolicyViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture
@patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
@patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
@patch("backend.db_monitor.models.alarm.bkm_save_alarm_strategy")
def add_policy(mocked_bkm_save_alarm_strategy, db):
    mocked_bkm_save_alarm_strategy.return_value = {"id": 3, "other_details": "mocked response"}
    policy = MonitorPolicy.objects.create(**CREATE_POLICY[0])
    return policy


class TestMonitorPolicyViewSet:
    @pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
    def set_empty_middleware(self):
        with patch.object(settings, "MIDDLEWARE", []):
            yield

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    @patch("backend.db_monitor.models.alarm.bkm_save_alarm_strategy")
    def test_create_policy(self, mocked_bkm_save_alarm_strategy, add_policy):
        mocked_bkm_save_alarm_strategy.return_value = {"id": 3, "other_details": "mocked response"}
        url = "/apis/monitor/policy/"
        response = client.post(url, data=CREATE_POLICY[1])
        assert response.status_code == 201
        assert MonitorPolicy.objects.count() == 2

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.iam_app.handlers.permission.Permission", PermissionMock)
    def test_list_policies(self, add_policy):
        url = "/apis/monitor/policy/?bk_biz_id=0"
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"
        assert MonitorPolicy.objects.count() == 1

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_retrive_policies_details(self, add_policy):
        add_policy_id = add_policy.pk
        url = reverse("policy-detail", kwargs={"pk": add_policy_id})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    @patch("backend.db_monitor.models.alarm.bkm_delete_alarm_strategy")
    def test_delete_policy(self, mocked_bkm_delete_alarm_strategy, add_policy):
        mocked_bkm_delete_alarm_strategy.return_value = None
        add_policy_id = add_policy.pk
        url = "/apis/monitor/policy/"
        response = client.delete(f"{url}{add_policy_id}/")
        assert response.status_code == 200
        assert MonitorPolicy.objects.exists() is False

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_db_module_list(self):
        url = "/apis/monitor/policy/db_module_list/?dbtype=mysql"
        response = client.get(url)
        assert response.status_code == 200
