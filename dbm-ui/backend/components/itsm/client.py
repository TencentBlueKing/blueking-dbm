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

from ..base import DataAPI
from ..domains import ITSM_APIGW_DOMAIN


class _ItsmApi(object):
    MODULE = _("ITSM流程管理")

    def __init__(self):
        self.create_ticket = DataAPI(
            method="POST",
            base=ITSM_APIGW_DOMAIN,
            url="create_ticket/",
            module=self.MODULE,
            description=_("创建单据"),
        )
        self.ticket_approval_result = DataAPI(
            method="POST",
            base=ITSM_APIGW_DOMAIN,
            url="ticket_approval_result/",
            module=self.MODULE,
            description=_("审批结果查询"),
        )
        self.get_ticket_logs = DataAPI(
            method="GET",
            base=ITSM_APIGW_DOMAIN,
            url="get_ticket_logs/",
            module=self.MODULE,
            description=_("单据日志查询"),
        )
        self.get_service_catalogs = DataAPI(
            method="GET",
            base=ITSM_APIGW_DOMAIN,
            url="get_service_catalogs/",
            module=self.MODULE,
            description=_("服务目录查询"),
        )
        self.get_services = DataAPI(
            method="GET", base=ITSM_APIGW_DOMAIN, url="get_services/", module=self.MODULE, description=_("服务列表查询")
        )
        self.create_service_catalog = DataAPI(
            method="POST",
            base=ITSM_APIGW_DOMAIN,
            url="create_service_catalog/",
            module=self.MODULE,
            description=_("创建服务目录"),
        )
        self.import_service = DataAPI(
            method="POST", base=ITSM_APIGW_DOMAIN, url="import_service/", module=self.MODULE, description=_("导入服务")
        )
        self.update_service = DataAPI(
            method="POST", base=ITSM_APIGW_DOMAIN, url="update_service/", module=self.MODULE, description=_("更新服务")
        )


ItsmApi = _ItsmApi()
