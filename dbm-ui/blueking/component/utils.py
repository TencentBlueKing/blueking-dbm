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
import re
import json
import base64
import hmac
import hashlib


def get_signature(method, path, app_secret, params=None, data=None):
    """generate signature"""
    kwargs = {}
    if params:
        kwargs.update(params)
    if data:
        data = json.dumps(data) if isinstance(data, dict) else data
        kwargs["data"] = data
    kwargs = "&".join(["%s=%s" % (k, v) for k, v in sorted(kwargs.items(), key=lambda x: x[0])])
    orignal = "%s%s?%s" % (method, path, kwargs)
    app_secret = app_secret.encode("utf-8") if isinstance(app_secret, str) else app_secret
    orignal = orignal.encode("utf-8") if isinstance(orignal, str) else orignal
    signature = base64.b64encode(hmac.new(app_secret, orignal, hashlib.sha1).digest())
    return signature if isinstance(signature, str) else signature.decode("utf-8")


def transform_uin(uin):
    """
    将uin转换为字符型的qq号
    去掉第一个字符然后转为整形
    o01234567 -> 1234567
    """
    match = re.match(r"^o(?P<uin>\d{3,32})$", uin)
    if match:
        return str(int(match.group("uin")))
    return uin


def get_auth_params(request, auth_cookies_params):
    auth_params = {}
    for key, cookie_name in auth_cookies_params.items():
        value = (
            request.COOKIES.get(cookie_name) or request.session.get(cookie_name) or request.GET.get(cookie_name, "")
        )
        if key == "uin":
            value = transform_uin(value)
        if value:
            auth_params[key] = value
    return auth_params
