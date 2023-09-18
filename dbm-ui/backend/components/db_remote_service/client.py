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

from django.utils.translation import ugettext_lazy as _

from backend import env

from ..domains import DRS_APIGW_DOMAIN
from ..proxy_api import ProxyAPI


class _DRSApi(object):
    MODULE = _("DB 远程服务")
    BASE_DOMAIN = DRS_APIGW_DOMAIN

    def __init__(self):
        ssl_flag = True

        # 配置了DRS_SKIP_SSL，认为跳过ssl认证
        if env.DRS_SKIP_SSL:
            ssl_flag = False

        self.rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="mysql/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB 远程执行"),
        )

        self.proxyrpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="proxy-admin/rpc",
            module=self.MODULE,
            ssl=ssl_flag,
            description=_("DB PROXY远程执行"),
        )

        self.redis_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="redis/rpc",
            module=self.MODULE,
            ssl=True,
            description=_("redis 远程执行"),
        )

        self.twemproxy_rpc = ProxyAPI(
            method="POST",
            base=self.BASE_DOMAIN,
            url="twemproxy/rpc",
            module=self.MODULE,
            ssl=True,
            description=_("twemproxy 远程执行"),
        )


DRSApi = _DRSApi()
