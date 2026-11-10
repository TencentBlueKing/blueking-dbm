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
from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory

from backend.bk_web.middleware import CsrfCookieRefreshMiddleware

EXISTING_CSRF_SECRET = "a" * 32


def fake_view(request):
    return HttpResponse("ok")


def run_middlewares(cookies):
    """按 Django handler 的顺序执行 CsrfViewMiddleware 与 CsrfCookieRefreshMiddleware"""
    request = RequestFactory().get("/")
    request.COOKIES.update(cookies)

    csrf_middleware = CsrfViewMiddleware(fake_view)
    refresh_middleware = CsrfCookieRefreshMiddleware(fake_view)

    csrf_middleware.process_request(request)
    for middleware in (csrf_middleware, refresh_middleware):
        assert middleware.process_view(request, fake_view, (), {}) is None
    return csrf_middleware.process_response(request, fake_view(request))


class TestCsrfCookieRefreshMiddleware:
    def test_set_csrf_cookie_when_missing(self):
        response = run_middlewares({settings.SESSION_COOKIE_NAME: "session"})

        assert response.cookies[settings.CSRF_COOKIE_NAME].value

    def test_renew_existing_csrf_cookie(self):
        response = run_middlewares(
            {settings.SESSION_COOKIE_NAME: "session", settings.CSRF_COOKIE_NAME: EXISTING_CSRF_SECRET}
        )

        assert response.cookies[settings.CSRF_COOKIE_NAME].value == EXISTING_CSRF_SECRET

    def test_skip_request_without_session(self):
        response = run_middlewares({})

        assert settings.CSRF_COOKIE_NAME not in response.cookies
