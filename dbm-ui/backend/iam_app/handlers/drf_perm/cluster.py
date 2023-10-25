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
from backend.db_meta.models import Cluster, StorageInstance
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission


class ClusterDetailPermission(ResourceActionPermission):
    """
    集群详情相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从获取到集群ID后，决定动作和资源类型
        cluster_id = self.get_key_id(request, view, key="cluster_id")
        cluster = Cluster.objects.get(id=cluster_id)
        self.actions = [ActionEnum.cluster_type_to_view(cluster.cluster_type)]
        self.resource_meta = ResourceEnum.cluster_type_to_resource_meta(cluster.cluster_type)
        return [cluster_id]


class InstanceDetailPermission(ResourceActionPermission):
    """
    实例详情相关动作鉴权
    """

    def __init__(self, actions: List[ActionMeta] = None, resource_meta: ResourceMeta = None):
        super().__init__(actions=actions, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从获取到实例后，决定动作和资源类型
        instance_id = self.get_key_id(request, view, key="instance_id")
        if not instance_id:
            ip, port = self.get_key_id(request, view, key="instance_address").split(":")
            instance = StorageInstance.objects.get(machine__ip=ip, port=port)
        else:
            instance = StorageInstance.objects.get(id=instance_id)
        self.actions = [ActionEnum.instance_type_to_instance_action(instance.instance_role)]
        self.resource_meta = ResourceEnum.instance_type_to_resource_meta(instance.instance_role)
        return [instance.id]


class PartitionManagePermission(ResourceActionPermission):
    """
    分区管理相关动作鉴权
    """

    def __init__(self):
        resource_meta = ResourceEnum.BUSINESS
        super().__init__(actions=None, resource_meta=resource_meta, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从获取到业务ID和集群类型后，决定动作和资源类型
        convert = ClusterType.cluster_type_to_db_type
        if view.action in ["create", "update"]:
            cluster = Cluster.objects.get(id=request.data["cluster_id"])
            bk_biz_id, db_type = cluster.bk_biz_id, convert(cluster.cluster_type)
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_{view.action.upper()}")]
            return [bk_biz_id]

        elif view.action in ["enable", "disable", "batch_delete"]:
            db_type, bk_biz_id = convert(request.data["cluster_type"]), request.data["bk_biz_id"]
            if view.action == "batch_delete":
                self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_DELETE")]
            else:
                self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_ENABLE_DISABLE")]
            return [bk_biz_id]

        elif view.action in ["dry_run", "execute_partition"]:
            cluster = Cluster.objects.get(id=request.data["cluster_id"])
            db_type = convert(cluster.cluster_type)
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION")]
            self.resource_meta = getattr(ResourceEnum, f"{db_type.upper()}")
            return [cluster.id]
