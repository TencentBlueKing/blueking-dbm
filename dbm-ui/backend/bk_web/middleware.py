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

from blueapps.account.middlewares import LoginRequiredMiddleware
from blueapps.account.models import User
from django.contrib.auth.models import AnonymousUser

from backend import env
from backend.utils.local import local

logger = logging.getLogger("root")


class DisableCSRFCheckMiddleware:
    """本地开发，去掉 django rest framework 强制的 csrf 检查"""

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        setattr(request, "_dont_enforce_csrf_checks", True)

        response = self.get_response(request)
        return response


class RequestProviderMiddleware:
    """
    request_id 中间件
    调用链使用
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        local.request = request
        request.request_id = local.get_http_request_id()

        response = self.get_response(request)
        response["X-Request-Id"] = request.request_id

        local.release()
        return response


class DBMLoginRequiredMiddleware(LoginRequiredMiddleware):
    """DBM自定义的登录中间件，主要用于增加额外的鉴权格式"""

    def process_view(self, request, view, args, kwargs):
        """
        对于这里的登录用户，分为以下情况：
        1. 如果是已认证用户，则直接返回
        2. 如果用的dbm的APP CODE和APP TOKEN，则认为是服务内调用，授予超级用户
        3. 如果是apigw认证通过，则授予请求头中X-Bkapi-Apigw的用户
        """

        def authorize_admin_user():
            request.user = User(username="admin", is_superuser=True)
            request.internal_call = True
            setattr(request, "_dont_enforce_csrf_checks", True)

        def authorize_valid_user():
            username = request.jwt.payload.get("user", {}).get("username", None)
            request.user = User(username=username) if username else AnonymousUser()
            setattr(request, "_dont_enforce_csrf_checks", True)

        bk_app_code = request.COOKIES.get("bk_app_code")
        bk_app_secret = request.COOKIES.get("bk_app_secret")

        if request.user and request.user.is_authenticated:
            return super().process_view(request, view, args, kwargs)
        elif bk_app_code == env.APP_CODE and bk_app_secret == env.SECRET_KEY:
            authorize_admin_user()
            return None
        elif request.is_bk_jwt():
            authorize_valid_user()
        # TODO: 考虑特殊平台开发admin账号，比如通过X-Bkapi-JWT查看app_code是否为特殊加白(eg: 作业平台，bcs等)

        return super().process_view(request, view, args, kwargs)
