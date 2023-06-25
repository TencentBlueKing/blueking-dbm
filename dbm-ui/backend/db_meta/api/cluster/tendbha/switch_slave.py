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

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def switch_slave(cluster_id: int, target_slave_ip: str, source_slave_ip: str, slave_domain: str):
    """
    集群替换slave场景元数据注册方式
    这里集群调用暂时只支持tendb-ha架构
    """

    # for cluster_id in cluster_ids:
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_storage_port = StorageInstance.objects.filter(cluster=cluster).all()[0].port
    target_storage_obj = StorageInstance.objects.get(
        machine__ip=target_slave_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    source_storage_obj = StorageInstance.objects.get(
        machine__ip=source_slave_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    # target实例需要继承source实例的is_standby特性
    target_storage_obj.is_stand_by = source_storage_obj.is_stand_by
    target_storage_obj.status = InstanceStatus.RUNNING.value
    target_storage_obj.save()

    cluster_entry = cluster.clusterentry_set.get(entry=slave_domain)
    cluster_entry.storageinstance_set.remove(source_storage_obj)
    cluster_entry.storageinstance_set.add(target_storage_obj)
    # cluster.storageinstance_set.remove(*source_storage_objs)
    # cluster.storageinstance_set.add(*target_storage_objs)


@transaction.atomic
def add_slave(cluster_id: int, target_slave_ip: str):
    """
    集群添加slave
    """
    # for cluster_id in cluster_ids:
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_storage_port = StorageInstance.objects.filter(cluster=cluster).all()[0].port
    target_storage_objs = StorageInstance.objects.filter(
        machine__ip=target_slave_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    cluster.storageinstance_set.add(*target_storage_objs)


@transaction.atomic
def remove_slave(cluster_id: int, target_slave_ip: str):
    """
    集群删除slave
    """
    # for cluster_id in cluster_ids:
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_storage_port = StorageInstance.objects.filter(cluster=cluster).all()[0].port
    target_storage_objs = StorageInstance.objects.filter(
        machine__ip=target_slave_ip, port=cluster_storage_port, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    cluster.storageinstance_set.remove(*target_storage_objs)
