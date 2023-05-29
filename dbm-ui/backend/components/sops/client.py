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

import logging
import urllib.parse

from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import SOPS_APIGW_DOMAIN

logger = logging.getLogger("component")


class _BkSopsApi(object):
    MODULE = _("标准运维")

    def __init__(self):
        # logger.info(f"sops domain: {SOPS_APIGW_DOMAIN}")
        self.create_task = DataAPI(
            method="POST",
            base=SOPS_APIGW_DOMAIN,
            url="create_task/",
            module=self.MODULE,
            description=_("通过业务流程模版创建任务"),
        )
        self.start_task = DataAPI(
            method="POST",
            base=SOPS_APIGW_DOMAIN,
            url="start_task/",
            module=self.MODULE,
            description=_("启动任务"),
        )
        self.query_task_status = DataAPI(
            method="GET",
            base=SOPS_APIGW_DOMAIN,
            url="get_task_status/",
            module=self.MODULE,
            description=_("查询任务状态"),
        )
        self.task_detail = DataAPI(
            method="GET",
            base=SOPS_APIGW_DOMAIN,
            url="get_task_detail/",
            module=self.MODULE,
            description=_("查询任务详情"),
        )
        self.task_node_detail = DataAPI(
            method="GET",
            base=SOPS_APIGW_DOMAIN,
            url="get_task_node_detail/",
            module=self.MODULE,
            description=_("查询任务Node详情"),
        )


BkSopsApi = _BkSopsApi()
