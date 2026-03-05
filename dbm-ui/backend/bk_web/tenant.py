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
from typing import Optional

from backend import env

logger = logging.getLogger("root")

TENANT_ID_HEADER = "X-Bk-Tenant-Id"


def resolve_tenant_id(request) -> Optional[str]:
    """
    解析当前请求对应的租户ID，作为多租户下的唯一租户解析入口。
    解析优先级：
    1. request.user.tenant_id（浏览器登录后由 blueapps 写入 User 表，权威来源）；
    2. 请求头 X-Bk-Tenant-Id（无用户身份的 API/网关请求按规范携带，也是 tenant-router 路由依据）；
    3. request.app.tenant_id（apigw 应用态租户，如凭证可解析）；
    4. apigw JWT payload 中的 user.tenant_id；
    5. 兜底为部署环境变量 BK_TENANT_ID。
    """
    if request is None or not env.ENABLE_MULTI_TENANT_MODE:
        return env.BK_TENANT_ID

    # 1. 登录用户（User 表 tenant_id，登录时由 blueapps 写入，权威来源）
    user_tenant = getattr(getattr(request, "user", None), "tenant_id", "")
    if user_tenant:
        return user_tenant

    # 2. 请求头（无用户身份的服务/API 调用）
    if hasattr(request, "headers"):
        header_tenant = request.headers.get(TENANT_ID_HEADER, "")
        if header_tenant:
            return header_tenant

    # 3. apigw 应用态租户
    app_tenant = getattr(getattr(request, "app", None), "tenant_id", "")
    if app_tenant:
        return app_tenant

    # 4. JWT payload
    try:
        jwt = getattr(request, "jwt", None)
        if jwt is not None:
            jwt_tenant = jwt.payload.get("user", {}).get("tenant_id")
            return jwt_tenant or env.BK_TENANT_ID
    except Exception as err:  # pylint: disable=broad-except
        logger.warning("resolve tenant_id from jwt failed: %s", err)

    # 5. 兜底
    return env.BK_TENANT_ID
