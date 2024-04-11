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
from backend.db_monitor.views.policy import MonitorPolicyViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi

pytestmark = pytest.mark.django_db


class TestMonitorPolicyViewSet:
    @pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
    def set_empty_middleware(self):
        with patch.object(settings, "MIDDLEWARE", []):
            yield

    @pytest.fixture
    def client(self):
        client = APIClient()
        client.login(username="admin")
        return client

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_list_policies(self, client):
        url = reverse("policy-list")
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_retrive_policies_details(self, client):
        url = reverse("policy-detail", kwargs={"pk": 1})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "OK"

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_create_policy(self, client):
        url = "/apis/monitor/policy/"
        response = client.post(url, data=CREATE_POLICY)
        assert response.status_code == 200

    @patch.object(MonitorPolicyViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorPolicyViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_db_module_list(self, client):
        url = "/apis/monitor/policy/db_module_list/?dbtype=mysql"
        response = client.get(url)
        assert response.status_code == 200
