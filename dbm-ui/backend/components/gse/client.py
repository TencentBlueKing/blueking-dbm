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
from ..domains import GSE_APIGW_DOMAIN


class _GseApi(object):
    MODULE = _("管控平台")

    def __init__(self):
        self.get_agent_status = DataAPI(
            method="POST",
            base=GSE_APIGW_DOMAIN,
            url="get_agent_status/",
            module=self.MODULE,
            description=_("Agent在线状态查询 - 1.0"),
        )

        self.list_agent_state = DataAPI(
            method="POST",
            base=GSE_APIGW_DOMAIN,
            url="list_agent_state/",
            module=self.MODULE,
            description=_("查询Agent状态列表信息 - 2.0"),
        )


GseApi = _GseApi()
