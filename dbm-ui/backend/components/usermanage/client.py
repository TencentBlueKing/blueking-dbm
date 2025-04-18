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
from ..domains import USER_MANAGE_APIGW_DOMAIN


class _UserManageApi(BaseApi):
    MODULE = _("用户管理模块")
    BASE = USER_MANAGE_APIGW_DOMAIN

    def __init__(self):
        # TODO：前端改造为通用的人员选择器，list_user接口可以后续废弃
        self.list_user = self.generate_data_api(
            method="GET",
            url="tenant/users/",
            description=_("获取所有用户"),
            cache_time=300,
        )
        self.list_tenant = self.generate_data_api(
            method="GET",
            url="tenants/",
            description=_("获取租户列表"),
        )
        self.batch_lookup_virtual_user = self.generate_data_api(
            method="GET",
            url="tenant/virtual-users/-/lookup/",
            description=_("批量查询虚拟用户"),
        )


UserManagerApi = _UserManageApi()
