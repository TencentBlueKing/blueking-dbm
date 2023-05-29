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

from django.db import transaction

from backend.db_meta.enums import InstanceRoleInstanceInnerRoleMap, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def switch_storage(cluster_id: int, target_storage_ip: str, origin_storage_ip: str, role: str = None):
    """
    集群主从成对迁移切换场景的元数据写入
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_storage_port = StorageInstance.objects.filter(cluster=cluster).all()[0].port
    target_storage = StorageInstance.objects.get(
        machine__ip=target_storage_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    origin_storage = StorageInstance.objects.get(
        machine__ip=origin_storage_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    cluster.storageinstance_set.remove(origin_storage)
    target_storage.status = InstanceStatus.RUNNING.value
    if role:
        target_storage.instance_role = role
        target_storage.instance_inner_role = InstanceRoleInstanceInnerRoleMap[role].value
    target_storage.save()


def change_proxy_storage_entry(cluster_id: int, master_ip: str, new_master_ip: str):
    cluster = Cluster.objects.get(id=cluster_id)
    master_storage = cluster.storageinstance_set.get(machine__ip=master_ip)
    new_master_storage = cluster.storageinstance_set.get(machine__ip=new_master_ip)
    proxy_list = master_storage.proxyinstance_set.all()
    for proxy in proxy_list:
        proxy.storageinstance.remove(master_storage)
        proxy.storageinstance.add(new_master_storage)


def change_storage_cluster_entry(cluster_id: int, slave_ip: str, new_slave_ip: str):
    cluster = Cluster.objects.get(id=cluster_id)
    slave_storage = cluster.storageinstance_set.get(machine__ip=slave_ip)
    new_slave_storage = cluster.storageinstance_set.get(machine__ip=new_slave_ip)
    slave_bind_entry = slave_storage.bind_entry.get()
    slave_bind_entry.storageinstance_set.remove(slave_storage)
    slave_bind_entry.storageinstance_set.add(new_slave_storage)
