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
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from backend.bk_web.middleware import DBMLoginRequiredMiddleware


def _make_request(with_jwt_header: bool, decoded_jwt=None):
    headers = {"HTTP_X_BKAPI_JWT": "forged.jwt.token"} if with_jwt_header else {}
    request = RequestFactory().post("/", **headers)
    request.user = SimpleNamespace(is_authenticated=True, username="normal_user", is_superuser=False)
    # 模拟 blueapps RequestProvider 的原始实现：只判断请求头是否存在
    request.is_bk_jwt = lambda: bool(request.META.get("HTTP_X_BKAPI_JWT", ""))
    if decoded_jwt is not None:
        request.jwt = decoded_jwt
    return request


@pytest.fixture
def middleware():
    with patch.object(DBMLoginRequiredMiddleware.__bases__[0], "process_view", return_value=None):
        yield DBMLoginRequiredMiddleware(get_response=lambda request: None)


class TestDBMLoginRequiredMiddlewareJWT:
    def test_forged_jwt_header_is_not_bk_jwt(self, middleware):
        """网关中间件未能验签(未设置 request.jwt)时，仅携带 X-Bkapi-JWT 头不能被认为是网关请求"""
        request = _make_request(with_jwt_header=True)
        assert request.is_bk_jwt()

        middleware.process_view(request, lambda r: None, (), {})

        assert not request.is_bk_jwt()

    def test_verified_jwt_is_bk_jwt(self, middleware):
        request = _make_request(with_jwt_header=True, decoded_jwt=SimpleNamespace(payload={}))

        middleware.process_view(request, lambda r: None, (), {})

        assert request.is_bk_jwt()

    def test_no_jwt_header(self, middleware):
        request = _make_request(with_jwt_header=False)

        middleware.process_view(request, lambda r: None, (), {})

        assert not request.is_bk_jwt()
