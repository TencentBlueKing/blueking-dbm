# -*- coding: utf-8 -*-
import asyncio
import json
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from websockets.exceptions import ConnectionClosed

from backend import env
from backend.bk_web.constants import IP_RE
from backend.components.dbconsole.ws_client import WEBCONSOLE_WS_PATH, create_webconsole_proxy_api
from backend.db_services.dbbase.ws.consumers import WebConsoleConsumer, _WebSocketRequest

logger = logging.getLogger("root")


class ExternalWebConsoleConsumer(AsyncJsonWebsocketConsumer):
    """外部只代理 WebConsole，业务鉴权、SQL 校验、限流和审计均在内网执行。"""

    async def connect(self):
        self.upstream_context = None
        self.upstream = None
        self.relay_task = None
        # 独立 WS 白名单，不复用 HTTP 的宽泛匹配，也不开放动态目标路径。
        if self.scope.get("path") != f"/{WEBCONSOLE_WS_PATH}":
            await self.close(code=4403)
            return
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.accept()
            await self.close(code=4401)
            return
        # 网关错误地回指外部部署时拒绝二次代理，避免无限建连。
        if any(name.lower() == b"x-dbm-ws-proxy" for name, _ in self.scope.get("headers", [])):
            await self.accept()
            await self.send_json({"result": False, "error": "WS 网关后端必须指向内网 dbm-ws"})
            await self.close(code=1011)
            return

        await self.accept()
        try:
            api = create_webconsole_proxy_api()
            self.upstream_context = api.connect(
                bk_username=user.username,
                use_param_user=True,
                local_request=_WebSocketRequest(self.scope),
                # 不透传客户端的 Cookie、Origin、JWT 和外部标记。
                # WebSocketAPI 将登录凭据组装到 X-Bkapi-Authorization，网关签发新的 JWT。
                headers={"IS-EXTERNAL": "true", "X-DBM-WS-Proxy": "1"},
            )
            self.upstream = await self.upstream_context.__aenter__()
            # 独立接收协程转发响应和关闭帧，空闲时也能感知内网上游断开。
            self.relay_task = asyncio.create_task(self._relay_responses())
        except asyncio.CancelledError:
            await self._close_upstream()
            raise
        except Exception:  # pylint: disable=broad-except
            logger.exception("外部 WebConsole 连接内网 WS 失败")
            # 建连异常可能包含内网 IP、网关 URL，不将底层异常直接返回浏览器。
            await self.send_json({"result": False, "error": "连接内网 WebConsole 失败，请稍后重试"})
            await self.close(code=1011)
            await self._close_upstream()

    async def receive_json(self, content, **kwargs):
        if self.upstream is None:
            await self.close(code=1011)
            return
        try:
            if not isinstance(content, dict):
                raise ValueError("请求必须是 JSON 对象")
            request_type = WebConsoleConsumer._normalize_request_type(content)
            if request_type not in {"CONNECT", "COMMAND"}:
                raise ValueError("仅允许 CONNECT 和 COMMAND 请求")
        except ValueError as error:
            await self.send_json({"result": False, "error": str(error)})
            await self.close(code=4400)
            return
        try:
            # 原样保留 cluster_id、options 和 SQL，由内网 Consumer 重新鉴权和校验。
            # 只发送一次，不对 COMMAND 重连或重放；响应由接收协程转发。
            await self.upstream.websocket.send(json.dumps(content))
        except ConnectionClosed as error:
            await self.close(code=self._close_code(error.rcvd.code if error.rcvd else None))
        except Exception:  # pylint: disable=broad-except
            logger.exception("外部 WebConsole 向内网转发消息失败")
            await self.send_json({"result": False, "error": "内网 WebConsole 连接异常，请重新连接"})
            await self.close(code=1011)

    async def _relay_responses(self):
        try:
            while True:
                message = await self.upstream.websocket.recv()
                response = json.loads(message)
                # 对齐 HTTP after_response：普通外部代理屏蔽 IPv4，开放代理保留原响应。
                # SQL 数据脱敏已由内网 Consumer 根据 IS-EXTERNAL 完成。
                if not env.ENABLE_OPEN_EXTERNAL_PROXY:
                    response = json.loads(IP_RE.sub("*.*.*.*", json.dumps(response, ensure_ascii=False)))
                await self.send_json(response)
        except ConnectionClosed as error:
            # 保留内网 4403 等业务关闭码，不将包含内部信息的关闭原因直接透传。
            await self.close(code=self._close_code(error.rcvd.code if error.rcvd else None))
        except asyncio.CancelledError:
            raise
        except Exception:  # pylint: disable=broad-except
            logger.exception("外部 WebConsole 接收内网响应失败")
            await self.send_json({"result": False, "error": "内网 WebConsole 响应异常，请重新连接"})
            await self.close(code=1011)
        finally:
            await self._close_upstream()

    @staticmethod
    def _close_code(code):
        # 1005、1006、1015 不能写入关闭帧，将异常断开统一转换为 1011。
        if code in {1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014}:
            return code
        if isinstance(code, int) and 3000 <= code <= 4999:
            return code
        return 1011

    async def _close_upstream(self):
        # 先清空引用，使断连回调与接收协程同时清理时不会重复释放。
        upstream, self.upstream = self.upstream, None
        if upstream is not None:
            try:
                await upstream.close()
            except Exception:  # pylint: disable=broad-except
                logger.exception("外部 WebConsole 关闭内网连接失败")

    async def disconnect(self, close_code):
        if self.relay_task is not None:
            self.relay_task.cancel()
            await asyncio.gather(self.relay_task, return_exceptions=True)
        await self._close_upstream()
