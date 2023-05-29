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

from backend import env
from backend.components import CCApi
from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def replace(
    cluster_id: int,
    del_storages: Optional[List] = None,
    add_storages: Optional[List] = None,
):
    """
    替换 HDFS 集群 DBMeta
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)
    add_storages = request_validator.validated_storage_list(add_storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(add_storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)
    for storage_instance in storage_objs:
        machine = storage_instance.machine
        storage_instance.db_module_id = cluster.db_module_id
        machine.db_module_id = cluster.db_module_id
        storage_instance.save()
        machine.save()
        # 新DN需要加入entry
        if storage_instance.instance_role == InstanceRole.HDFS_DATA_NODE.value:
            cluster_entry.storageinstance_set.add(storage_instance)

    del_storages = request_validator.validated_storage_list(del_storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(del_storages, StorageInstance.objects.all())
    for storage in storage_objs:
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():
            # 将机器挪到 待回收模块
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
            )
            storage.machine.delete(keep_parents=True)
    cluster.storageinstance_set.remove(*storage_objs)
    cluster.save()
    cluster_entry.storageinstance_set.remove(*storage_objs)
    cluster_entry.save()
