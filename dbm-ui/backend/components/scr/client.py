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
from ..domains import SCR_APIGW_DOMAIN


class _ScrApi(object):
    MODULE = _("Scr平台")

    def __init__(self):
        self.common_query = DataAPI(
            method="POST",
            base=SCR_APIGW_DOMAIN,
            url="gcscmdb/common/query/",
            module=self.MODULE,
            freeze_params=True,
            description=_("scr平台通用查询接口)"),
        )


ScrApi = _ScrApi()
