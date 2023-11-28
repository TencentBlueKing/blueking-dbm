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
from ..domains import GCS_APIGW_DOMAIN


class _GcsApi(object):
    MODULE = _("Gcs平台")

    def __init__(self):
        self.cloud_privileges_asyn_bydbname = DataAPI(
            method="POST",
            base=GCS_APIGW_DOMAIN,
            url="mysql_privileges/",
            module=self.MODULE,
            description=_("gcs授权接口(mysql和spider)"),
        )

        self.cloud_service_status = DataAPI(
            method="GET",
            base=GCS_APIGW_DOMAIN,
            url="check_service_status/",
            module=self.MODULE,
            description=_("查询gcs作业执行状态"),
        )


GcsApi = _GcsApi()
