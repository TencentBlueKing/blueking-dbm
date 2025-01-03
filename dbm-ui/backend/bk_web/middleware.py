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
import re

import wrapt
from apigw_manager.apigw.authentication import UserModelBackend
from blueapps.account.middlewares import LoginRequiredMiddleware
from blueapps.account.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext as _

from backend import env
from backend.bk_web.constants import (
    EXTERNAL_TICKET_TYPE_WHITELIST,
    NON_EXTERNAL_PROXY_ROUTING,
    ROUTING_WHITELIST_PATTERNS,
)
from backend.bk_web.exceptions import ExternalProxyBaseException, ExternalRouteInvalidException
from backend.bk_web.handlers import _error
from backend.components import BKBaseApi
from backend.ticket.views import TicketViewSet
from backend.utils.local import local
from backend.utils.string import str2bool

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


class ExternalProxyMiddleware(MiddlewareMixin):
    """
    外部代理的中间件，主要功能：
    - 路由前缀添加external，使其转发到external_proxy接口
    - 外部用户和内部用户的映射
    - 相关header的转换
    """

    routing_patterns: list = ROUTING_WHITELIST_PATTERNS
    non_proxy_routing: list = NON_EXTERNAL_PROXY_ROUTING

    def __init__(self, get_response=None):
        self.get_response = get_response
        # 获取所有视图
        # 预编译正则匹配，复用匹配模式
        self.complied_routing_patterns = [re.compile(pattern) for pattern in self.routing_patterns]
        super().__init__(get_response)

    @staticmethod
    def error_handler(return_response=True):
        @wrapt.decorator
        def wrapper(wrapped, instance=None, args=None, kwargs=None):
            try:
                return wrapped(*args, **kwargs)
            except ExternalProxyBaseException as exc:
                if return_response:
                    error_msg = _("外部请求失败，错误原因:{}").format(exc.message)
                    return JsonResponse(_error(exc.code, error_msg, exc.data, exc.errors))
                raise exc

        return wrapper

    def __check_action_permission_is_none(self, request):
        """校验当前动作的权限类是否为空，默认为空允许转发"""
        try:
            func = resolve(request.path).func
            action = func.actions.get(request.method.lower())
        except Exception as e:
            logger.error("resolve request error: %s", e)
            return False

        permission_class_with_action = getattr(func.cls(), "get_permission_class_with_action", None)
        if permission_class_with_action and permission_class_with_action(action):
            return False

        # 缓存到路由白名单中，不用下次校验。TODO: 缓存的数量级会过大吗？
        self.routing_patterns.append(request.path)
        return True

    def __check_specific_request_params(self, request):
        """校验特殊接口的参数是否满足要求"""

        # 单据创建校验函数
        def check_create_ticket():
            data = json.loads(request.body.decode("utf-8"))
            # 目前只放开数据导出
            if data["ticket_type"] not in EXTERNAL_TICKET_TYPE_WHITELIST:
                raise ExternalRouteInvalidException(_("单据类型[{}]非法，未开通白名单").format(data["ticket_type"]))

        # 单据过滤校验函数
        def check_list_ticket():
            data = request.GET.copy()
            # 强制加上单据白名单类型
            data["ticket_type__in"] = ",".join(EXTERNAL_TICKET_TYPE_WHITELIST)
            request.GET = data

        check_action_func_map = {
            f"{TicketViewSet.__name__}.{TicketViewSet.create.__name__}": check_create_ticket,
            f"{TicketViewSet.__name__}.{TicketViewSet.list.__name__}": check_list_ticket,
        }
        # 根据请求的视图 + 动作判断是否特殊接口，以及接口参数是否合法
        try:
            func = resolve(request.path).func
            action = func.actions.get(request.method.lower())
            check_action_func_map.get(f"{func.cls.__name__}.{action}", lambda: None)()
        except AttributeError:
            # 对无法解析func或者func action的接口忽略，不在特殊接口参数校验范围
            pass

    def __verify_request_url(self, request):
        """校验外部请求路由是否允许被转发"""
        # 外部请求路由属于转发白名单，则校验通过
        if request.path in self.routing_patterns:
            return
        for url_pattern in self.complied_routing_patterns:
            if url_pattern.match(request.path):
                return
        # 外部请求路由无需鉴权，则校验通过
        if self.__check_action_permission_is_none(request):
            return
        # 非白名单路由，禁止转发
        raise ExternalRouteInvalidException(_("路由{}非法，未开通白名单").format(request.path))

    def __check_non_proxy_routing(self, request):
        """校验本地路由，请求这些接口不用做用户转发和路由映射"""
        # 静态非转发路由白名单
        if request.path in self.non_proxy_routing:
            return True
        func_path_splits = resolve(request.path)._func_path.split(".")
        # home请求和版本请求非转发
        if func_path_splits[1] in ["homepage", "version_log", "contrib"]:
            return True
        return False

    def __parser_request_url(self, request):
        """外部转发接口进行路由映射"""
        if self.__check_non_proxy_routing(request):
            return
        if env.ENABLE_EXTERNAL_PROXY:
            self.__verify_request_url(request)
            self.__check_specific_request_params(request)
        request.path = f"/external/{request.path.lstrip('/')}"
        request.path_info = request.path
        setattr(request, "_dont_enforce_csrf_checks", True)

    @error_handler(return_response=True)
    def __call__(self, request):
        # 外部路由转发仅提供给外部环境使用
        if env.ENABLE_EXTERNAL_PROXY or env.ENABLE_OPEN_EXTERNAL_PROXY:
            self.__parser_request_url(request)
        else:
            # 解析来自外部转发的header
            request.is_external = str2bool(request.headers.get("IS-EXTERNAL", ""), strict=False)
        response = self.get_response(request)

        # 如果是来自外部转发的请求，进行脱敏
        if getattr(request, "is_external", False) and "webconsole" in request.path and env.BKDATA_DATA_TOKEN:
            data = BKBaseApi.data_desensitization(response.content.decode("utf-8"))
            return JsonResponse(json.loads(data))

        return response


class JWTUserModelBackend(UserModelBackend):
    """dbm jwt用户认证后端"""

    def __init__(self):
        super().__init__()
        self.user_maker = self.jwt_user_maker

    @staticmethod
    def jwt_user_maker(username):
        user_model = get_user_model()
        if hasattr(user_model.objects, "get_by_natural_key"):
            _user_maker = user_model.objects.get_by_natural_key  # type: ignore
        else:
            _user_maker = lambda x: user_model.objects.get(username=x)  # noqa: E731

        # 如果找不到用户，则自动注册用户
        try:
            user = _user_maker(username)
        except User.DoesNotExist:
            user = user_model.objects.create(username=username)

        return user

    def authenticate(self, request, api_name, bk_username, verified, **credentials):
        super().authenticate(request, api_name, bk_username, verified, **credentials)
