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
import functools
import operator
from typing import List

from django.db.models import Q

from backend.components.mysql_partition.client import DBPartitionApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.handlers.drf_perm.base import MoreResourceActionPermission, ResourceActionPermission


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
        if view.action == "get_password":
            self.actions = [ActionEnum.cluster_type_to_action(cluster.cluster_type, action_key="ACCESS_ENTRY_VIEW")]
        else:
            self.actions = [ActionEnum.cluster_type_to_action(cluster.cluster_type, action_key="VIEW")]
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
        super().__init__(actions=None, resource_meta=None, instance_ids_getter=self.instance_ids_getter)

    def instance_ids_getter(self, request, view):
        # 从获取到业务ID和集群类型后，决定动作和资源类型
        convert = ClusterType.cluster_type_to_db_type
        if view.action in ["create", "update"]:
            cluster = Cluster.objects.get(id=request.data["cluster_id"])
            bk_biz_id, db_type = cluster.bk_biz_id, convert(cluster.cluster_type)
            self.resource_meta = ResourceEnum.BUSINESS
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_{view.action.upper()}")]
            return [bk_biz_id]

        elif view.action in ["enable", "disable", "batch_delete"]:
            db_type = convert(request.data["cluster_type"])
            params = {"limit": len(request.data["ids"]), "offset": 0, **request.data}
            partition_data = DBPartitionApi.query_conf(params=params)["items"]
            cluster_ids = [data["cluster_id"] for data in partition_data]
            if view.action == "batch_delete":
                self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_DELETE")]
            else:
                self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION_ENABLE_DISABLE")]
            self.resource_meta = getattr(ResourceEnum, f"{db_type.upper()}")
            return list(set(cluster_ids))

        elif view.action in ["dry_run", "execute_partition", "query_log"]:
            if view.action == "query_log":
                config_id, cluster_type = int(request.query_params["config_id"]), request.query_params["cluster_type"]
                params = {"limit": 1, "offset": 0, "ids": [config_id], "cluster_type": cluster_type}
                cluster_id = DBPartitionApi.query_conf(params=params)["items"][0]["cluster_id"]
            else:
                cluster_id = request.data["cluster_id"]
            cluster = Cluster.objects.get(id=cluster_id)
            db_type = convert(cluster.cluster_type)
            self.actions = [getattr(ActionEnum, f"{db_type.upper()}_PARTITION")]
            self.resource_meta = getattr(ResourceEnum, f"{db_type.upper()}")
            return [cluster.id]


class ModifyClusterPasswordPermission(ResourceActionPermission):
    """
    集群admin密码修改相关动作鉴权
    """

    def inst_ids_getter(self, request, view):
        data = request.data or request.query_params
        instance_list = data["instance_list"]
        # 获取实例关联的machine(这里不查询实例是因为存在spider角色)
        machine_ip_filters = functools.reduce(
            operator.or_, [Q(bk_cloud_id=inst["bk_cloud_id"], ip=inst["ip"]) for inst in instance_list]
        )
        machines = Machine.objects.filter(machine_ip_filters)
        # 根据集群类型获得关联实例和动作
        db_type = ClusterType.cluster_type_to_db_type(machines.first().cluster_type)
        self.actions = [getattr(ActionEnum, f"{db_type}_admin_pwd_modify".upper())]
        self.resource_meta = getattr(ResourceEnum, db_type.upper())
        # 通过machine获取关联集群，用于鉴权
        cluster_id_tuples = list(machines.values("storageinstance__cluster", "proxyinstance__cluster"))
        cluster_ids = set([v for item in cluster_id_tuples for v in item.values() if isinstance(v, int)])
        return cluster_ids

    def __init__(self):
        super().__init__(actions=None, resource_meta=None, instance_ids_getter=self.inst_ids_getter)


class QueryClusterPasswordPermission(MoreResourceActionPermission):
    @staticmethod
    def instance_ids_getters(request, view):
        data = request.data or request.query_params
        # 目前仅支持mysql的admin密码查询鉴权
        if view.action == "query_mysql_admin_password":
            if "bk_biz_id" in data:
                return [(data["bk_biz_id"], DBType.MySQL.value)]
            elif "instances" in data:
                instance = data["instances"].split(",")[0]
                bk_cloud_id, ip, __ = instance.split(":")
                machine = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
                return [(machine.bk_biz_id, ClusterType.cluster_type_to_db_type(machine.cluster_type))]
            else:
                raise NotImplementedError
        else:
            return []

    def __init__(self):
        super().__init__(
            actions=[ActionEnum.ADMIN_PWD_VIEW],
            resource_metes=[ResourceEnum.BUSINESS, ResourceEnum.DBTYPE],
            instance_ids_getters=self.instance_ids_getters,
        )
