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
from django.utils.crypto import get_random_string
from rest_framework.test import APIRequestFactory

from backend.tests.conftest import mock_bk_user
from backend.utils.local import local


def force_authenticate(request, user=None, token=None):
    request._force_auth_user = user
    request._force_auth_token = token
    local.request = request


def assert_json_response(response, code=0):
    assert response.status_code == 200
    resp = response.json()
    assert resp["code"] == code
    return resp


class AuthorizedAPIRequestFactory(APIRequestFactory):
    def generic(self, method, path, data="", content_type="application/octet-stream", secure=False, **extra):
        request = super().generic(
            method, path, data="", content_type="application/octet-stream", secure=False, **extra
        )
        bk_user = mock_bk_user(get_random_string(6))
        force_authenticate(request, user=bk_user)
        return request
