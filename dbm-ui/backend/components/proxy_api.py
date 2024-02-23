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

from backend.components.base import DataAPI
from backend.components.exception import DataAPIException
from backend.db_proxy.models import DBCloudProxy
from backend.db_services.ipchooser.constants import DEFAULT_CLOUD


class ProxyAPI(DataAPI):
    """
    DB项目专属改造，用于不同云区域的服务请求调用
    """

    def build_actual_url(self, param):
        try:
            bk_cloud_id = param["bk_cloud_id"]
        except KeyError:
            raise DataAPIException(_("ProxyApi 必须传入 bk_cloud_id 参数"))

        url = super().build_actual_url(param)
        # 只取最新的nginx作为转发服务
        proxy = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last()
        # 直连区域未部署代理时，直接返回原地址（用于一般容器化环境或本地开发）
        if not proxy and bk_cloud_id == DEFAULT_CLOUD:
            return url
        host = "https://" if self.ssl else "http://"
        external_address = f"{host}{proxy.external_address}"
        return url.replace(self.base.rstrip("/"), external_address)
