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
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.decorators import action
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from backend import env
from backend.version_log.utils import get_latest_version


class HomeView(APIView):
    template_name = "index.html"
    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = ()

    @xframe_options_exempt
    @method_decorator(login_required(redirect_field_name="c_url"))
    def get(self, request):
        context = {"SITE_URL": settings.SITE_URL[:-1]}
        return Response(context)

    @action(methods=["GET"], detail=False)
    def version(self, request):
        return Response({"app_version": get_latest_version()})


class VersionView(APIView):
    def get(self, request):
        return Response(
            {"version": get_latest_version(), "app_version": env.APP_VERSION, "chart_version": env.CHART_VERSION}
        )


class LoginSuccessView(APIView):
    template_name = "login_success.html"
    renderer_classes = [TemplateHTMLRenderer]
    permission_classes = ()

    @xframe_options_exempt
    @method_decorator(login_required(redirect_field_name="c_url"))
    def get(self, request):
        context = {"SESSION_COOKIE_DOMAIN": settings.SESSION_COOKIE_DOMAIN.lstrip(".")}
        return Response(context)


class LogOutView(APIView):
    def get(self, request):
        auth.logout(request)
        response = Response("User Logged out successfully")
        cookie_keys = ["bk_ticket", "bk_token", "bk_uid"]
        host = "".join(request.headers["Host"].split(":")[:1])
        domain = f'.{".".join(host.split(".")[1:])}'
        for _domain in [host, domain]:
            for key in cookie_keys:
                response.delete_cookie(key, domain=_domain)
        return response
