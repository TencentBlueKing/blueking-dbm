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

from backend.configuration.constants import BizSettingsEnum
from backend.db_meta.enums import ClusterType
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.handlers.drf_perm.base import (
    BizDBTypeResourceActionPermission,
    ResourceActionPermission,
    get_request_key_id,
)


def meta_cluster_type_to_db_type(meta_cluster_type: str) -> str:
    """
    dbconfig 场景下将 meta_cluster_type/namespace 映射为 db_type
    通用配置(meta_cluster_type=common)无法映射到真实 db_type，使用 common 特殊实例兜底
    """
    try:
        return ClusterType.cluster_type_to_db_type(meta_cluster_type)
    except ValueError:
        return "common"


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
        namespace = cluster_type or get_request_key_id(request, key="namespace")
        return [meta_cluster_type_to_db_type(namespace)]


class GlobalConfigPermission(ResourceActionPermission):
    def __init__(self, actions: List[ActionMeta] = None):
        self.actions = actions
        super().__init__(
            actions=actions, resource_meta=ResourceEnum.DBTYPE, instance_ids_getter=self.instance_dbtype_getter
        )

    @staticmethod
    def instance_dbtype_getter(request, view):
        return BizDBConfigPermission.instance_dbtype_getter(request, view)


class ClusterLevelConfigPermission(ResourceActionPermission):
    """
    集群层级(level_name=cluster)配置鉴权:
    - 查看复用各组件的 {dbtype}_view
    - 编辑使用各组件的 {dbtype}_dbconfig_edit
    资源均为集群实例，集群通过 level_value(immute_domain) 反查得到
    """

    def __init__(self, is_edit: bool):
        self.is_edit = is_edit
        super().__init__(actions=None, resource_meta=None, instance_ids_getter=self.instance_cluster_getter)

    def instance_cluster_getter(self, request, view):
        from backend.db_meta.models import Cluster

        immute_domain = get_request_key_id(request, key="level_value")
        cluster = Cluster.objects.get(immute_domain=immute_domain)
        db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
        action_id = f"{db_type.upper()}_DBCONFIG_EDIT" if self.is_edit else f"{db_type.upper()}_VIEW"
        self.actions = [getattr(ActionEnum, action_id)]
        self.resource_meta = ResourceEnum.cluster_type_to_resource_meta(cluster.cluster_type)
        return [cluster.id]


class BizSettingsPermission(ResourceActionPermission):
    """
    业务配置相关鉴权
    """

    config_action_map = {
        BizSettingsEnum.BIZ_ASSISTANCE_VARS: ActionEnum.BIZ_ASSISTANCE_VARS_CONFIG,
        BizSettingsEnum.NOTIFY_CONFIG: ActionEnum.BIZ_NOTIFY_CONFIG,
        BizSettingsEnum.BIZ_ASSISTANCE_SWITCH: ActionEnum.BIZ_ASSISTANCE_VARS_CONFIG,
    }

    def inst_ids_getter(self, request, view):
        action = self.config_action_map.get(request.data["key"])
        self.actions = [action] if action else []
        self.resource_meta = ResourceEnum.BUSINESS
        return [request.data["bk_biz_id"]]

    def __init__(self):
        super().__init__(actions=None, resource_meta=None, instance_ids_getter=self.inst_ids_getter)


class BizBatchSettingsPermission(BizSettingsPermission):
    """
    业务配置批量更新鉴权
    """

    def inst_ids_getter(self, request, view):
        actions = [
            self.config_action_map[s["key"]] for s in request.data["settings"] if s["key"] in self.config_action_map
        ]
        self.actions = list(set(actions))
        self.resource_meta = ResourceEnum.BUSINESS
        return [request.data["bk_biz_id"]]
