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

from ..base import BaseApi
from ..domains import HADB_APIGW_DOMAIN


class _HADBApi(BaseApi):
    MODULE = _("HADB 服务")
    BASE = HADB_APIGW_DOMAIN

    def __init__(self):
        self.ha_logs = self.generate_data_api(
            method="POST",
            url="halogs/",
            description=_("上报和查询ha的探测切换日志"),
        )
        self.db_status = self.generate_data_api(
            method="POST",
            url="dbstatus/",
            description=_("上报和查询数据库实例的状态"),
        )
        self.ha_status = self.generate_data_api(
            method="POST",
            url="hastatus/",
            description=_("上报和查询ha服务的状态"),
        )
        self.switch_queue = self.generate_data_api(
            method="POST",
            url="switchqueue/",
            description=_("查询和上报切换队列"),
        )
        self.switch_logs = self.generate_data_api(
            method="POST",
            url="switchlogs/",
            description=_("查询切换详情"),
        )
        self.shieldconfig = self.generate_data_api(
            method="POST",
            url="shieldconfig/",
            description=_("DBHA切换屏蔽配置"),
        )


HADBApi = _HADBApi()
