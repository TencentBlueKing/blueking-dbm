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
from unittest import TestCase
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_monitor.views.duty_rule import MonitorDutyRuleViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi
from backend.tests.mock_data.db_monitor.duty_rule import LIST_DUTY_RULE

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")
client = APIClient()


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestMonitorDutyRuleViewSet(TestCase):
    @patch.object(MonitorDutyRuleViewSet, "permission_classes")
    @patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_priority_distinct(self, mocked_permission_classes):
        client.login(username="admin")
        mocked_permission_classes.return_value = [AllowAny]
        for duty_rule in LIST_DUTY_RULE:
            client.post("/apis/monitor/duty_rule/", data=duty_rule)
        priority_list = client.get("/apis/monitor/duty_rule/priority_distinct/")
        assert len(priority_list.json()["data"]) == 2
