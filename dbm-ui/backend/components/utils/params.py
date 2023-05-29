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
import sys

from django.conf import settings

from backend import env
from backend.utils.local import local

logger = logging.getLogger("component")


def build_auth_args(request):
    """
    组装认证信息
    """
    # auth_args 用于ESB身份校验
    auth_args = {}
    if request is None:
        return auth_args

    for key, value in get_oath_cookies_params().items():
        if value in request.COOKIES:
            auth_args.update({key: request.COOKIES[value]})

    return auth_args


def _clean_auth_info_uin(auth_info):
    if "uin" in auth_info:
        # 混合云uin去掉第一位
        if auth_info["uin"].startswith("o"):
            auth_info["uin"] = auth_info["uin"][1:]
    return auth_info


IS_BACKEND = False
for argv in sys.argv:
    if "celery" in argv:
        IS_BACKEND = True
        break
    if "manage.py" in argv and "runserver" not in sys.argv:
        IS_BACKEND = True

# 后台任务 & 测试任务调用 ESB 接口不需要用户权限控制
if IS_BACKEND:

    def add_esb_info_before_request(params):
        params["bk_app_code"] = settings.APP_CODE
        params["bk_app_secret"] = settings.SECRET_KEY
        if "bk_username" not in params:
            params["bk_username"] = "admin"

        params.pop("_request", None)
        return params


# 正常 WEB 请求所使用的函数
else:

    def add_esb_info_before_request(params):
        """
        通过 params 参数控制是否检查 request

        @param {Boolean} [params.no_request] 是否需要带上 request 标识
        """
        # 规范后的参数
        params["bk_app_code"] = settings.APP_CODE
        params["bk_app_secret"] = settings.SECRET_KEY

        if "no_request" in params and params["no_request"]:
            params["bk_username"] = env.DEFAULT_USERNAME
        else:
            # _request，用于并发请求的场景
            _request = params.get("_request")
            req = _request or local.request
            auth_info = build_auth_args(req)
            params.update(auth_info)

            try:
                bk_username = req.user.bk_username if hasattr(req.user, "bk_username") else req.user.username
                if bk_username:
                    params["bk_username"] = bk_username
            except AttributeError:
                # 无登录态则默认为admin
                params["bk_username"] = env.DEFAULT_USERNAME

        params.pop("_request", None)
        return params


def get_oath_cookies_params() -> dict:
    # 企业版给默认值bk_token，其他版本从settings中获取
    return getattr(settings, "OAUTH_COOKIES_PARAMS", {"bk_token": "bk_token"})


def remove_auth_args(params):
    """
    移除认证信息，用于使用admin请求时排除bk_token等信息
    :param params:
    :return:
    """
    for key in get_oath_cookies_params().keys():
        params.pop(key, None)
    return params
