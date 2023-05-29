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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import BKLOG_APIGW_DOMAIN


class _BKLogApi(object):
    MODULE = _("蓝鲸日志平台")

    def __init__(self):
        self.esquery_search = DataAPI(
            method="POST",
            base=BKLOG_APIGW_DOMAIN,
            url="esquery_search/",
            module=self.MODULE,
            description=_("查询索引"),
        )
        self.fast_create = DataAPI(
            method="POST",
            base=BKLOG_APIGW_DOMAIN,
            url="databus/collectors/fast_create/" if settings.RUN_VER == "open" else "databus_collectors/fast_create/",
            module=self.MODULE,
            description=_("简易创建采集配置"),
        )
        self.fast_update = DataAPI(
            method="POST",
            base=BKLOG_APIGW_DOMAIN,
            url="databus/collectors/{collector_config_id}/fast_update/"
            if settings.RUN_VER == "open"
            else "/databus_collectors/{collector_config_id}/fast_update/",
            module=self.MODULE,
            description=_("简易更新采集配置"),
        )
        self.pre_check = DataAPI(
            method="GET",
            base=BKLOG_APIGW_DOMAIN,
            url="databus_collectors/pre_check/",
            module=self.MODULE,
            description=_("创建采集项的前置检查"),
        )
        self.list_collectors = DataAPI(
            method="GET",
            base=BKLOG_APIGW_DOMAIN,
            url="databus_collectors/",
            module=self.MODULE,
            description=_("获取采集项列表"),
        )


BKLogApi = _BKLogApi()
