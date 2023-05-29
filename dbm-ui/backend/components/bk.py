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

from django.utils.translation import ugettext as _
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
