# -*- coding: utf-8 -*-
from urllib.parse import urlparse

from apigw_manager.apigw.authentication import ApiGatewayJWTGenericMiddleware
from apigw_manager.apigw.providers import JWTTokenInvalid
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser

from backend import env


class _WebSocketJWTRequest(object):
    def __init__(self, scope):
        self.scope = scope
        self.user = scope.get("user") or AnonymousUser()
        self.META = self._get_meta(scope)

    @staticmethod
    def _get_meta(scope):
        return {
            "HTTP_{}".format(name.decode("latin1").upper().replace("-", "_")): value.decode("latin1")
            for name, value in scope.get("headers", [])
        }

    def is_bk_jwt(self):
        return bool(getattr(self, "jwt", None))


class ApiGatewayJWTAuthMiddleware(object):
    """使用与 HTTP 中间件一致的 APIGW JWT 协议认证 WebSocket 握手。"""

    JWT_KEY_NAME = "HTTP_X_BKAPI_JWT"
    ALGORITHM = "RS512"

    def __init__(self, inner):
        self.inner = inner
        self.provider = ApiGatewayJWTGenericMiddleware(lambda request: None).provider

    async def __call__(self, scope, receive, send):
        request = _WebSocketJWTRequest(scope)
        try:
            jwt = self.provider.provide(request)
        except JWTTokenInvalid:
            await send({"type": "websocket.close", "code": 4401})
            return

        scope["bkapi_jwt_verified"] = bool(jwt)
        if jwt and not request.user.is_authenticated:
            request.jwt = jwt
            jwt_user = (jwt.payload.get("user") or {}).copy()
            jwt_user.setdefault("bk_username", jwt_user.pop("username", None))
            scope["user"] = await database_sync_to_async(auth.authenticate)(
                request,
                gateway_name=jwt.gateway_name,
                **jwt_user,
            )

        return await self.inner(scope, receive, send)


def _get_header(scope, header_name):
    header_name = header_name.lower().encode("latin1")
    for name, value in scope.get("headers", []):
        if name.lower() == header_name:
            return value.decode("latin1")
    return ""


def _get_origin(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        return ""
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def _iter_channels_origin_patterns(origin):
    yield origin
    parsed_origin = urlparse(origin)
    if parsed_origin.hostname and parsed_origin.hostname.startswith("*."):
        netloc = parsed_origin.netloc.replace("*.", ".", 1)
        yield f"{parsed_origin.scheme}://{netloc}"


def get_ws_allowed_origins():
    origins = []
    configured_origins = getattr(settings, "WS_ALLOWED_ORIGINS", None)
    if configured_origins is None:
        configured_origins = getattr(settings, "CSRF_TRUSTED_ORIGINS", [])

    for origin in configured_origins or []:
        for pattern in _iter_channels_origin_patterns(origin):
            if pattern and pattern not in origins:
                origins.append(pattern)

    saas_origin = _get_origin(env.BK_SAAS_HOST)
    if saas_origin and saas_origin not in origins:
        origins.append(saas_origin)
    return origins


class DBMWebSocketOriginValidator(object):
    """校验 WebSocket Origin，并兼容无 Origin 的 APIGW/JWT 调用。"""

    def __init__(self, inner, allowed_origins):
        self.inner = inner
        self.origin_validator = OriginValidator(inner, allowed_origins)

    async def __call__(self, scope, receive, send):
        origin = _get_header(scope, "origin")
        if scope.get("bkapi_jwt_verified") and not origin:
            return await self.inner(scope, receive, send)
        if origin:
            try:
                # 在 Channels 匹配来源前，读取 port 属性以校验端口格式和范围。
                parsed_origin = urlparse(origin)
                _ = parsed_origin.port
            except ValueError:
                await send({"type": "websocket.close"})
                return
        return await self.origin_validator(scope, receive, send)


def DBMWebSocketAuthMiddleware(inner):
    # AuthMiddlewareStack 等价于 CookieMiddleware + SessionMiddleware + AuthMiddleware。
    # SessionMiddleware 会读取 settings.SESSION_COOKIE_NAME，因此 WS 握手复用 dbm_sessionid。
    return AuthMiddlewareStack(
        ApiGatewayJWTAuthMiddleware(DBMWebSocketOriginValidator(inner, get_ws_allowed_origins()))
    )
