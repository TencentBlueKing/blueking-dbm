# -*- coding: utf-8 -*-
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from asgiref.sync import async_to_sync

from backend.components.exception import DataAPIException
from backend.components.ws_api import ProxyWSAPI, WebSocketSession, _to_ws_url


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "HTTPS://bk-dbm-nginx.paas3-dev.bktencent.com/v2/webconsole/ws",
            "wss://bk-dbm-nginx.paas3-dev.bktencent.com/v2/webconsole/ws",
        ),
        ("http://example.com/ws?token=1", "ws://example.com/ws?token=1"),
        ("wss://example.com/ws", "wss://example.com/ws"),
    ],
)
def test_to_ws_url_normalizes_http_scheme(source, expected):
    assert _to_ws_url(source) == expected


def test_to_ws_url_rejects_unsupported_scheme():
    with pytest.raises(DataAPIException):
        _to_ws_url("ftp://example.com/ws")


@patch("backend.components.ws_api.DBCloudProxy.get_cloud_proxy_external_address")
@patch("backend.components.ws_api.env.CLOUD_CONTAINER_ENABLE", False)
@patch("backend.components.ws_api.env.DOMAIN_SKIP_PROXY", False)
def test_proxy_ws_api_build_actual_url_returns_websocket_scheme(get_external_address_mock):
    get_external_address_mock.return_value = "bk-dbm-nginx.paas3-dev.bktencent.com"
    api = ProxyWSAPI(method="GET", base="https://drs.example.com", url="v2/webconsole/ws", module="DB", ssl=False)

    assert api.build_actual_url({"bk_cloud_id": 5}) == "wss://bk-dbm-nginx.paas3-dev.bktencent.com/v2/webconsole/ws"


def test_websocket_session_request_uses_default_timeout():
    api = SimpleNamespace(default_timeout=7, module="DB")
    session = WebSocketSession(api, params={}, headers={}, use_admin=False, use_param_user=False)
    session.websocket = AsyncMock()
    session.websocket.recv = AsyncMock()

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        assert timeout == 7
        return '{"result": true}'

    with patch("backend.components.ws_api.asyncio.wait_for", fake_wait_for):
        response = async_to_sync(session.request)({"request-type": "COMMAND"})

    assert response == {"result": True}
    session.websocket.send.assert_awaited_once_with('{"request-type": "COMMAND"}')
    session.websocket.close.assert_not_awaited()


def test_websocket_session_request_closes_on_timeout():
    api = SimpleNamespace(default_timeout=7, module="DB")
    session = WebSocketSession(api, params={}, headers={}, use_admin=False, use_param_user=False)
    websocket = AsyncMock()
    websocket.recv = AsyncMock()
    session.websocket = websocket

    async def fake_wait_for(awaitable, timeout):
        awaitable.close()
        assert timeout == 7
        raise asyncio.TimeoutError

    with patch("backend.components.ws_api.asyncio.wait_for", fake_wait_for), pytest.raises(
        DataAPIException, match="websocket request timeout after 7s"
    ):
        async_to_sync(session.request)({"request-type": "COMMAND"})

    websocket.send.assert_awaited_once_with('{"request-type": "COMMAND"}')
    websocket.close.assert_awaited_once()
    assert session.websocket is None


def test_websocket_api_connect_does_not_mutate_singleton_user_flag():
    api = ProxyWSAPI(method="GET", base="https://drs.example.com", url="v2/webconsole/ws", module="DB", ssl=False)
    api.use_param_user = False

    session = api.connect(params={"bk_cloud_id": 5}, use_param_user=True)

    assert session.use_param_user is True
    assert api.use_param_user is False


def test_websocket_headers_use_session_state_without_mutating_api():
    api = ProxyWSAPI(method="GET", base="https://drs.example.com", url="v2/webconsole/ws", module="DB", ssl=False)
    api.request_id = "old-request-id"
    api.use_param_user = False
    session = SimpleNamespace(headers={})

    api._set_ws_session_headers(
        session,
        local_request=None,
        headers={},
        params={"bk_username": "alice"},
        use_param_user=True,
        request_id="session-request-id",
    )

    assert session.headers["X-Bkapi-Request-Id"] == "session-request-id"
    assert json.loads(session.headers["X-Bkapi-Authorization"])["bk_username"] == "alice"
    assert api.request_id == "old-request-id"
    assert api.use_param_user is False


@patch("backend.components.ws_api.env.CLOUD_CONTAINER_ENABLE", True)
@patch("backend.components.ws_api.env.DOMAIN_SKIP_PROXY", False)
def test_proxy_ws_api_container_build_url_does_not_mutate_ssl():
    api = ProxyWSAPI(method="GET", base="https://drs.example.com", url="v2/webconsole/ws", module="DB", ssl=True)

    assert api.build_actual_url({"bk_cloud_id": 0}) == "wss://drs.example.com/v2/webconsole/ws"
    assert api.ssl is True
    assert api.use_client_cert({"bk_cloud_id": 0}) is False
