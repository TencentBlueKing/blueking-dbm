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

from django.utils.translation import gettext as _

from backend import env
from backend.components.base import DataAPI
from backend.components.exception import DataAPIException
from backend.db_proxy.models import DBCloudProxy


class ProxyAPI(DataAPI):
    """
    DB项目专属改造，用于不同云区域的服务请求调用
    """

    def build_actual_url(self, param):
        url = super().build_actual_url(param)

        # 如果配置了DOMAIN_SKIP_PROXY，表示跳过proxy代理
        if env.DOMAIN_SKIP_PROXY:
            return url

        try:
            bk_cloud_id = param["bk_cloud_id"]
        except KeyError:
            raise DataAPIException(_("ProxyApi 必须传入 bk_cloud_id 参数"))

        # 只取最新的nginx作为转发服务
        proxy = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last()
        host = "https://" if self.ssl else "http://"
        external_address = f"{host}{proxy.external_address}"
        return url.replace(self.base.rstrip("/"), external_address)


class ExternalProxyAPI(DataAPI):
    """
    外部代理API，用于将API接口从外部路由转发到内部
    """

    def __call__(
        self,
        params=None,
        data=None,
        raw=False,
        timeout=None,
        raise_exception=True,
        use_admin=False,
        headers=None,
        current_retry_times=0,
    ):
        # 解析url
        params = params or None
        if "_url_path" not in params and not self.url:
            raise DataAPIException(_("必须在请求体中传入 url 参数"))

        self.url = f'{self.base.rstrip("/")}/{params["_url_path"].lstrip("/")}'

        # 添加自定义headers
        headers = headers or {}
        headers.update({"IS-EXTERNAL": "true"})

        return self._send(params, headers, use_admin)

    def _set_session_cookies(self, session, cookies=None, use_admin=False):
        # 转发路由要设置session为空，否则网关会优先以session的用户认证，而忽略headers的bk_username
        session.cookies.clear()
