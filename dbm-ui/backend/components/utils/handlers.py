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
from typing import Any, Dict, List, Union

import requests
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components.domains import USER_MANAGE_APIGW_DOMAIN
from backend.components.exception import DataAPIException
from backend.exceptions import ValidationError

logger = logging.getLogger("root")


def get_first_item_from_list(resp: Dict[str, Union[Any, List[Any]]]) -> Any:
    """获取列表中的第一个元素"""
    try:
        resp["data"] = resp["data"][0]
    except IndexError:
        raise DataAPIException(resp, _("接口返回数据为空，请检查接口数据是否正常"))
    return resp


def get_virtual_username():
    """
    获取缓存的租户管理员用户名
    """
    if not env.ENABLE_MULTI_TENANT_MODE:
        return env.DEFAULT_USERNAME

    login_name = "bk_admin"
    cache_key = f"dbm:tenant_admin_username:{env.BK_TENANT_ID}:{login_name}"
    bk_username = cache.get(cache_key, "")
    if not bk_username:
        try:
            auth_data = {"bk_app_code": env.APP_CODE, "bk_app_secret": env.SECRET_KEY}
            auth_hearders = {"X-Bkapi-Authorization": json.dumps(auth_data), "X-Bk-Tenant-Id": env.BK_TENANT_ID}
            params = {"lookup_field": "login_name", "lookups": login_name}
            response = requests.get(
                USER_MANAGE_APIGW_DOMAIN.strip("/") + "/" + "tenant/virtual-users/-/lookup/",
                headers=auth_hearders,
                params=params,
            )
            result = response.json()
            data = result.get("data")
            if isinstance(data, list) and data:
                bk_username = data[0].get("bk_username") or data[0].get("username")
            elif isinstance(data, dict) and data:
                bk_username = data.get("bk_username") or data.get("username")
            if bk_username:
                cache.set(cache_key, bk_username, 60 * 60 * 24)
            else:
                raise ValidationError(_("获取租户管理员账号失败: 未能从响应中获取用户名"))
        except Exception as e:
            error_msg = _("获取租户管理员账号失败: {error}").format(error=str(e))
            logger.error(error_msg)
            raise ValidationError(error_msg)

    return bk_username
