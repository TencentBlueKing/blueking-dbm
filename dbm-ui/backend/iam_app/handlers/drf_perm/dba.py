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

from typing import List

from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.handlers.drf_perm.base import MoreResourceActionPermission, ResourceActionPermission


class BizDBAPermission(MoreResourceActionPermission):
    """
    业务下DBA人员管理相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None):
        self.actions = actions
        super().__init__(
            actions=actions,
            resource_metes=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
            instance_ids_getters=self.instance_ids_getters,
        )

    @staticmethod
    def instance_ids_getters(request, view):
        data = request.data
        biz__db_type_tuples = [(data["bk_biz_id"], item["db_type"]) for item in data.get("db_admins", [])]
        return biz__db_type_tuples


class GlobalDBAPermission(ResourceActionPermission):
    """
    全局DBA人员管理相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None):
        self.actions = actions
        super().__init__(
            actions=actions, resource_meta=ResourceEnum.DBTYPE, instance_ids_getter=self.instance_dbtype_getter
        )

    @staticmethod
    def instance_dbtype_getter(request, view):
        db_type_list = [item["db_type"] for item in request.data.get("db_admins")]
        return db_type_list
