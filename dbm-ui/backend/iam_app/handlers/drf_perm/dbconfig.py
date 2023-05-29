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

from backend.db_meta.enums import ClusterType
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    ResourceActionPermission,
    get_request_key_id,
)


class BizDBConfigPermission(BizDBTypeResourceActionPermission):
    """
    业务下数据库配置相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None):
        self.actions = actions
        super().__init__(
            actions=actions,
            instance_biz_getter=self.instance_biz_getter,
            instance_dbtype_getter=self.instance_dbtype_getter,
        )

    @staticmethod
    def instance_biz_getter(request, view):
        return [get_request_key_id(request, key="bk_biz_id")]

    @staticmethod
    def instance_dbtype_getter(request, view):
        cluster_type = get_request_key_id(request, key="meta_cluster_type")
        return [ClusterType.cluster_type_to_db_type(cluster_type)]


class GlobalConfigPermission(ResourceActionPermission):
    def __init__(self, actions: List[ActionMeta] = None):
        self.actions = actions
        super().__init__(
            actions=actions, resource_meta=ResourceEnum.DBTYPE, instance_ids_getter=self.instance_dbtype_getter
        )

    @staticmethod
    def instance_dbtype_getter(request, view):
        return BizDBConfigPermission.instance_dbtype_getter(request, view)
