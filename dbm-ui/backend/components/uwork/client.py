# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import UWORK_APIGW_DOMAIN


class _UWORKApi(BaseApi):
    MODULE = _("星象 服务")
    BASE = UWORK_APIGW_DOMAIN

    def __init__(self):
        self.uwork_list = self.generate_data_api(
            method="POST",
            url="/xray-srv-process-reception/queryMergedFaultInfo",
            description=_("获取故障机器列表"),
        )


UWORKApi = _UWORKApi()
