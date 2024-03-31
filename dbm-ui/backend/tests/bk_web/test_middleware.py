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
import json
import logging
from unittest.mock import patch

import pytest
from blueapps.account.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from backend import env
from backend.bk_web.models import ExternalUserMapping
from backend.tests.mock_data.components.dnconsole import DBConsoleApiMock

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()


@pytest.fixture(autouse=True)
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        # 创建外部用户和内外部用户映射
        User.objects.create(username="external_user", password="123456")
        User.objects.create(username="user", password="123456")
        ExternalUserMapping.objects.create(internal_username="admin", external_username="external_user")
        yield
        User.objects.filter(username="external_user").delete()
        ExternalUserMapping.objects.all().delete()


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_middleware():
    with patch.object(
        settings,
        "MIDDLEWARE",
        [
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "backend.bk_web.middleware.ExternalProxyMiddleware",
        ],
    ):
        yield


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_user_backends():
    with patch.object(settings, "AUTHENTICATION_BACKENDS", ["backend.tests.bk_web.FakeUserBackend"]):
        yield


class TestMiddleware:
    """中间件的测试样例"""

    @patch("backend.bk_web.viewsets.DBConsoleApi", DBConsoleApiMock())
    def test_external_proxy_middleware(self):
        env.ENABLE_EXTERNAL_PROXY = True
        env.EXTERNAL_PROXY_DOMAIN = "https://dbm.external.example.com"

        # 1. 尝试访问不存在的路由(eg: 污点池)，会得到500
        user = User.objects.get(username="external_user")
        client.force_login(user=user)
        raw = client.get("/apis/partition/", data={})
        response = json.loads(raw.content.decode("utf-8"))
        assert not response["result"]

        # 2. 访问正确路由，得到200
        raw = client.get("/apis/mysql/bizs/3/tendbha_resources/", data={})
        assert raw.status_code == status.HTTP_200_OK

        # 3. 访问本地路由，不做校验
        response = client.get("/ping", data={})
        assert response.content.decode("utf-8") == "pong"
        client.logout()
