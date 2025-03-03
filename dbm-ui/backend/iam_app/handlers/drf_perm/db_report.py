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

from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import BizOrGlobalResourceActionPermission

logger = logging.getLogger("root")


class DBReportPermission(BizOrGlobalResourceActionPermission):
    """
    巡检报告相关动作鉴权
    """

    def __init__(self, actions=None, resource_meta=None):
        super().__init__(actions, resource_meta)
        self.biz_action = ActionEnum.HEALTHY_REPORT_VIEW
        self.global_action = ActionEnum.PLATFORM_HEALTHY_REPORT_VIEW

    def instance_ids_getter(self, request, view):

        # 如果是个人视角查看管理巡检，则不鉴权
        if "manage" in request.query_params:
            self.actions = self.resource_meta = None
            return []

        return super().instance_ids_getter(request, view)
