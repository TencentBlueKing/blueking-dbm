# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import time
import uuid
from http.cookies import SimpleCookie

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from backend import env
from backend.components import BKBaseApi
from backend.components.db_remote_service.client import DRSApi
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.ws.command_control import CommandLimiter, CommandLimitExceeded, CommandLimitUnavailable
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.db_services.mysql.sql_import.constants import SQLCharset
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler
from backend.iam_app.exceptions import PermissionDeniedError
from backend.iam_app.handlers.drf_perm.cluster import check_cluster_webconsole_permission
from backend.utils.string import str2bool
from backend.utils.time import get_local_charset

audit_logger = logging.getLogger("dbm.webconsole.audit")


class _WebSocketRequest(object):
    """将 Channels 的 scope 适配成 DataAPI 组装鉴权头所需的轻量 request。"""

    def __init__(self, scope):
        self.user = scope["user"]
        self.COOKIES = self._get_cookies(scope)
        self.META = self._get_meta(scope)
        self.is_external = self._is_external_request(scope)

    @staticmethod
    def _is_external_request(scope):
        """结合部署环境和已认证网关的转发标记判断是否需要外部脱敏。"""
        # 外部部署始终脱敏，不能通过省略请求头或传入 false 绕过。
        if env.ENABLE_EXTERNAL_PROXY or env.ENABLE_OPEN_EXTERNAL_PROXY:
            return True
        # 内网仅采信通过 APIGW JWT 验证的请求；此标记由认证中间件写入。
        if not scope.get("bkapi_jwt_verified"):
            return False
        # 外部 WS 代理固定添加 IS-EXTERNAL: true，解析规则与 HTTP 一致。
        for name, value in scope.get("headers", []):
            if name.lower() == b"is-external":
                return str2bool(value.decode("latin1"), strict=False)
        return False

    @staticmethod
    def _get_cookies(scope):
        """从 WebSocket 握手头中解析 cookie，用于透传登录态和 bk_token。"""
        cookie = SimpleCookie()
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                cookie.load(value.decode("latin1"))
        return {key: morsel.value for key, morsel in cookie.items()}

    @staticmethod
    def _get_meta(scope):
        """从 WebSocket 握手信息中提取旧 HTTP request.META 里会用到的字段。"""
        headers = {
            name.decode("latin1").upper().replace("-", "_"): value.decode("latin1")
            for name, value in scope.get("headers", [])
        }
        client = scope.get("client") or ["", ""]
        return {
            "HTTP_X_FORWARDED_FOR": headers.get("X_FORWARDED_FOR", ""),
            "REMOTE_ADDR": client[0],
        }


class WebConsoleConsumer(AsyncJsonWebsocketConsumer):
    CONNECT_REQUEST_TYPE = "CONNECT"
    COMMAND_REQUEST_TYPE = "COMMAND"
    DRS_REQUEST_TYPE_KEY = "request-type"
    COMPAT_REQUEST_TYPE_KEY = "request_type"
    CONNECTED_ALLOWED_REQUEST_TYPES = {COMMAND_REQUEST_TYPE}

    async def connect(self):
        """建立 DBM 侧 WebSocket 连接，并校验用户登录态。"""
        self.drs_context = None
        self.drs_session = None
        self.bk_biz_id = None
        self.cluster_id = None
        self.local_request = None
        self.connection_id = uuid.uuid4().hex
        self.command_running = False

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            # 握手完成后才能发送 WS 关闭码，否则 ASGI 服务只会返回 HTTP 403。
            await self.accept()
            await self.close(code=4401)
            return

        self.local_request = _WebSocketRequest(self.scope)
        await self.accept()

    async def disconnect(self, close_code):
        """关闭 DBM 侧连接时，同步释放 DRS WebSocket 会话。"""
        if self.drs_context:
            await self.drs_context.__aexit__(None, None, None)

    async def receive_json(self, content, **kwargs):
        """处理前端消息：首包 CONNECT 建立 DRS 会话，后续 COMMAND 校验后透传。"""
        try:
            request_type = self._normalize_request_type(content)
        except ValueError as error:
            await self.send_json({"result": False, "error": str(error)})
            await self.close(code=4400)
            return

        # 每条 COMMAND 统一进入业务处理，尚未 CONNECT 的请求也记录审计。
        if request_type == self.COMMAND_REQUEST_TYPE:
            await self._handle_command(content)
            return

        if self.drs_session is None:
            if request_type != self.CONNECT_REQUEST_TYPE:
                await self.send_json({"result": False, "error": "websocket session is not connected"})
                return
            try:
                await self._connect_drs(content)
            except PermissionDeniedError as error:
                await self.send_json({"result": False, "code": 4403, "error": str(error)})
                await self.close(code=4403)
                return
            except Exception as error:  # pylint: disable=broad-except
                await self.send_json({"result": False, "error": str(error)})
                return
        elif request_type not in self.CONNECTED_ALLOWED_REQUEST_TYPES:
            await self.send_json({"result": False, "error": f"unsupported request type: {request_type}"})
            await self.close(code=4400)
            return

        try:
            response = await self.drs_session.request(content)
            response = await self._desensitize_response(response)
        except Exception as error:  # pylint: disable=broad-except
            await self.send_json({"result": False, "error": str(error)})
            return
        await self.send_json(response)

    async def _handle_command(self, content):
        """按校验、限流、转发、脱敏、审计、回推的顺序处理命令。"""
        started = time.monotonic()
        body = content.get("body")
        audit = {
            "command_id": uuid.uuid4().hex,
            "connection_id": self.connection_id,
            "user": self.scope["user"].username,
            # 使用服务端实际绑定的集群，不采信 COMMAND 自行传入的集群 ID。
            "cluster_id": self.cluster_id,
            "bk_biz_id": self.bk_biz_id,
            "sql": body.get("command") if isinstance(body, dict) else None,
            # 未收到 DRS 回包时行数未知，以 null 表示，不能误记为零行。
            "rows_affected": None,
            "status": "error",
            "error": "",
        }
        close_code = None
        try:
            await sync_to_async(self._validate_command, thread_sensitive=True)(content)
            if self.drs_session is None:
                raise ValueError("websocket session is not connected")
            response = await self._execute_limited_command(content, audit)
            # DRS 的 result 是数据，不能作为成功标志；error 为空才表示成功。
            audit["status"] = "success" if audit["error"] == "" else "error"
        except CommandLimitExceeded as error:
            # 429 为业务消息状态码，保留连接，客户端可稍后重试。
            audit.update(status="rejected", error=str(error))
            response = {"result": False, "code": 429, "error": str(error)}
        except CommandLimitUnavailable as error:
            audit.update(status="unavailable", error=str(error))
            response = {"result": False, "code": 503, "error": str(error)}
        except asyncio.TimeoutError:
            audit.update(status="timeout", error="命令等待超时，请重新连接")
            response = {"result": False, "code": 408, "error": audit["error"]}
            close_code = 1011
        except asyncio.CancelledError:
            audit.update(status="cancelled", error="命令处理被取消")
            raise
        except Exception as error:  # pylint: disable=broad-except
            audit["error"] = str(error)
            response = {"result": False, "error": str(error)}
        finally:
            # 耗时包含校验、限流、执行、脱敏及名额释放，不包含前端回推。
            # JSON 编码转义 SQL 中的换行，确保一条命令对应一条结构化日志。
            audit["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
            audit_logger.info("[WEBCONSOLE_COMMAND] %s", json.dumps(audit, ensure_ascii=False))
        await self.send_json(response)
        if close_code is not None:
            await self.close(code=close_code)

    async def _execute_limited_command(self, content, audit):
        """SQL 校验通过后限流，再转发和脱敏，退出时回收并发名额。"""
        # Channels 默认串行分发消息，额外检查防止同一 DRS 会话并行收发。
        # 单连接并发固定为 1，避免响应错配，不提供调大配置。
        if self.command_running:
            raise CommandLimitExceeded("当前连接已有命令执行中")
        self.command_running = True
        token = uuid.uuid4().hex
        limiter = None
        try:
            limiter = CommandLimiter(self.scope["user"].username, self.connection_id)
            # Redis 是同步 IO，放在线程中执行，避免阻塞事件循环。
            await sync_to_async(limiter.acquire, thread_sensitive=False)(token)

            async def execute():
                response = await self.drs_session.request(content)
                # 脱敏前保留执行元信息，即使脱敏失败仍可记录实际行数。
                # 查询结果集不写入审计日志。
                audit["rows_affected"] = response.get("rows_affected")
                audit["error"] = response.get("error", "DRS 响应缺少 error 字段")
                return await self._desensitize_response(response)

            # 总等待上限小于租约；body.timeout 继续透传，超时不重发 COMMAND。
            try:
                return await asyncio.wait_for(execute(), timeout=limiter.command_timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                # 关闭上游，避免迟到的响应被下一条命令误读。
                await self.drs_session.close()
                raise
        finally:
            try:
                if limiter is not None:
                    # 占用响应丢失时也尝试清理，只释放当前命令的唯一 token。
                    await sync_to_async(limiter.release, thread_sensitive=False)(token)
            finally:
                self.command_running = False

    @classmethod
    def _normalize_request_type(cls, content):
        """在校验和转发给 DRS 前，归一化兼容的请求类型字段。"""
        request_type = content.get(cls.DRS_REQUEST_TYPE_KEY)
        compat_request_type = content.get(cls.COMPAT_REQUEST_TYPE_KEY)
        if request_type and compat_request_type and str(request_type).upper() != str(compat_request_type).upper():
            raise ValueError("conflicting request type")

        request_type = request_type or compat_request_type
        if not request_type:
            raise ValueError("request-type is required")

        normalized_request_type = str(request_type).upper()
        content[cls.DRS_REQUEST_TYPE_KEY] = normalized_request_type
        content.pop(cls.COMPAT_REQUEST_TYPE_KEY, None)
        return normalized_request_type

    async def _connect_drs(self, content):
        """复用旧 webconsole 的鉴权和选址逻辑，建立到 DRS 的 WebSocket 连接。"""
        cluster_id = self._get_cluster_id(content)
        username = self.scope["user"].username
        await sync_to_async(check_cluster_webconsole_permission, thread_sensitive=True)(username, cluster_id)
        cluster = await sync_to_async(Cluster.objects.get, thread_sensitive=True)(id=cluster_id)
        self.bk_biz_id = cluster.bk_biz_id
        content["body"] = await sync_to_async(self._build_drs_connect_body, thread_sensitive=True)(cluster, content)

        self.drs_context = DRSApi.v2_webconsole_ws.connect(
            bk_cloud_id=cluster.bk_cloud_id,
            bk_username=username,
            use_param_user=True,
            local_request=self.local_request,
        )
        self.drs_session = await self.drs_context.__aenter__()
        self.cluster_id = cluster.id

    @staticmethod
    def _get_cluster_id(content):
        """兼容从顶层或 body 中读取 cluster_id。"""
        body = content.get("body") or {}
        cluster_id = content.get("cluster_id") or body.get("cluster_id")
        if not cluster_id:
            raise ValueError("cluster_id is required")
        return int(cluster_id)

    @staticmethod
    def _build_drs_connect_body(cluster, content):
        """将前端 CONNECT 消息转换成 DRS /v2/webconsole/ws 需要的连接参数。"""
        body = content.get("body") or {}
        options = content.get("options") or body.get("options") or {}
        cluster_id__role_map = {}
        if options.get("role"):
            cluster_id__role_map[cluster.id] = options["role"]

        __, remote_address = RemoteServiceHandler(bk_biz_id=cluster.bk_biz_id)._get_cluster_address(
            cluster_id__role_map=cluster_id__role_map,
            cluster_id=cluster.id,
        )

        drs_body = {
            "address": remote_address,
            "charset": options.get("charset", SQLCharset.DEFAULT.value),
            "timezone": options.get("timezone", get_local_charset()),
        }
        if body.get("timeout"):
            drs_body["timeout"] = body["timeout"]
        if body.get("pre_hook_cmds"):
            drs_body["pre_hook_cmds"] = body["pre_hook_cmds"]
        if body.get("skip_set_names"):
            drs_body["skip_set_names"] = body["skip_set_names"]
        return drs_body

    @staticmethod
    def _validate_command(content):
        """复用旧 POST 接口的 SQL 白名单，只允许 webconsole 查询类语句。"""
        request_type = (content.get(WebConsoleConsumer.DRS_REQUEST_TYPE_KEY) or "").upper()
        if request_type != WebConsoleConsumer.COMMAND_REQUEST_TYPE:
            return

        body = content.get("body") or {}
        command = body.get("command")
        if not command:
            raise ValueError("command is required")
        SQLParseHandler().parse_select_statement(sql=command, db_query=False)

    async def _desensitize_response(self, response):
        """外部请求返回前复用旧接口的 BKBase 脱敏逻辑。"""
        # 与 HTTP 一致：配置 V2 地址或 V1 Token 均可启用脱敏，版本由公共 API 选择。
        if not self.local_request.is_external or not (env.BKDATA_SENSI_AGENT_URL or env.BKDATA_DATA_TOKEN):
            return response

        username = self.scope["user"].username
        masked_response = await sync_to_async(BKBaseApi.data_desensitization, thread_sensitive=True)(
            user=username,
            text=json.dumps(response),
            bk_biz_id=self.bk_biz_id,
        )
        return json.loads(masked_response)
