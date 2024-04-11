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

from backend.db_monitor.mock_data import CREATE_NOTICE_GROUP
from backend.db_monitor.models import NoticeGroup
from backend.db_monitor.views.notice_group import MonitorNoticeGroupViewSet
from backend.tests.mock_data.db_monitor.bkmonitorv3 import BKMonitorV3MockApi

pytestmark = pytest.mark.django_db

client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestMonitorNoticeGroupViewSet:
    @patch.object(MonitorNoticeGroupViewSet, "permission_classes")
    @patch.object(MonitorNoticeGroupViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_create_notice_group(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        response = client.post("/apis/monitor/notice_group/", data=CREATE_NOTICE_GROUP)
        assert response.status_code == 201
        assert NoticeGroup.objects.exists()

    @patch.object(MonitorNoticeGroupViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorNoticeGroupViewSet, "get_permissions", lambda x: [])
    @patch("backend.db_monitor.models.alarm.BKMonitorV3Api", BKMonitorV3MockApi)
    def test_destroy_notice_group(self):
        create_response = client.post("/apis/monitor/notice_group/", data=CREATE_NOTICE_GROUP)
        create_id = create_response.json()["data"]["id"]
        delete_response = client.delete(f"/apis/monitor/notice_group/{create_id}/")
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "OK"

    @patch.object(MonitorNoticeGroupViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorNoticeGroupViewSet, "get_permissions", lambda x: [])
    def test_get_msg_type(self):
        response = client.get("/apis/monitor/notice_group/get_msg_type/")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 4  # 4种msg_type

    @patch.object(MonitorNoticeGroupViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorNoticeGroupViewSet, "get_permissions", lambda x: [])
    def test_list_group_name(self):
        response = client.get("/apis/monitor/notice_group/list_group_name/")
        assert response.json()["message"] == "OK"
        assert response.status_code == 200

    @patch.object(MonitorNoticeGroupViewSet, "permission_classes", [AllowAny])
    @patch.object(MonitorNoticeGroupViewSet, "get_permissions", lambda x: [])
    def test_list_default_group(self):
        response = client.get("/apis/monitor/notice_group/list_default_group/")
        assert response.json()["message"] == "OK"
        assert response.status_code == 200
