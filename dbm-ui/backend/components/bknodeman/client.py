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
from ..domains import BKNODEMAN_APIGW_DOMAIN


class _BKNodeManApi(BaseApi):
    MODULE = _("节点管理")
    BASE = BKNODEMAN_APIGW_DOMAIN

    class JobStatusType(object):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        PROCESSING_STATUS = [PENDING, RUNNING]

    def __init__(self):
        is_esb = self.is_esb()
        self.operate_plugin = self.generate_data_api(method="POST", url="api/plugin/operate/", description=_("插件操作任务"))
        self.job_details = self.generate_data_api(
            method="GET" if is_esb else "POST",
            url="api/job/details/" if is_esb else "api/job/{job_id}/details/",
            description=_("查询任务详情"),
        )
        self.ipchooser_host_details = self.generate_data_api(
            method="POST", url="core/api/ipchooser_host/details/", description=_("查询agent状态")
        )


BKNodeManApi = _BKNodeManApi()
