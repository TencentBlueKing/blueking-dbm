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
import logging
from typing import Any, Dict, Optional

import requests
from requests import HTTPError as RequestHTTPError
from requests import RequestException, Response, adapters
from requests.auth import AuthBase

from backend.utils.local import local

logger = logging.getLogger(__name__)


class BaseHTTPError(Exception):
    """请求异常基类"""


class RequestError(BaseHTTPError):
    """请求异常错误"""

    def __init__(self, url: str, exc: Exception):
        """
        :param url: 请求 URL 地址
        :param exc: 原异常对象
        """
        self.url = url
        self.exc = exc
        super().__init__(f'request error "{url}": {exc}')


class ResponseError(BaseHTTPError):
    """请求响应错误"""

    def __init__(self, url: str, response: Response, exc: Exception):
        """
        :param url: 请求 URL 地址
        :param response: 请求响应对象
        :param exc: 原异常对象
        """
        self.url = url
        self.response = response
        self.exc = exc
        super().__init__(f'response error "{url}": {exc}')


class InternalError(BaseHTTPError):
    """模块内部错误（未知）错误"""

    def __str__(self):
        s = super().__str__()
        return f"comp internal error: {s}"


# 使用全局的 requests 请求池
POOL_MAXSIZE = 10

_pool_adapter = adapters.HTTPAdapter(pool_connections=POOL_MAXSIZE, pool_maxsize=POOL_MAXSIZE)


class HttpClient:
    """发送 HTTP 请求的 Client 模块，基于 requests 模块包装而来。提供常见的工具函数，并对异常进行封装。"""

    _default_timeout = 30
    _ssl_verify = False

    def __init__(self, auth: Optional[AuthBase] = None):
        """
        :param auth: 默认 requests 身份校验对象
        """
        self._auth = auth

    def request(self, method: str, url: str, **kwargs) -> Response:
        """发送 HTTP 请求

        :param method: 请求类型，GET / POST / ...
        :param url: 请求地址
        :param raise_for_status: 是否在响应状态码非 2xx 时抛出异常
        :param **kwargs: 其他请求参数
        :raises: CompRequestError（请求错误），CompInternalError（内部错误）
        """
        raise_for_status = kwargs.pop("raise_for_status", True)

        self.set_defaults_kwargs(kwargs)
        # 设置请求 request-id
        kwargs["headers"]["X-Request-Id"] = local.request_id

        session = requests.session()
        session.mount("http://", _pool_adapter)
        session.mount("https://", _pool_adapter)

        try:
            # TODO：记录请求日志
            resp = session.request(method, url, **kwargs)
        except RequestException as e:
            logger.exception("requests error when requesting %s: %s", url, e)
            raise RequestError(url, e)
        except Exception as e:
            logger.exception("internal error when requesting %s: %s", url, e)
            raise InternalError(str(e)) from e

        if raise_for_status:
            try:
                resp.raise_for_status()
            except RequestHTTPError as e:
                raise RequestError(url, e)

        return resp

    def request_json(self, method: str, url: str, **kwargs) -> Any:
        """请求并尝试返回 Json 结果"""
        resp = self.request(method, url, **kwargs)
        return resp.json()

    def set_defaults_kwargs(self, kwargs: Dict[str, Any]):
        """修改请求 kwargs，设置默认的请求参数

        :param kwargs: 用于 requests.request 请求参数
        """
        kwargs.setdefault("auth", self._auth)
        kwargs.setdefault("timeout", self._default_timeout)
        kwargs.setdefault("verify", self._ssl_verify)
        kwargs.setdefault("headers", {})
