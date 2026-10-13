# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import ssl
import time
import uuid
from typing import Any, Dict
from urllib import parse

import websockets
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import translation

from backend import env
from backend.components.base import DataAPI
from backend.components.exception import DataAPIException
from backend.components.utils.handlers import get_virtual_username
from backend.db_proxy.models import DBCloudProxy

logger = logging.getLogger("root")


class _HeaderSession(object):
    """用于复用通用请求头组装逻辑的轻量 session 对象。"""

    def __init__(self):
        self.headers = {}


def _to_ws_url(url: str) -> str:
    parsed = parse.urlsplit(url)
    if parsed.scheme == "https":
        scheme = "wss"
    elif parsed.scheme == "http":
        scheme = "ws"
    elif parsed.scheme in ["ws", "wss"]:
        scheme = parsed.scheme
    else:
        raise DataAPIException(f"unsupported websocket url scheme: {parsed.scheme}")
    return parse.urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))


def _is_secure_url(url: str) -> bool:
    return parse.urlsplit(url).scheme.lower() in ["https", "wss"]


class WebSocketSession(object):
    def __init__(
        self,
        api,
        params: Dict[str, Any],
        headers: Dict[str, str],
        use_admin: bool,
        use_param_user: bool,
        local_request=None,
    ):
        self.api = api
        self.params = params
        self.headers = headers
        self.use_admin = use_admin
        self.use_param_user = use_param_user
        self.local_request = local_request
        self.websocket = None
        self.url = ""
        self.request_id = ""

    async def __aenter__(self):
        self.websocket = await self._connect_with_retry()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await self.websocket.send(json.dumps(payload))
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=self.api.default_timeout)
        except asyncio.TimeoutError as error:
            await self.close()
            raise DataAPIException(
                f"{self.api.module}-websocket request timeout after {self.api.default_timeout}s"
            ) from error
        if isinstance(response, bytes):
            response = response.decode("utf-8")
        return json.loads(response)

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def _connect_with_retry(self):
        last_error = None
        for current_retry_times in range(self.api.max_retry_times):
            start_time = time.time()
            try:
                websocket = await self._connect_once()
                self.api.log_request(
                    params=self.params,
                    headers=self.headers,
                    start_time=start_time,
                    response_result=True,
                    response_code="00",
                    response_data="",
                    response_message="websocket connected",
                    response_errors="",
                    request_id=self.request_id,
                    url=self.url,
                )
                return websocket
            except Exception as error:  # pylint: disable=broad-except
                last_error = error
                self.api.log_request(
                    params=self.params,
                    headers=self.headers,
                    start_time=start_time,
                    response_result=False,
                    response_code=-1,
                    response_data="",
                    response_message=str(error),
                    response_errors="",
                    request_id=self.request_id,
                    url=self.url,
                )
                if current_retry_times + 1 >= self.api.max_retry_times:
                    break
                await asyncio.sleep(0.2 * (current_retry_times + 1))
        raise DataAPIException(f"{self.api.module}-websocket connect failed: {last_error}")

    async def _connect_once(self):
        session = _HeaderSession()
        self.request_id = uuid.uuid4().hex
        self.api._set_ws_session_headers(  # pylint: disable=protected-access
            session,
            self.local_request,
            self.headers,
            self.params,
            use_admin=self.use_admin,
            use_param_user=self.use_param_user,
            request_id=self.request_id,
        )
        headers = dict(session.headers)
        actual_url = await sync_to_async(self.api.build_actual_url, thread_sensitive=True)(self.params)
        self.url = _to_ws_url(actual_url)

        ssl_context = None
        if _is_secure_url(self.url):
            ssl_context = await self.api.build_ssl_context(self.params)

        return await websockets.connect(self.url, additional_headers=headers, ssl=ssl_context)


class WebSocketAPI(DataAPI):
    def __call__(self, *args, **kwargs):
        raise TypeError("WebSocketAPI does not support __call__; use connect(...) instead")

    def connect(
        self,
        params=None,
        headers=None,
        use_admin=False,
        use_param_user=False,
        local_request=None,
        **kwargs,
    ):
        params = dict(params or {})
        params.update(kwargs)
        return WebSocketSession(
            self,
            params,
            headers or {},
            use_admin=use_admin,
            use_param_user=use_param_user,
            local_request=local_request,
        )

    def use_client_cert(self, params):
        return self.ssl

    async def build_ssl_context(self, params):
        """构造内部服务连接的 TLS 上下文，证书本地化仍在线程中执行。"""
        context = ssl._create_unverified_context()  # noqa: S323
        if self.use_client_cert(params):
            client_crt, client_key = await sync_to_async(self._fetch_client_crt, thread_sensitive=True)()
            context.load_cert_chain(client_crt, client_key)
        return context

    def _set_ws_session_headers(
        self,
        session,
        local_request,
        headers: Dict,
        params: Dict,
        use_admin: bool = False,
        use_param_user: bool = False,
        request_id: str = "",
    ):
        session.headers.update(headers)
        session.headers.update(
            {
                "X-Bkapi-Request-Id": request_id,
                "blueking-language": translation.get_language(),
                "X-Bk-Tenant-Id": env.BK_TENANT_ID,
            }
        )

        if isinstance(params, dict):
            bkapi_auth_headers = {
                "bk_app_code": params.get("bk_app_code", env.APP_CODE),
                "bk_app_secret": params.get("bk_app_secret", env.SECRET_KEY),
                "bk_username": params.get("bk_username", "Anonymous"),
            }
        else:
            bkapi_auth_headers = {
                "bk_app_code": env.APP_CODE,
                "bk_app_secret": env.SECRET_KEY,
                "bk_username": "Anonymous",
            }

        if use_admin:
            bkapi_auth_headers["bk_username"] = get_virtual_username()
        elif self.is_backend_request(local_request) and not use_param_user:
            bkapi_auth_headers["bk_username"] = get_virtual_username()
        elif local_request and local_request.COOKIES:
            bkapi_auth_headers["bk_username"] = local_request.user.username
            oath_cookies_params = getattr(settings, "OAUTH_COOKIES_PARAMS", {"bk_token": "bk_token"})
            for key, value in oath_cookies_params.items():
                if value in local_request.COOKIES:
                    bkapi_auth_headers.update({key: local_request.COOKIES[value]})
        session.headers.update({"X-Bkapi-Authorization": json.dumps(bkapi_auth_headers)})

        if self.method_override is not None:
            session.headers.update({"X-METHOD-OVERRIDE": self.method_override})

    def log_request(
        self,
        params,
        headers,
        start_time,
        response_result,
        response_code,
        response_data,
        response_message,
        response_errors,
        request_id=None,
        url=None,
    ):
        end_time = time.time()
        log_params = params if isinstance(params, dict) else {"params_data": params}
        bk_username = log_params.get("bk_username", "")
        _info = {
            "request_datetime": start_time,
            "url": url or self.url,
            "module": self.module,
            "method": "WEBSOCKET",
            "method_override": self.method_override,
            "headers": headers,
            "query_params": json.dumps(log_params)[: self.max_query_params_record],
            "response_result": response_result,
            "response_code": response_code,
            "response_data": response_data,
            "response_message": str(response_message)[:1023],
            "response_errors": response_errors,
            "cost_time": end_time - start_time,
            "request_id": request_id,
            "request_user": bk_username,
        }
        _log = "[BKAPI] {}".format(" && ".join([" {}=>{} ".format(k, v) for k, v in list(_info.items())]))
        if response_result:
            logger.debug(_log)
        else:
            logger.exception(_log)


class ProxyWSAPI(WebSocketAPI):
    def build_actual_url(self, param):
        url = super().build_actual_url(param)

        if env.DOMAIN_SKIP_PROXY:
            return _to_ws_url(url)

        try:
            bk_cloud_id = param["bk_cloud_id"]
        except KeyError:
            raise DataAPIException("ProxyWSAPI must receive bk_cloud_id param")

        if env.CLOUD_CONTAINER_ENABLE and bk_cloud_id == 0:
            return _to_ws_url(url)

        proxy_url = DBCloudProxy.get_cloud_proxy_external_address(bk_cloud_id)
        host = "https://" if _is_secure_url(self.base) else "http://"
        external_address = f"{host}{proxy_url}"
        proxy_http_url = url.replace(self.base.rstrip("/"), external_address)
        return _to_ws_url(proxy_http_url)

    def use_client_cert(self, params):
        if env.CLOUD_CONTAINER_ENABLE and params.get("bk_cloud_id") == 0:
            return False
        return self.ssl

    def _set_session_headers(self, session, local_request, headers, params, use_admin: bool = False):
        super()._set_session_headers(session, local_request, headers, params, use_admin)
        if local_request:
            session.headers.update({"X-Forwarded-For": local_request.META.get("HTTP_X_FORWARDED_FOR", "")})
            session.headers.update({"X-Real-IP": local_request.META.get("REMOTE_ADDR", "")})

    def _set_ws_session_headers(
        self,
        session,
        local_request,
        headers,
        params,
        use_admin: bool = False,
        use_param_user: bool = False,
        request_id: str = "",
    ):
        super()._set_ws_session_headers(
            session,
            local_request,
            headers,
            params,
            use_admin=use_admin,
            use_param_user=use_param_user,
            request_id=request_id,
        )
        if local_request:
            session.headers.update({"X-Forwarded-For": local_request.META.get("HTTP_X_FORWARDED_FOR", "")})
            session.headers.update({"X-Real-IP": local_request.META.get("REMOTE_ADDR", "")})
