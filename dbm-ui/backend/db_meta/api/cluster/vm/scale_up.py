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
from typing import List, Optional

from django.db import transaction

from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums.cluster_entry_role import ClusterEntryRole
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.utils.vm.vm_module_operate import VmCCTopoOperator

logger = logging.getLogger("root")


@transaction.atomic
def scale_up(
    cluster_id: int,
    storages: Optional[List] = None,
):
    """
    扩容 vm 集群 注册DBMeta
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster, role=ClusterEntryRole.MASTER_ENTRY)
    slave_entry = ClusterEntry.objects.get(cluster=cluster, role=ClusterEntryRole.SLAVE_ENTRY)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)
    cluster.save()

    # 域名信息处理
    vminserts = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.VM_INSERT)
    for instance in vminserts:
        if not instance.bind_entry.exists():
            cluster_entry.storageinstance_set.add(instance)
    cluster_entry.save()

    vmselects = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.VM_SELECT)
    for instance in vmselects:
        if not instance.bind_entry.exists():
            slave_entry.storageinstance_set.add(instance)
    slave_entry.save()

    for storage_instance in storage_objs:
        machine = storage_instance.machine
        storage_instance.db_module_id = cluster.db_module_id
        machine.db_module_id = cluster.db_module_id
        storage_instance.save()
        machine.save()

    # vm主机转移模块、添加对应的服务实例
    VmCCTopoOperator(cluster).transfer_instances_to_cluster_module(storage_objs)
