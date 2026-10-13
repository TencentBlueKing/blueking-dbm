# -*- coding: utf-8 -*-
import json
from http.cookies import SimpleCookie

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from backend import env
from backend.components import BKBaseApi
from backend.components.db_remote_service.client import DRSApi
from backend.db_meta.models import Cluster
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.db_services.mysql.sql_import.constants import SQLCharset
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler
from backend.iam_app.exceptions import PermissionDeniedError
from backend.iam_app.handlers.drf_perm.cluster import check_cluster_webconsole_permission
from backend.utils.time import get_local_charset


class _WebSocketRequest(object):
    """将 Channels 的 scope 适配成 DataAPI 组装鉴权头所需的轻量 request。"""

    def __init__(self, scope):
        self.user = scope["user"]
        self.COOKIES = self._get_cookies(scope)
        self.META = self._get_meta(scope)
        self.is_external = env.ENABLE_EXTERNAL_PROXY or env.ENABLE_OPEN_EXTERNAL_PROXY

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
        self.local_request = None

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
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
            await sync_to_async(self._validate_command, thread_sensitive=True)(content)
            response = await self.drs_session.request(content)
            response = await self._desensitize_response(response)
        except Exception as error:  # pylint: disable=broad-except
            await self.send_json({"result": False, "error": str(error)})
            return
        await self.send_json(response)

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
        if not self.local_request.is_external or not env.BKDATA_DATA_TOKEN:
            return response

        username = self.scope["user"].username
        masked_response = await sync_to_async(BKBaseApi.data_desensitization, thread_sensitive=True)(
            user=username,
            text=json.dumps(response),
            bk_biz_id=self.bk_biz_id,
        )
        return json.loads(masked_response)
