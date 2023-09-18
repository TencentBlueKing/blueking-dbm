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
from django.db.models import Q

from backend import env
from backend.components import CCApi
from backend.db_meta import request_validator
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, ClusterMonitorTopo, StorageInstance
from backend.flow.consts import InstanceFuncAliasEnum
from backend.flow.utils.es.es_module_operate import init_instance_service

logger = logging.getLogger("root")


@transaction.atomic
def shrink(
    cluster_id: int,
    storages: Optional[List] = None,
):
    """
    清理DBMeta
    """
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    queries = Q()
    for storage in storages:
        queries |= Q(**{"machine__ip": storage["ip"]})
    storage_objs = StorageInstance.objects.filter(cluster_type=ClusterType.Es.value).filter(queries)

    for storage in storage_objs.all():
        storage.delete(keep_parents=True)
        if not storage.machine.storageinstance_set.exists():
            # 这个 api 不需要检查返回值, 转移主机到待回收模块，转移模块这里会把服务实例删除
            CCApi.transfer_host_to_recyclemodule(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [storage.machine.bk_host_id]}
            )
            storage.machine.delete(keep_parents=True)

    # 修正entry到instance的关系
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster)

    if not cluster_entry.storageinstance_set.exists():
        all_client_nodes = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_CLIENT.value)
        all_hot_datanodes = StorageInstance.objects.filter(
            cluster=cluster, instance_role=InstanceRole.ES_DATANODE_HOT.value
        )
        all_cold_datanodes = StorageInstance.objects.filter(
            cluster=cluster, instance_role=InstanceRole.ES_DATANODE_COLD.value
        )
        all_master_nodes = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER.value)
        if all_client_nodes.exists():
            for instance in all_client_nodes:
                cluster_entry.storageinstance_set.add(instance)
        elif all_hot_datanodes.exists():
            for instance in all_hot_datanodes:
                cluster_entry.storageinstance_set.add(instance)
        elif all_cold_datanodes.exists():
            for instance in all_cold_datanodes:
                cluster_entry.storageinstance_set.add(instance)
        else:
            for instance in all_master_nodes:
                cluster_entry.storageinstance_set.add(instance)

    # 判断服务实例是否还存在，不存在则安装
    service_instance = StorageInstance.objects.filter(cluster=cluster).exclude(bk_instance_id=0)
    if not service_instance.exists():
        # 写入监控信息
        bk_module_id = ClusterMonitorTopo.objects.get(
            bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id, machine_type=MachineType.ES_DATANODE.value
        ).bk_module_id
        instance = StorageInstance.objects.filter(
            cluster=cluster, machine__machine_type=MachineType.ES_DATANODE.value
        ).first()
        init_instance_service(
            cluster=cluster,
            ins=instance,
            bk_module_id=bk_module_id,
            instance_role=instance.instance_role,
            func_name=InstanceFuncAliasEnum.ES_FUNC_ALIAS.value,
        )
