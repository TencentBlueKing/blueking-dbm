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
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.views.password_policy import PasswordPolicyViewSet

logger = logging.getLogger("test")
client = APIClient()
pytestmark = pytest.mark.django_db


class TestPasswordPolicyViewSet:
    """
    PasswordPolicyViewSet的相关api测试类
    """

    @patch.object(PasswordPolicyViewSet, "permission_classes")
    def test_list_config_names(self, mocked_permission_classes):
        mocked_permission_classes.return_value = [AllowAny]
        client.login(username="admin")

        url = reverse("password_policy-update-password-policy")
        response = client.get(url, data={"account_type": "mysql"})
        assert response is not None
