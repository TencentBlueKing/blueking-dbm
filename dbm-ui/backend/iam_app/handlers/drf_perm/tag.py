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
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id

logger = logging.getLogger("root")


class TagPermission(ResourceActionPermission):
    """
    标签管理相关权限
    """

    def __init__(self, actions=None, resource_meta=None, instance_ids_getter=None):
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # Todo 后续要考虑集群标签权限
        bk_biz_id = get_request_key_id(request, "bk_biz_id")
        if bk_biz_id:
            self.actions = [ActionEnum.RESOURCE_TAG_MANAGE]
            self.resource_meta = ResourceEnum.BUSINESS
            return [bk_biz_id]
        else:
            self.actions = [ActionEnum.GLOBAL_RESOURCE_TAG_MANAGE]
            return []
