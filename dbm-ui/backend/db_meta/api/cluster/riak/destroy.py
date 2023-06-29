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

from backend import env
from backend.components import CCApi
from backend.configuration.constants import DBType
from backend.db_meta.api.db_module import delete_cluster_modules
from backend.db_meta.models import Cluster, ClusterEntry

logger = logging.getLogger("root")


@transaction.atomic
def destroy(cluster_id: int):
    """
    清理DBMeta
    """

    cluster = Cluster.objects.get(id=cluster_id)

    # 删除storage instance
    for storage in cluster.storageinstance_set.all():
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():
            # 这个 api 不需要检查返回值, 转移主机到待回收模块，转移模块这里会把服务实例删除
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
            )
            storage.machine.delete(keep_parents=True)

    # 删除entry
    for ce in ClusterEntry.objects.filter(cluster=cluster).all():
        ce.delete(keep_parents=True)

    # 删除cmdb中的模块
    delete_cluster_modules(db_type=DBType.Riak.value, del_cluster_id=cluster.id)

    # 删除集群
    cluster.delete(keep_parents=True)
