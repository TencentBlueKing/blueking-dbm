# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-权限中心Python SDK(iam-python-sdk) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import json
import logging
import os
from typing import Any

import curlify
import requests

logger = logging.getLogger("plugin")

HTTP_STATUS_OK_CODE = 200


class HttpResponse(object):
    result: bool
    message: str
    data: Any

    def __init__(self, result, message, data):
        self.result = result
        self.message = message
        self.data = data


class HttpHandler:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    def is_status_ok(self, code):
        return 200 <= code <= 299

    def _gen_header_cookie(self, send_file=False):
        headers = {
            "Content-Type": "application/json",
            "X-Bkapi-Authorization": json.dumps(
                {"bk_app_code": os.getenv("APP_CODE"), "bk_app_secret": os.getenv("APP_TOKEN")}
            ),
        }
        cookie = {"bk_app_code": os.getenv("APP_CODE"), "bk_app_secret": os.getenv("APP_TOKEN")}
        # 如果是form表单提交，则无需自定义Content-Type，request库会自动填充
        if send_file:
            headers.pop("Content-Type")
        return headers, cookie

    def _http_request(
        self, method, url, headers=None, data=None, verify=False, cert=None, timeout=None, cookies=None, **kwargs
    ):
        url = f"{os.getenv('DBM_SAAS_URL')}{url}"
        resp = requests.Response()
        try:
            if method == "GET":
                resp = self.session.get(
                    url=url,
                    headers=headers,
                    params=data,
                    verify=verify,
                    cert=cert,
                    timeout=timeout,
                    cookies=cookies,
                    **kwargs,
                )
            elif method == "HEAD":
                resp = self.session.head(
                    url=url, headers=headers, verify=verify, cert=cert, timeout=timeout, cookies=cookies, **kwargs
                )
            elif method == "POST":
                resp = self.session.post(
                    url=url,
                    headers=headers,
                    json=data,
                    verify=verify,
                    cert=cert,
                    timeout=timeout,
                    cookies=cookies,
                    **kwargs,
                )
            elif method == "DELETE":
                resp = self.session.delete(
                    url=url,
                    headers=headers,
                    json=data,
                    verify=verify,
                    cert=cert,
                    timeout=timeout,
                    cookies=cookies,
                    **kwargs,
                )
            elif method == "PUT":
                resp = self.session.put(
                    url=url,
                    headers=headers,
                    json=data,
                    verify=verify,
                    cert=cert,
                    timeout=timeout,
                    cookies=cookies,
                    **kwargs,
                )
            else:
                return False, "invalid http method: %s" % method, None
        except Exception as e:
            message = "http error! request: [method=`%s`, url=`%s`, data=`%s`] err=`%s`" % (method, url, data, str(e))
            logger.exception(message)
            return HttpResponse(result=False, message=message, data=None)
        else:
            request_id = resp.headers.get("X-Request-Id")

            content = resp.content if resp.content else ""
            if not logger.isEnabledFor(logging.DEBUG) and len(content) > 200:
                content = content[:200] + b"......"

            message_format = (
                "request: [method=`%s`, url=`%s`, data=`%s`] response: [status_code=`%s`, request_id=`%s`, "
                "content=`%s`]"
            )

            if not self.is_status_ok(resp.status_code) or resp.json()["code"]:
                message = message_format % (method, url, str(data), resp.status_code, request_id, content)
                message = f"{message}, error: {resp.json().get('message')}"
                logger.error(message)
                return HttpResponse(result=False, message=message, data=None)

            logger.info(message_format % (method, url, str(data), resp.status_code, request_id, content))
            return HttpResponse(result=True, message="ok", data=resp.json()["data"])
        finally:
            if resp.request is None:
                resp.request = requests.Request(method, url, headers=headers, data=data, cookies=cookies).prepare()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "the request_id: `%s`. curl: `%s`",
                    resp.headers.get("X-Request-Id", ""),
                    curlify.to_curl(resp.request, verify=False),
                )

    def get(self, url, data, headers=None, verify=False, cert=None, timeout=None, cookies=None, **kwargs):
        if not headers:
            headers, cookies = self._gen_header_cookie()
        return self._http_request(
            method="GET",
            url=url,
            headers=headers,
            data=data,
            verify=verify,
            cert=cert,
            timeout=timeout,
            cookies=cookies,
            **kwargs,
        )

    def post(self, url, data, headers=None, verify=False, cert=None, timeout=None, cookies=None, **kwargs):
        if not headers:
            headers, cookies = self._gen_header_cookie()
        return self._http_request(
            method="POST",
            url=url,
            headers=headers,
            data=data,
            verify=verify,
            cert=cert,
            timeout=timeout,
            cookies=cookies,
            **kwargs,
        )

    def put(self, url, data, headers=None, verify=False, cert=None, timeout=None, cookies=None, **kwargs):
        if not headers:
            headers, cookies = self._gen_header_cookie()
        return self._http_request(
            method="PUT",
            url=url,
            headers=headers,
            data=data,
            verify=verify,
            cert=cert,
            timeout=timeout,
            cookies=cookies,
            **kwargs,
        )

    def delete(self, url, data, headers=None, verify=False, cert=None, timeout=None, cookies=None, **kwargs):
        if not headers:
            headers, cookies = self._gen_header_cookie()
        return self._http_request(
            method="DELETE",
            url=url,
            headers=headers,
            data=data,
            verify=verify,
            cert=cert,
            timeout=timeout,
            cookies=cookies,
            **kwargs,
        )
