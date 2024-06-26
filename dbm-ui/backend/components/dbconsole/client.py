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
from rest_framework.viewsets import ViewSet

from ...env import EXTERNAL_PROXY_DOMAIN
from ..base import BaseApi
from ..proxy_api import ExternalProxyAPI


class _DBConsoleApi(BaseApi):
    MODULE = _("DBConsole")
    BASE = EXTERNAL_PROXY_DOMAIN

    def generate_data_api(self, method, description, **kwargs):
        return ExternalProxyAPI(
            method=method, base=self.BASE, url="", module=self.MODULE, description=description, **kwargs
        )

    def __init__(self):
        for method in ViewSet.http_method_names:
            setattr(self, method, self.generate_data_api(method=method.upper(), description=f"External {method}"))


DBConsoleApi = _DBConsoleApi()
