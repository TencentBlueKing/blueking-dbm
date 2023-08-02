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
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, ClusterMonitorTopo, StorageInstance
from backend.flow.consts import InstanceFuncAliasEnum
from backend.flow.utils.es.es_module_operate import EsCCTopoOperator

logger = logging.getLogger("root")


@transaction.atomic
def create(
    bk_cloud_id: int,
    bk_biz_id: int,
    name: str,
    alias: str,
    immute_domain: str,
    db_module_id: int,
    storages: Optional[List] = None,
    creator: str = "",
    major_version: str = "",
):
    """
    注册 ES 集群
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)

    # 创建集群, 添加存储和接入实例
    cluster = Cluster.objects.create(
        bk_biz_id=bk_biz_id,
        name=name,
        alias=alias,
        cluster_type=ClusterType.Es,
        db_module_id=db_module_id,
        immute_domain=immute_domain,
        creator=creator,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        major_version=major_version,
        bk_cloud_id=bk_cloud_id,
    )

    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
    )

    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    cluster.storageinstance_set.add(*storage_objs)

    cluster.save()

    clients = common.filter_out_instance_obj(
        storages, StorageInstance.objects.filter(instance_role=InstanceRole.ES_CLIENT)
    )
    datanodes_hot = common.filter_out_instance_obj(
        storages, StorageInstance.objects.filter(instance_role=InstanceRole.ES_DATANODE_HOT)
    )
    datanodes_cold = common.filter_out_instance_obj(
        storages, StorageInstance.objects.filter(instance_role=InstanceRole.ES_DATANODE_COLD)
    )
    masters = common.filter_out_instance_obj(
        storages, StorageInstance.objects.filter(instance_role=InstanceRole.ES_MASTER)
    )
    if clients.exists():
        cluster_entry.storageinstance_set.add(*clients)
    elif datanodes_hot.exists():
        cluster_entry.storageinstance_set.add(*datanodes_hot)
    elif datanodes_cold.exists():
        cluster_entry.storageinstance_set.add(*datanodes_cold)
    elif masters.exists():
        cluster_entry.storageinstance_set.add(*masters)
    else:
        logger.info("add entry failed, find 0 node")
        raise Exception("0 node found")
    cluster_entry.save()

    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save()
        m.save()

    # 生成域名模块、es主机转移模块、添加对应的服务实例
    EsCCTopoOperator(cluster).transfer_instances_to_cluster_module(storage_objs)
