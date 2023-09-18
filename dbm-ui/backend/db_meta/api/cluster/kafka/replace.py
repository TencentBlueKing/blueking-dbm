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
from django.utils.translation import ugettext as _

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
    old_storages: Optional[List] = None,
    new_storages: Optional[List] = None,
):
    """
    集群扩容注册DBMeta
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)

    # 增加
    new_storages = request_validator.validated_storage_list(new_storages, allow_empty=False, allow_null=False)
    new_storage_objs = common.filter_out_instance_obj(new_storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*new_storage_objs)

    # 删除
    old_storages = request_validator.validated_storage_list(old_storages, allow_empty=False, allow_null=False)
    old_storage_objs = common.filter_out_instance_obj(old_storages, StorageInstance.objects.all())
    for storage in old_storage_objs:
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():
            # 将主机转移到待回收模块下
            logger.info(_("将主机{}转移到待回收").format(storage.machine.ip))
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
            )
            storage.machine.delete(keep_parents=True)
    cluster.storageinstance_set.remove(*old_storage_objs)

    cluster.save()

    # 关联对应的域名信息
    broker = cluster.storageinstance_set.filter(instance_role=InstanceRole.BROKER)
    for instance in broker:
        if not instance.bind_entry.exists():
            cluster_entry.storageinstance_set.add(instance)
    cluster_entry.storageinstance_set.remove(*old_storage_objs)
    cluster_entry.save()

    for ins in common.filter_out_instance_obj(new_storages, StorageInstance.objects.all()):
        machine = ins.machine
        ins.db_module_id = cluster.db_module_id
        machine.db_module_id = cluster.db_module_id
        ins.save()
        machine.save()
