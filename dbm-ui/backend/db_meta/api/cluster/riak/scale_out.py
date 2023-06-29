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
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.utils.riak.riak_module_operate import transfer_host_in_cluster_module

logger = logging.getLogger("root")


@transaction.atomic
def scale_out(
    cluster_id: int,
    storages: Optional[List] = None,
):
    """
    扩容 riak 集群 DBMeta
    """

    cluster = Cluster.objects.get(id=cluster_id)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)
    cluster_entry.storageinstance_set.add(*storage_objs)
    cluster.save()
    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = cluster.db_module_id
        m.db_module_id = cluster.db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    # 主机转移模块、添加对应的服务实例
    machine_type = MachineType.RIAK.value
    ip_set = set([ins.machine.ip for ins in storage_objs.filter(machine__machine_type=machine_type)])
    if ip_set:
        transfer_host_in_cluster_module(
            cluster_id=cluster.id,
            ip_list=list(ip_set),
            machine_type=machine_type,
            bk_cloud_id=cluster.bk_cloud_id,
        )
    return True
