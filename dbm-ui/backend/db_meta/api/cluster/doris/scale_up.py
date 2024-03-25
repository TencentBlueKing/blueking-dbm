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
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.utils.doris.doris_module_operate import DorisCCTopoOperator

logger = logging.getLogger("root")


@transaction.atomic
def scale_up(
    cluster_id: int,
    storages: Optional[List] = None,
):
    """
    Doris集群扩容注册DBMeta
    """

    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)

    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)

    # 关联cluster
    cluster.save()

    # 关联对应的域名信息
    all_observers = cluster.storageinstance_set.filter(instance_role=InstanceRole.DORIS_OBSERVER)
    all_followers = cluster.storageinstance_set.filter(instance_role=InstanceRole.DORIS_FOLLOWER)

    if all_observers.exists():
        for instance in all_observers:
            if not instance.bind_entry.exists():
                cluster_entry.storageinstance_set.add(instance)
        for instance in cluster_entry.storageinstance_set.all():
            if instance not in all_observers:
                instance.bind_entry.remove(cluster_entry)
    else:
        for instance in all_followers:
            if not instance.bind_entry.exists():
                cluster_entry.storageinstance_set.add(instance)
        for instance in cluster_entry.storageinstance_set.all():
            if instance not in all_followers:
                instance.bind_entry.remove(cluster_entry)

    cluster_entry.save()

    for ins in common.filter_out_instance_obj(storages, StorageInstance.objects.all()):
        m = ins.machine
        ins.db_module_id = cluster.db_module_id
        m.db_module_id = cluster.db_module_id
        ins.save()
        m.save()

    # 生成域名模块、es主机转移模块、添加对应的服务实例
    DorisCCTopoOperator(cluster).transfer_instances_to_cluster_module(storage_objs)
