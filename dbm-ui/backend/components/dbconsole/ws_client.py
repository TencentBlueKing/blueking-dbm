# -*- coding: utf-8 -*-
import ssl
from urllib.parse import urlsplit

from backend import env
from backend.components.ws_api import WebSocketAPI

# 固定上游路径，不允许前端传入目标 URL，避免代理成为任意地址转发入口。
WEBCONSOLE_WS_PATH = "ws/dbbase/webconsole/"


class ExternalProxyWSAPI(WebSocketAPI):
    """经 APIGW 连接内网 DBM，不访问云区域代理，也不加载 DRS 客户端证书。"""

    async def build_ssl_context(self, params):
        # 外部网关使用系统信任的 CA 验证服务端证书，不复用 DRS 的跳过校验配置。
        return ssl.create_default_context()

    def build_actual_url(self, params):
        url = super().build_actual_url(params)
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https", "ws", "wss"} or not parsed.hostname:
            raise ValueError("EXTERNAL_PROXY_WS_DOMAIN 必须配置为有效的 HTTP 或 WS 网关地址")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("EXTERNAL_PROXY_WS_DOMAIN 不允许包含用户信息、查询参数或片段")
        return url


def create_webconsole_proxy_api():
    """每个代理连接独立创建客户端，实际响应通过接收协程持续转发。"""
    return ExternalProxyWSAPI(
        method="GET",
        base=env.EXTERNAL_PROXY_WS_DOMAIN,
        url=WEBCONSOLE_WS_PATH,
        module="DBConsole WS 外部代理",
        ssl=False,
        max_retry_times=3,
    )
