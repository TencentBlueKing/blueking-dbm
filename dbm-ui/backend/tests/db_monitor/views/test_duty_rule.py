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
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from backend.db_monitor.mock_data import CREATE_CUSTOM_DUTY_RULE, CREATE_HANDOFF_DUTY_RULE
from backend.db_monitor.models import DutyRule
from backend.db_monitor.views.duty_rule import MonitorDutyRuleViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi
from backend.tests.mock_data.db_monitor.duty_rule import LIST_DUTY_RULE
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture
@patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny])
@patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
@patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
def add_duty_rule(db):
    duty_rule = DutyRule.objects.create(**CREATE_HANDOFF_DUTY_RULE)
    return duty_rule


class TestMonitorDutyRuleViewSet:
    @patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    @patch("backend.iam_app.handlers.permission.Permission", PermissionMock)
    def test_list_duty_rule(self, add_duty_rule):
        url = reverse("duty_rule-list")
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["data"]["count"] != 0
        assert DutyRule.objects.exists()

    @patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_create_duty_rule(self, add_duty_rule):
        url = "/apis/monitor/duty_rule/"
        response = client.post(url, data=CREATE_CUSTOM_DUTY_RULE)
        assert response.status_code == 201
        assert DutyRule.objects.count() == 2

    @patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_update_duty_rule(self, add_duty_rule):
        add_duty_rule_id = add_duty_rule.pk
        url = f"/apis/monitor/duty_rule/{add_duty_rule_id}/"
        response = client.put(url, data=CREATE_CUSTOM_DUTY_RULE)
        assert response.status_code == 200
        assert DutyRule.objects.first().name == "固定排班"

    @patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_destroy_duty_rule(self, add_duty_rule):
        add_duty_rule_id = add_duty_rule.pk
        url = f"/apis/monitor/duty_rule/{add_duty_rule_id}/"
        response = client.delete(url)
        assert response.status_code == 200
        assert DutyRule.objects.exists() is False

    @patch.object(MonitorDutyRuleViewSet, "permission_classes")
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_priority_distinct(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        for duty_rule in LIST_DUTY_RULE:
            client.post("/apis/monitor/duty_rule/", data=duty_rule)
        priority_list = client.get("/apis/monitor/duty_rule/priority_distinct/")
        assert len(priority_list.json()["data"]) == 2
