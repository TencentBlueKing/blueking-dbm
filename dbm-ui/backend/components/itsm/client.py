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
from ..domains import ITSM_APIGW_DOMAIN


class _ItsmApi(BaseApi):
    MODULE = _("ITSM流程管理")
    BASE = ITSM_APIGW_DOMAIN

    def __init__(self):
        self.create_ticket = self.generate_data_api(
            method="POST",
            url="create_ticket/",
            description=_("创建单据"),
        )
        self.ticket_approval_result = self.generate_data_api(
            method="POST",
            url="ticket_approval_result/",
            description=_("审批结果查询"),
        )
        self.get_ticket_logs = self.generate_data_api(
            method="GET",
            url="get_ticket_logs/",
            description=_("单据日志查询"),
        )
        self.get_service_catalogs = self.generate_data_api(
            method="GET",
            url="get_service_catalogs/",
            description=_("服务目录查询"),
        )
        self.get_services = self.generate_data_api(method="GET", url="get_services/", description=_("服务列表查询"))
        self.create_service_catalog = self.generate_data_api(
            method="POST",
            url="create_service_catalog/",
            description=_("创建服务目录"),
        )
        self.import_service = self.generate_data_api(method="POST", url="import_service/", description=_("导入服务"))
        self.update_service = self.generate_data_api(method="POST", url="update_service/", description=_("更新服务"))


ItsmApi = _ItsmApi()
