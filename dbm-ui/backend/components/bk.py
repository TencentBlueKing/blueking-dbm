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
from typing import Dict, Optional

from django.utils.translation import gettext as _
from requests import PreparedRequest
from requests.auth import AuthBase

from backend import env
from backend.utils.http import HttpClient

DEFAULT_USERNAME = env.DEFAULT_USERNAME

logger = logging.getLogger("json")


class BKConfig:
    def __init__(self, host: Optional[str] = None):
        self.host = host if host else env.BK_COMPONENT_API_URL

    @property
    def prefix_path(self):
        """请求前缀"""
        raise NotImplementedError


class BKAuth(AuthBase):
    def __init__(self, username: Optional[str] = None):
        self.bk_app_code = env.APP_CODE
        self.bk_app_secret = env.SECRET_KEY
        self.bk_username = username if username else DEFAULT_USERNAME

    @property
    def basic_payload(self) -> Dict:
        """蓝鲸协议的基础字段"""
        return {
            "bk_app_code": self.bk_app_code,
            "bk_app_secret": self.bk_app_secret,
            "bk_username": self.bk_username,
        }

    @property
    def extra_payload(self) -> Dict:
        """蓝鲸协议的额外自定义字段"""
        return {}

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        payload = self.basic_payload
        if self.extra_payload:
            payload.update(self.extra_payload)
        r.body = self.update_request_body(r.body, payload)
        return r

    @staticmethod
    def update_request_body(body: Optional[bytes], params: Dict) -> bytes:
        """
        更新请求体参数
        :param body: 原始的body
        :param params: 需要添加的参数
        :returns: 返回新的body
        """
        # body体为None时，需要设置为空字典，方便添加参数
        if not body:
            body_dict = {}
        else:
            body_dict = json.loads(bytes.decode(body))
        body_dict.update(params)
        return str.encode(json.dumps(body_dict))


class BKClient:
    def __init__(self, username: str):
        self._config = BKConfig(host=env.BK_COMPONENT_API_URL)
        self._client = HttpClient(BKAuth(username))

    def esb_func_url(self, func_name: str) -> str:
        """构造完整的URL"""
        url = f"{self._config.host}{self._config.prefix_path}{func_name}"
        return url

    def common_request(self, http_method: str, func_name: str, **kwargs) -> Dict:
        """
        请求公共方法
        """
        func_url = self.esb_func_url(func_name)
        logger.info("common request url: {}".format(func_url))
        response = self._client.request_json(http_method, func_url, **kwargs)
        if not response.get("result"):
            logger.error("comm_request response err: {}".format(response))
            raise Exception(_("请求[{}]失败：{}").format(func_url, response.get("message")))
        return response


def resolve_user_access_token(request, app_code: str, app_secret: str) -> str:
    """使用指定应用凭证(app_code/app_secret) + 当前请求携带的用户票据，向鉴权网关换取用户 access_token。

    复用 bkoauth 的鉴权网关(OAUTH_API_URL)标准实现，自动兼容内部版/社区版两种网关协议：
    - 内部版(ieod)：GET  {OAUTH_API_URL}/auth_api/token/
    - 社区版(open)：POST {OAUTH_API_URL}/api/v1/auth/access-tokens
    换取到的 access_token 主体为传入的 app_code；用户身份(bk_token/bk_ticket)由 bkoauth
    从 request.COOKIES 中按 OAUTH_COOKIES_PARAMS 自动提取。

    :param request: 当前 HTTP 请求（需携带用户票据 cookie），无请求上下文时返回空
    :param app_code: 换取 access_token 的应用 code（即 token 主体）
    :param app_secret: 应用 secret
    :return: access_token 字符串，失败时返回空字符串
    """
    if request is None or not app_code or not app_secret:
        return ""

    try:
        from bkoauth.client import oauth_client
        from bkoauth.django_conf import OAUTH_API_URL, OAUTH_COOKIES_PARAMS, OAUTH_PARAMS

        # 使用与当前部署一致的客户端类型，新建实例避免污染全局单例，并替换为指定 app 凭证
        client = type(oauth_client)(OAUTH_API_URL, OAUTH_COOKIES_PARAMS, **OAUTH_PARAMS)
        client.app_code = app_code
        client.secret_key = app_secret

        data = client._get_access_token_data(request)
        return data.get("access_token", "")
    except Exception as e:
        logger.warning("resolve_user_access_token failed, app_code=%s, err=%s", app_code, e)
        return ""
