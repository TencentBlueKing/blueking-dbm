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
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def scale_in(
    cluster_id: int,
    storages: Optional[List] = None,
):
    """
    缩容 riak 集群 DBMeta
    """

    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)

    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    for storage in storage_objs:
        storage.delete(keep_parents=True)
        # 将机器挪到待回收模块, riak一台机器只有一个实例
        CCApi.transfer_host_to_recyclemodule(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
        )
        storage.machine.delete(keep_parents=True)

    cluster.storageinstance_set.remove(*storage_objs)
    cluster.save()
    cluster_entry.storageinstance_set.remove(*storage_objs)
    cluster_entry.save()
