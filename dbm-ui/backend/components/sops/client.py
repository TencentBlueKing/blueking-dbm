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
from ..domains import SOPS_APIGW_DOMAIN


class _BkSopsApi(BaseApi):
    MODULE = _("标准运维")
    BASE = SOPS_APIGW_DOMAIN

    def __init__(self):
        is_esb = self.is_esb()
        self.create_task = self.generate_data_api(
            method="POST",
            url="create_task/" if is_esb else "create_task/{template_id}/{bk_biz_id}/",
            description=_("通过业务流程模版创建任务"),
        )
        self.start_task = self.generate_data_api(
            method="POST",
            url="start_task/" if is_esb else "start_task/{task_id}/{bk_biz_id}/",
            description=_("启动任务"),
        )
        self.get_task_status = self.generate_data_api(
            method="GET",
            url="get_task_status/" if is_esb else "get_task_status/{task_id}/{bk_biz_id}/",
            description=_("查询任务状态"),
        )
        self.get_task_node_detail = self.generate_data_api(
            method="GET",
            url="get_task_node_detail/" if is_esb else "get_task_node_detail/{task_id}/{bk_biz_id}/",
            description=_("查询任务节点执行详情"),
        )


BkSopsApi = _BkSopsApi()
