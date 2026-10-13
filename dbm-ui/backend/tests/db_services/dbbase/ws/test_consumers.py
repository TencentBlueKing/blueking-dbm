# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from apigw_manager.apigw.providers import JWTTokenInvalid
from asgiref.sync import async_to_sync
from django.test import override_settings

from backend import env
from backend.components.ws_api import ProxyWSAPI
from backend.db_services.dbbase.ws.consumers import WebConsoleConsumer, _WebSocketRequest
from backend.db_services.dbbase.ws.middleware import (
    ApiGatewayJWTAuthMiddleware,
    DBMWebSocketOriginValidator,
    get_ws_allowed_origins,
)
from backend.iam_app.exceptions import PermissionDeniedError


class _User:
    username = "alice"
    is_authenticated = True


def test_websocket_request_uses_external_proxy_env_for_external_flag():
    scope = {
        "user": _User(),
        "client": ("client-remote-addr", 12345),
        "headers": [
            (b"cookie", b"dbm_sessionid=session-value; bk_token=token-value"),
            (b"is-external", b"true"),
            (b"x-forwarded-for", b"client-forwarded-for"),
        ],
    }

    with patch.object(env, "ENABLE_EXTERNAL_PROXY", True), patch.object(env, "ENABLE_OPEN_EXTERNAL_PROXY", False):
        request = _WebSocketRequest(scope)

    assert request.user.username == "alice"
    assert request.COOKIES["dbm_sessionid"] == "session-value"
    assert request.COOKIES["bk_token"] == "token-value"
    assert request.META["HTTP_X_FORWARDED_FOR"] == "client-forwarded-for"
    assert request.is_external is True


def test_websocket_request_does_not_trust_external_header_when_proxy_disabled():
    scope = {
        "user": _User(),
        "client": ("client-remote-addr", 12345),
        "headers": [(b"is-external", b"true")],
    }

    with patch.object(env, "ENABLE_EXTERNAL_PROXY", False), patch.object(env, "ENABLE_OPEN_EXTERNAL_PROXY", False):
        request = _WebSocketRequest(scope)

    assert request.is_external is False
    assert "IS_EXTERNAL" not in request.META


def test_consumer_sends_readable_error_before_iam_close():
    consumer = WebConsoleConsumer()
    consumer.scope = {"user": _User()}
    consumer.drs_session = None
    consumer.send_json = AsyncMock()
    consumer.close = AsyncMock()

    with patch.object(consumer, "_connect_drs", side_effect=PermissionDeniedError("forbidden", {}, "")):
        async_to_sync(consumer.receive_json)({"request-type": "CONNECT", "cluster_id": 1})

    consumer.send_json.assert_awaited_once()
    assert consumer.send_json.await_args.args[0]["result"] is False
    assert consumer.send_json.await_args.args[0]["code"] == 4403
    assert "forbidden" in consumer.send_json.await_args.args[0]["error"]
    consumer.close.assert_awaited_once_with(code=4403)


def test_consumer_rejects_repeated_connect_after_drs_connected():
    consumer = WebConsoleConsumer()
    consumer.scope = {"user": _User()}
    consumer.drs_session = AsyncMock()
    consumer.send_json = AsyncMock()
    consumer.close = AsyncMock()

    async_to_sync(consumer.receive_json)({"request-type": "CONNECT", "body": {"address": "1.1.1.1:20000"}})

    consumer.drs_session.request.assert_not_awaited()
    consumer.send_json.assert_awaited_once()
    assert consumer.send_json.await_args.args[0]["result"] is False
    assert "unsupported request type" in consumer.send_json.await_args.args[0]["error"]
    consumer.close.assert_awaited_once_with(code=4400)


def test_consumer_normalizes_request_type_before_drs_forwarding():
    consumer = WebConsoleConsumer()
    consumer.scope = {"user": _User()}
    consumer.drs_session = AsyncMock()
    consumer.drs_session.request = AsyncMock(return_value={"result": True})
    consumer.local_request = SimpleNamespace(is_external=False)
    consumer.send_json = AsyncMock()
    consumer.close = AsyncMock()

    with patch.object(consumer, "_validate_command") as validate_command:
        async_to_sync(consumer.receive_json)({"request_type": "command", "body": {"command": "select 1"}})

    forwarded_content = consumer.drs_session.request.await_args.args[0]
    assert forwarded_content["request-type"] == "COMMAND"
    assert "request_type" not in forwarded_content
    validate_command.assert_called_once_with(forwarded_content)
    consumer.send_json.assert_awaited_once_with({"result": True})
    consumer.close.assert_not_awaited()


def test_ws_api_uses_local_request_user_and_cookies_in_auth_header():
    api = ProxyWSAPI(method="GET", base="https://drs.example.com", url="v2/webconsole/ws", module="DB", ssl=False)
    api.request_id = "request-id"
    api.use_param_user = False
    session = Mock(headers={})
    request = SimpleNamespace(
        user=SimpleNamespace(username="alice"),
        COOKIES={"bk_token": "token-value"},
        META={"HTTP_X_FORWARDED_FOR": "client-forwarded-for", "REMOTE_ADDR": "client-remote-addr"},
    )

    api._set_session_headers(session, request, {}, {"bk_username": "alice"}, use_admin=False)

    assert '"bk_username": "alice"' in session.headers["X-Bkapi-Authorization"]
    assert '"bk_token": "token-value"' in session.headers["X-Bkapi-Authorization"]
    assert "Anonymous" not in session.headers["X-Bkapi-Authorization"]


def test_apigw_jwt_middleware_sets_scope_user():
    async def inner(scope, receive, send):
        return scope["user"]

    middleware = ApiGatewayJWTAuthMiddleware.__new__(ApiGatewayJWTAuthMiddleware)
    middleware.inner = inner
    middleware.provider = Mock(
        provide=Mock(
            return_value=SimpleNamespace(
                gateway_name="bkdbm",
                payload={"user": {"username": "alice", "verified": True}},
            )
        )
    )
    scope = {"headers": [(b"x-bkapi-jwt", b"jwt-token")], "user": SimpleNamespace(is_authenticated=False)}

    with patch(
        "backend.db_services.dbbase.ws.middleware.auth.authenticate", return_value=_User()
    ) as authenticate_mock:
        user = async_to_sync(middleware)(scope, AsyncMock(), AsyncMock())

    assert user.username == "alice"
    assert scope["user"].username == "alice"
    authenticate_mock.assert_called_once()


def test_ws_allowed_origins_uses_csrf_trusted_origins_and_saas_host():
    with override_settings(
        WS_ALLOWED_ORIGINS=None,
        CSRF_TRUSTED_ORIGINS=["https://trusted.example.com", "https://*.dbm.example.com"],
    ), patch.object(env, "BK_SAAS_HOST", "https://dbm.example.com/path/"):
        origins = get_ws_allowed_origins()

    assert origins == [
        "https://trusted.example.com",
        "https://*.dbm.example.com",
        "https://.dbm.example.com",
        "https://dbm.example.com",
    ]


def test_ws_allowed_origins_prefers_ws_allowed_origins():
    with override_settings(
        WS_ALLOWED_ORIGINS=["https://ws.example.com"],
        CSRF_TRUSTED_ORIGINS=["https://csrf.example.com"],
    ), patch.object(env, "BK_SAAS_HOST", "https://dbm.example.com/"):
        origins = get_ws_allowed_origins()

    assert origins == ["https://ws.example.com", "https://dbm.example.com"]


def test_ws_origin_validator_allows_verified_jwt_without_origin():
    validator = DBMWebSocketOriginValidator.__new__(DBMWebSocketOriginValidator)
    validator.inner = AsyncMock()
    validator.origin_validator = AsyncMock()
    scope = {"bkapi_jwt_verified": True, "headers": []}

    async_to_sync(validator)(scope, AsyncMock(), AsyncMock())

    validator.inner.assert_awaited_once()
    validator.origin_validator.assert_not_awaited()


def test_ws_origin_validator_checks_origin_for_cookie_request():
    validator = DBMWebSocketOriginValidator.__new__(DBMWebSocketOriginValidator)
    validator.inner = AsyncMock()
    validator.origin_validator = AsyncMock()
    scope = {"headers": [(b"origin", b"https://evil.example.com")]}

    async_to_sync(validator)(scope, AsyncMock(), AsyncMock())

    validator.inner.assert_not_awaited()
    validator.origin_validator.assert_awaited_once()


def test_apigw_jwt_middleware_rejects_invalid_jwt():
    middleware = ApiGatewayJWTAuthMiddleware.__new__(ApiGatewayJWTAuthMiddleware)
    middleware.inner = AsyncMock()
    middleware.provider = Mock(provide=Mock(side_effect=JWTTokenInvalid))
    send = AsyncMock()

    async_to_sync(middleware)({"headers": [(b"x-bkapi-jwt", b"bad-token")]}, AsyncMock(), send)

    send.assert_awaited_once_with({"type": "websocket.close", "code": 4401})
    middleware.inner.assert_not_called()


@pytest.mark.parametrize(
    "origin",
    [
        "http://dev.paas3-dev.bktencent.com:80001",
        "http://dev.paas3-dev.bktencent.com:abc",
        "http://[invalid",
    ],
)
@pytest.mark.parametrize("verified_jwt", [False, True])
def test_ws_origin_validator_rejects_malformed_origin(origin, verified_jwt):
    validator = DBMWebSocketOriginValidator.__new__(DBMWebSocketOriginValidator)
    validator.inner = AsyncMock()
    validator.origin_validator = AsyncMock()
    send = AsyncMock()
    scope = {
        "headers": [(b"origin", origin.encode("latin1"))],
        "bkapi_jwt_verified": verified_jwt,
    }

    async_to_sync(validator)(scope, AsyncMock(), send)

    send.assert_awaited_once_with({"type": "websocket.close"})
    validator.inner.assert_not_awaited()
    validator.origin_validator.assert_not_awaited()
