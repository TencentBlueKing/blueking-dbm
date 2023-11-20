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

from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import HADB_APIGW_DOMAIN


class _HADBApi(object):
    MODULE = _("HADB 服务")

    def __init__(self):
        self.ha_logs = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="halogs/",
            module=self.MODULE,
            description=_("上报和查询ha的探测切换日志"),
        )
        self.db_status = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="dbstatus/",
            module=self.MODULE,
            description=_("上报和查询数据库实例的状态"),
        )
        self.ha_status = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="hastatus/",
            module=self.MODULE,
            description=_("上报和查询ha服务的状态"),
        )
        self.switch_queue = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="switchqueue/",
            module=self.MODULE,
            description=_("查询和上报切换队列"),
        )
        self.switch_logs = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="switchlogs/",
            module=self.MODULE,
            description=_("查询切换详情"),
        )
        self.shieldconfig = DataAPI(
            method="POST",
            base=HADB_APIGW_DOMAIN,
            url="shieldconfig/",
            module=self.MODULE,
            description=_("DBHA切换屏蔽配置"),
        )


HADBApi = _HADBApi()
