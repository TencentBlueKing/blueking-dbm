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
from ..domains import DNS_APIGW_DOMAIN


class _DnsApi(BaseApi):
    MODULE = _("DNS域名管理")
    BASE = DNS_APIGW_DOMAIN

    def __init__(self):
        self.get_domain = self.generate_data_api(
            method="GET",
            url="/api/v1/dns/domain/",
            description=_("获取域名映射关系"),
        )
        self.delete_domain = self.generate_data_api(
            method="DELETE",
            url="/api/v1/dns/domain/",
            description=_("删除域名映射"),
        )
        self.update_domain = self.generate_data_api(
            method="POST",
            url="/api/v1/dns/domain/",
            description=_("更新域名映射关系"),
        )
        self.create_domain = self.generate_data_api(
            method="PUT",
            url="/api/v1/dns/domain/",
            description=_("新增域名映射关系"),
        )
        self.batch_update_domain = self.generate_data_api(
            method="POST",
            url="/api/v1/dns/domain/batch",
            description=_("批量更新域名映射关系"),
        )
        self.get_all_domain_list = self.generate_data_api(
            method="GET",
            url="/api/v1/dns/domain/all",
            description=_("获取所有ip、域名关系"),
        )


DnsApi = _DnsApi()
