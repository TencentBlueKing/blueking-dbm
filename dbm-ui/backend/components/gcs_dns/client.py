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
from ..domains import DNS_APIGW_DOMAIN


class _GcsDnsApi(object):
    MODULE = _("GCSDNS域名管理")

    def __init__(self):
        self.get_domain = DataAPI(
            method="GET",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/",
            module=self.MODULE,
            description=_("获取域名映射关系"),
        )
        self.delete_domain = DataAPI(
            method="DELETE",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/",
            module=self.MODULE,
            description=_("删除域名映射"),
        )
        self.update_domain = DataAPI(
            method="POST",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/",
            module=self.MODULE,
            description=_("更新域名映射关系"),
        )
        self.create_domain = DataAPI(
            method="PUT",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/",
            module=self.MODULE,
            description=_("新增域名映射关系"),
        )
        self.batch_update_domain = DataAPI(
            method="POST",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/batch",
            module=self.MODULE,
            description=_("批量更新域名映射关系"),
        )
        self.get_all_domain_list = DataAPI(
            method="GET",
            base=DNS_APIGW_DOMAIN,
            url="/api/v1/dns/domain/all",
            module=self.MODULE,
            description=_("获取所有ip、域名关系"),
        )


GcsDnsApi = _GcsDnsApi()
