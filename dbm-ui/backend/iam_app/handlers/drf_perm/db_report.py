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
from typing import List

from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission
from backend.utils.string import str2bool

logger = logging.getLogger("root")


class DBReportPermission(ResourceActionPermission):
    """
    巡检报告相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions, resource_meta, self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        platform = str2bool(request.query_params.get("platform", "false"))

        # 如果是个人视角查看管理巡检，则不鉴权
        if "manage" in request.query_params:
            self.actions = self.resource_meta = None
            return []

        # 非平台查询，有业务ID过滤巡检，则用业务鉴权
        if not platform and "bk_biz_id" in request.query_params:
            self.actions = [ActionEnum.HEALTHY_REPORT_VIEW]
            self.resource_meta = ResourceEnum.BUSINESS
            return [request.query_params["bk_biz_id"]]

        # 其他情况则是查看全局巡检，则用平台管理鉴权
        self.actions = [ActionEnum.PLATFORM_HEALTHY_REPORT_VIEW]
        self.resource_meta = None
        return []
