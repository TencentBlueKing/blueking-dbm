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
from abc import ABC, abstractmethod

import wrapt
from apigw_manager.apigw.authentication import UserModelBackend
from blueapps.account.middlewares import LoginRequiredMiddleware
from blueapps.account.models import User
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext as _

from backend import env
from backend.bk_web.constants import (
    EXTERNAL_TICKET_TYPE_WHITELIST,
    NON_EXTERNAL_PROXY_ROUTING,
    ROUTING_WHITELIST_PATTERNS,
)
from backend.bk_web.exceptions import ExternalProxyBaseException, ExternalRouteInvalidException
from backend.bk_web.handlers import _error
from backend.bk_web.tenant import TENANT_ID_HEADER, resolve_tenant_id
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
        # 设置 request_id
        local.request = request
        request.request_id = local.get_http_request_id()

        response = self.get_response(request)
        response["X-Request-Id"] = request.request_id

        local.release()
        return response

    def process_view(self, request, view, args, kwargs):
        # 注入租户ID（多租户环境下按 header/user 解析，否则回退部署环境变量 BK_TENANT_ID）
        if env.ENABLE_MULTI_TENANT_MODE:
            request.tenant_id = local.inject_tenant_id()


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
            """管理员用户认证，只允许内部服务调用"""
            request.user = User(username=env.DEFAULT_USERNAME, is_superuser=True, tenant_id=env.BK_TENANT_ID)
            request.internal_call = True
            setattr(request, "_dont_enforce_csrf_checks", True)

        def authorize_jwt_user():
            """apigw 网关jwt用户认证"""
            app_code = request.jwt.payload.get("app", {}).get("app_code", None)
            # apigw 向前兼容，从请求头中拿 header X-Bk-Username，如果为空，则从jwt中拿
            username = request.headers.get("X-Bk-Username", None)
            username = username or request.jwt.payload.get("user", {}).get("username", None)
            logger.info(f"jwt decode is: username: {username}, app_code: {app_code}")
            try:
                request.user = User.objects.get(username=username) if username else AnonymousUser()
            except Exception:  # pylint: disable=broad-except
                request.user = User(username=username, tenant_id=env.BK_TENANT_ID) if username else AnonymousUser()
            setattr(request, "_dont_enforce_csrf_checks", True)

        bk_app_code = request.COOKIES.get("bk_app_code")
        bk_app_secret = request.COOKIES.get("bk_app_secret")

        if request.user and request.user.is_authenticated:
            return super().process_view(request, view, args, kwargs)
        elif bk_app_code == env.APP_CODE and bk_app_secret == env.SECRET_KEY:
            authorize_admin_user()
            return None
        elif request.is_bk_jwt():
            authorize_jwt_user()
        # TODO: 考虑特殊平台开发admin账号，比如通过X-Bkapi-JWT查看app_code是否为特殊加白(eg: 作业平台，bcs等)

        return super().process_view(request, view, args, kwargs)


class BaseForwardProxyMiddleware(MiddlewareMixin, ABC):
    """
    代理中间件基类
    提供通用的路由检查和URL重写逻辑
    """

    # 代理路由前缀，如 "external" 或 "tenant"
    PROXY_PREFIX: str = ""
    # 不需要代理的路由
    non_proxy_routing: list = []
    # 系统路由模块
    SYSTEM_MODULES = ["homepage", "version_log", "contrib"]

    def __init__(self, get_response=None):
        self.get_response = get_response
        super().__init__(get_response)
        self._init_proxy()

    def _init_proxy(self):
        """子类可以覆盖的初始化方法"""
        pass

    @abstractmethod
    def should_enable_proxy(self, request) -> bool:
        """判断是否启用代理"""
        raise NotImplementedError

    @abstractmethod
    def before_url_rewrite(self, request):
        """URL重写前的钩子"""
        raise NotImplementedError

    @abstractmethod
    def handle_proxy_disabled(self, request):
        """代理未启用时的处理逻辑"""
        raise NotImplementedError

    def _check_static_resources(self, request) -> bool:
        """检查是否为静态资源"""
        return request.path.startswith("/static/") or request.path.startswith("/media/")

    def _check_system_modules(self, request) -> bool:
        """检查是否为系统模块路由"""
        try:
            func_path_splits = resolve(request.path)._func_path.split(".")
            return func_path_splits[1] in self.SYSTEM_MODULES
        except Exception:
            return False

    def _check_whitelist(self, request) -> bool:
        """检查是否在白名单中"""
        if request.path in self.non_proxy_routing:
            return True
        return False

    def _check_non_proxy_routing(self, request) -> bool:
        """检查是否需要跳过代理"""
        # 1. 静态资源检查
        if self._check_static_resources(request):
            return True
        # 2. 系统模块检查
        if self._check_system_modules(request):
            return True
        # 3. 白名单检查
        if self._check_whitelist(request):
            return True
        return False

    def _rewrite_request_url(self, request):
        """重写请求URL"""
        # 检查是否需要跳过代理
        if self._check_non_proxy_routing(request):
            return
        # URL重写前的钩子
        self.before_url_rewrite(request)
        # 执行URL重写
        request.path = f"/{self.PROXY_PREFIX}/{request.path.lstrip('/')}"
        request.path_info = request.path
        # 禁用CSRF检查
        setattr(request, "_dont_enforce_csrf_checks", True)

    def __call__(self, request):
        """中间件主入口"""
        if self.should_enable_proxy(request):
            self._rewrite_request_url(request)
        else:
            self.handle_proxy_disabled(request)

        response = self.get_response(request)
        return response


class ExternalProxyMiddleware(BaseForwardProxyMiddleware):
    """
    外部代理中间件
    - 路由前缀添加external，使其转发到external_proxy接口
    - 外部用户和内部用户的映射
    - 相关header的转换
    """

    PROXY_PREFIX = "external"
    routing_patterns: list = ROUTING_WHITELIST_PATTERNS
    non_proxy_routing: list = NON_EXTERNAL_PROXY_ROUTING

    def _init_proxy(self):
        """初始化正则匹配模式"""
        self.complied_routing_patterns = [re.compile(pattern) for pattern in self.routing_patterns]

    def should_enable_proxy(self, request) -> bool:
        return env.ENABLE_EXTERNAL_PROXY or env.ENABLE_OPEN_EXTERNAL_PROXY

    def before_url_rewrite(self, request):
        # 外部请求路由增加额外校验
        if env.ENABLE_EXTERNAL_PROXY:
            self.__verify_request_url(request)
            self.__check_specific_request_params(request)

    def handle_proxy_disabled(self, request):
        # 解析来自外部转发的header
        request.is_external = str2bool(request.headers.get("IS-EXTERNAL", ""), strict=False)

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

    @error_handler(return_response=True)
    def __call__(self, request):
        """使用error_handler装饰的调用"""
        return super().__call__(request)


class MultiTenantProxyMiddleware(BaseForwardProxyMiddleware):
    """
    多租户代理中间件
    - 检查是否启用多租户模式
    - 路由映射：将请求路径映射到 /tenant/{path}
    - 传递租户ID信息
    TODO: 暂不启用，改用nginx转发模式
    """

    PROXY_PREFIX = "tenant"
    non_proxy_routing: list = []

    def should_enable_proxy(self, request) -> bool:
        return env.ENABLE_MULTI_TENANT_MODE

    def before_url_rewrite(self, request):
        return

    def handle_proxy_disabled(self, request):
        return


class TenantCookieMiddleware(MiddlewareMixin):
    """
    租户 Cookie 中间件（多租户环境 ENABLE_MULTI_TENANT_MODE 生效）。

    登录后解析用户租户ID写入 dbm_tenant_id cookie（父域），供接入层 tenant-router 路由。
    权威以 user.tenant_id 为准（tenant-router 会回填 X-Bk-Tenant-Id，故 header 不能用作权威）。

    - process_view：落到非用户归属实例时拦截（302/409），视图不执行；
    - process_response：在归属实例上补种/覆盖 dbm_tenant_id cookie。
    """

    TENANT_COOKIE_NAME = "dbm_tenant_id"

    def _set_tenant_cookie(self, response, tenant_id):
        response.set_cookie(
            self.TENANT_COOKIE_NAME,
            tenant_id,
            domain=settings.SESSION_COOKIE_DOMAIN or None,
            httponly=True,
            samesite="Lax",
        )

    def _resolve_tenant_context(self, request):
        """返回 (tenant_id, cookie_matched)；无法处理时 tenant_id 为 None。"""
        if not env.ENABLE_MULTI_TENANT_MODE:
            return None, False

        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return None, False

        tenant_id = getattr(user, "tenant_id", "") or resolve_tenant_id(request)
        if not tenant_id:
            return None, False

        cookie_matched = request.COOKIES.get(self.TENANT_COOKIE_NAME) == tenant_id
        return tenant_id, cookie_matched

    def process_view(self, request, view, args, kwargs):
        tenant_id, cookie_matched = self._resolve_tenant_context(request)
        if not tenant_id:
            return None

        # request租户和当前实例租户一致，放行process_view
        if tenant_id == env.BK_TENANT_ID:
            return None

        # 租户不一致，且 cookie 尚未带对：种正确 cookie 并纠正路由。
        # 浏览器跟随 302/带新 cookie 重试时不会重发自定义 header，tenant-router 将按 cookie 转到正确实例。
        if not cookie_matched:
            if request.method in ("GET", "HEAD"):
                redirect = HttpResponseRedirect(request.get_full_path())
                self._set_tenant_cookie(redirect, tenant_id)
                return redirect
            retry = JsonResponse(
                {"result": False, "code": "TenantRouteRetry", "data": None, "message": _("租户路由未就绪，请重试")},
                status=409,
            )
            self._set_tenant_cookie(retry, tenant_id)
            return retry

        # cookie 已是用户归属租户，却仍落到错误实例。可能原因：
        #   1) 请求带了与用户归属租户冲突的 X-Bk-Tenant-Id header，tenant-router 按 header 强制路由（越权企图）；
        #   2) tenant-router 缺少该租户到 namespace 的映射（配置缺失）。
        # 两种情况都不能在错误实例上服务用户数据（会读写到其它租户），且不再重定向以避免死循环，直接报错。
        logger.error(
            "tenant route conflict: user tenant=%s but served by instance tenant=%s, "
            "header X-Bk-Tenant-Id=%s; check conflicting header or tenant-router tenants mapping",
            tenant_id,
            env.BK_TENANT_ID,
            request.headers.get(TENANT_ID_HEADER, ""),
        )
        return JsonResponse(
            {"result": False, "code": "TenantRouteConflict", "data": None, "message": _("用户租户错误或不存在")},
            status=409,
        )

    def process_response(self, request, response):
        tenant_id, cookie_matched = self._resolve_tenant_context(request)
        if not tenant_id or tenant_id != env.BK_TENANT_ID:
            return response

        # 当前实例即用户归属租户：cookie 缺失或不一致则种植/覆盖
        if not cookie_matched:
            self._set_tenant_cookie(response, tenant_id)
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
