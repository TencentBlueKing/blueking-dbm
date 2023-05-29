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
from rest_framework.test import APIClient

from backend.components import BKMonitorV3Api
from backend.db_monitor.models.alarm import NoticeGroup

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture
def notice_group(db):
    group = NoticeGroup(
        bk_biz_id=0,
        name="TestNoticeGroup",
    )
    return group


class TestNoticeGroup:
    def test_save_monitor_group_success(self, notice_group):
        with patch("backend.db_monitor.models.alarm.NoticeGroup.save_monitor_group", return_value=1), patch(
            "backend.db_monitor.tasks.update_app_policy.delay"
        ):
            notice_group.save()
        assert NoticeGroup.objects.count() == 1

        # 设置result=="True"
        with patch(
            "backend.components.bkmonitorv3.client.BKMonitorV3Api.save_user_group",
            return_value={"result": True, "data": {"id": 1}},
        ):
            NoticeGroup.objects.filter(bk_biz_id=0).update(name="TestNoticeGroup1")
            assert NoticeGroup.objects.first().name == "TestNoticeGroup1"

        # 设置Result=="False" 并且code为有重复告警组名的状态码
        with patch(
            "backend.components.bkmonitorv3.client.BKMonitorV3Api.save_user_group",
            return_value={
                "result": False,
                "code": BKMonitorV3Api.ErrorCode.DUTY_RULE_NAME_ALREADY_EXISTS,
                "data": {"id": 2},
            },
        ), patch("backend.components.bkmonitorv3.client.BKMonitorV3Api.search_user_groups", return_value=[{"id": 10}]):
            NoticeGroup.objects.filter(bk_biz_id=0).update(name="TestNoticeGroup2")
            assert NoticeGroup.objects.first().name == "TestNoticeGroup2"
            assert NoticeGroup.objects.first().monitor_group_id != 0
