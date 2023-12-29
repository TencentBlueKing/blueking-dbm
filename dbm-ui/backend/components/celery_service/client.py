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

from ..base import BaseApi
from ..domains import CELERY_SERVICE_APIGW_DOMAIN


class _CeleryServiceApi(BaseApi):
    MODULE = _("周期任务服务")
    BASE = CELERY_SERVICE_APIGW_DOMAIN

    def __init__(self):
        self.list = self.generate_data_api(
            method="GET",
            freeze_params=True,
            url="/list",
            description=_("获取API列表"),
        )
        self.async_list = self.generate_data_api(
            method="GET",
            url="/discovery",
            description=_("获取周期任务的注册列表"),
        )
        self.async_query = self.generate_data_api(
            method="POST",
            url="/async/query",
            description=_("查询异步会话"),
        )
        self.async_kill = self.generate_data_api(
            method="POST",
            url="/async/kill",
            description=_("结束异步会话"),
        )


CeleryServiceApi = _CeleryServiceApi()
