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
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_monitor.mock_data import CREATE_CUSTOM_DUTY_RULE, CREATE_HANDOFF_DUTY_RULE
from backend.db_monitor.models import DutyRule
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


@pytest.mark.django_db
class TestMonitorDutyRuleViewSet:
    """测试轮值规则视图的核心功能"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_class(self, django_db_setup, django_db_blocker):
        with django_db_blocker.unblock():
            from backend.db_monitor.views.duty_rule import MonitorDutyRuleViewSet

            patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny]).start()
            patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: []).start()
            patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi).start()
            patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
            DutyRule.objects.create(**CREATE_HANDOFF_DUTY_RULE)
            yield
            DutyRule.objects.all().delete()

    def test_list_duty_rule(self):
        """测试查询轮值规则列表"""
        url = reverse("duty_rule-list")
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["data"]["count"] != 0

    def test_create_duty_rule(self):
        """测试创建轮值规则"""
        url = "/apis/monitor/duty_rule/"
        response = client.post(url, data=CREATE_CUSTOM_DUTY_RULE)
        assert response.status_code == 201

    def test_retrieve_duty_rule(self):
        """测试获取轮值规则详情"""
        duty_rule = DutyRule.objects.first()
        url = f"/apis/monitor/duty_rule/{duty_rule.id}/"
        response = client.get(url)
        assert response.status_code == 200

    def test_update_duty_rule(self):
        """测试更新轮值规则"""
        duty_rule = DutyRule.objects.first()
        url = f"/apis/monitor/duty_rule/{duty_rule.id}/"
        response = client.put(url, data=CREATE_CUSTOM_DUTY_RULE)
        assert response.status_code == 200

    def test_destroy_duty_rule(self):
        """测试删除轮值规则"""
        duty_rule = DutyRule.objects.first()
        url = f"/apis/monitor/duty_rule/{duty_rule.id}/"
        response = client.delete(url)
        assert response.status_code == 200

    def test_priority_distinct(self):
        """测试轮值规则优先级统计"""
        for duty_rule in LIST_DUTY_RULE:
            client.post("/apis/monitor/duty_rule/", data=duty_rule)
        priority_list = client.get("/apis/monitor/duty_rule/priority_distinct/")
        assert len(priority_list.json()["data"]) >= 1


class TestMonitorDutyRuleConfigViewSet:
    """测试轮值通知配置相关接口"""

    @pytest.fixture(autouse=True)
    def setup_method(self, django_db_blocker):
        with django_db_blocker.unblock():
            from backend.db_monitor.views.duty_rule import MonitorDutyRuleViewSet

            patch.object(MonitorDutyRuleViewSet, "permission_classes", [AllowAny]).start()
            patch.object(MonitorDutyRuleViewSet, "get_permissions", lambda x: []).start()
            patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi).start()
            SystemSettings.objects.filter(key=SystemSettingsEnum.BKM_DUTY_NOTICE.value).delete()
            yield
            SystemSettings.objects.filter(key=SystemSettingsEnum.BKM_DUTY_NOTICE.value).delete()

    def test_duty_notice_config(self):
        """测试查询轮值通知配置"""
        url = "/apis/monitor/duty_rule/duty_notice_config/"
        response = client.get(url)
        assert response.status_code == 200

    @patch("backend.db_periodic_task.models.DBPeriodicTask.create_or_update_periodic_task")
    def test_update_duty_notice_config(self, mock_create_task):
        """测试更新轮值通知配置"""
        mock_task = MagicMock()
        mock_task.task = MagicMock()
        mock_task.task.save = MagicMock()
        mock_create_task.return_value = mock_task

        url = "/apis/monitor/duty_rule/update_duty_notice_config/"
        config_data = {
            "db_type": "mysql",
            "enabled": True,
            "cron": {"hour": "9", "minute": "0", "day_of_week": "1"},
            "after": 7,
            "channels": ["weixin"],
        }
        response = client.post(url, data=config_data)
        assert response.status_code == 200

    @patch("backend.db_periodic_task.local_tasks.send_duty_schedule.apply_async")
    def test_send_duty_notice_schedule(self, mock_apply_async):
        """测试发送轮值排班表"""
        url = "/apis/monitor/duty_rule/send_duty_notice_schedule/"
        response = client.post(url, data={"db_type": "mysql"})
        assert response.status_code == 200
