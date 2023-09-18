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
from blueapps.account.middlewares import LoginRequiredMiddleware
from blueapps.account.models import User

from backend import env
from backend.utils.local import local


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
        # 如果传入了bk_app_code和bk_app_secret，则认为是内部调用，鉴权通过
        bk_app_code = request.COOKIES.get("bk_app_code")
        bk_app_secret = request.COOKIES.get("bk_app_secret")
        if bk_app_code == env.APP_CODE and bk_app_secret == env.SECRET_KEY:
            # 为request授权一个超级用户，并标记为内部调用
            request.user = User(username="admin", is_superuser=True)
            request.internal_call = True
            # 超级用户跳过csrf认证
            setattr(request, "_dont_enforce_csrf_checks", True)

            return None

        return super().process_view(request, view, args, kwargs)
