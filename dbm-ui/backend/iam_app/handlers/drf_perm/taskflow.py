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

from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.dataclass.resources import ResourceMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

logger = logging.getLogger("root")


class TaskFlowPermission(ResourceActionPermission):
    """
    任务历史相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta], resource_meta: ResourceMeta = None) -> None:
        instance_ids_getter = self.instance_id_getter
        super().__init__(actions, resource_meta, instance_ids_getter)

    def instance_id_getter(self, request, view):
        return self.get_key_id(request, view, self.resource_meta.lookup_field, many=True)
