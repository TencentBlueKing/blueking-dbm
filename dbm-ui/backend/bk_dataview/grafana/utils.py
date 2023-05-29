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
import os
from contextlib import contextmanager

from django.conf import settings

logger = logging.getLogger(__name__)


@contextmanager
def os_env(**kwargs):
    """临时修改环境变量"""
    _environ = dict(os.environ)

    # 添加settings变量
    for name in dir(settings):
        if not name.isupper():
            continue

        value = getattr(settings, name, "")
        # 环境变量只允许字符串
        if not isinstance(value, str):
            continue

        os.environ[f"SETTINGS_{name}"] = value

    # 添加自定义变量
    for k, v in kwargs.items():
        if not k.isupper():
            continue
        os.environ[k] = str(v)

    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(_environ)


def requests_curl_log(resp, *args, **kwargs):
    """记录requests curl log"""
    # 添加日志信息
    curl_req = "REQ: curl -X {method} '{url}'".format(method=resp.request.method, url=resp.request.url)

    if resp.request.body:
        curl_req += " -d '{body}'".format(body=resp.request.body)

    if resp.request.headers:
        for key, value in resp.request.headers.items():
            # ignore headers
            if key in ["User-Agent", "Accept-Encoding", "Connection", "Accept", "Content-Length"]:
                continue
            if key == "Cookie" and value.startswith("x_host_key"):
                continue

            curl_req += " -H '{k}: {v}'".format(k=key, v=value)

    if resp.headers.get("Content-Type").startswith("application/json"):
        resp_text = resp.content
    else:
        resp_text = f"Bin...(total {len(resp.content)} Bytes)"

    curl_resp = "RESP: [%s] %.2fms %s" % (resp.status_code, resp.elapsed.total_seconds() * 1000, resp_text)

    logger.info("%s\n \t %s", curl_req, curl_resp)
