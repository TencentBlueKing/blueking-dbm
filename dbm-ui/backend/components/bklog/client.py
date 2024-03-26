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
from ..domains import BKLOG_APIGW_DOMAIN


class _BKLogApi(BaseApi):
    MODULE = _("蓝鲸日志平台")
    BASE = BKLOG_APIGW_DOMAIN

    def __init__(self):
        is_esb = self.is_esb()
        self.esquery_search = self.generate_data_api(
            method="POST",
            url="esquery_search/",
            description=_("查询索引"),
        )
        self.fast_create = self.generate_data_api(
            method="POST",
            url="databus/collectors/fast_create/" if is_esb else "databus_collectors/fast_create/",
            description=_("简易创建采集配置"),
        )
        self.fast_update = self.generate_data_api(
            method="POST",
            url="databus/collectors/{collector_config_id}/fast_update/"
            if is_esb
            else "/databus_collectors/{collector_config_id}/fast_update/",
            description=_("简易更新采集配置"),
        )
        self.pre_check = self.generate_data_api(
            method="GET",
            url="databus_collectors/pre_check/",
            description=_("创建采集项的前置检查"),
        )
        self.list_collectors = self.generate_data_api(
            method="GET",
            url="databus_collectors/",
            description=_("获取采集项列表"),
        )


BKLogApi = _BKLogApi()
