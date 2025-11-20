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
import traceback
from typing import Dict, List, Optional

from django.db import transaction

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.nosqlcomm.create_instances import create_mongo_mutil_instances
from backend.db_meta.api.cluster.nosqlcomm.precheck import create_storage_precheck
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("flow")


@transaction.atomic
def cluster_add_shard(
    bk_biz_id: int,
    cluster_id: int,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    machine_specs: Optional[Dict] = None,
    cluster_type=ClusterType.MongoShardedCluster.value,
):
    """创建副本集 MongoSet 实例
    2. 可能需要支持多个 Secondary 节点

    Args:
        storages: [{"shard":"S1","nodes":[{"ip":,"port":,"role":},{},{}]},]
        machine_specs:{"mongodb":{"spec_id":0,"spec_config":""}}
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)

    # 空实例检查
    all_instances = []
    for storage in storages:
        all_instances.extend(storage["nodes"])

    # 实例创建，逻辑上主从关系创建
    machine_specs = machine_specs or {}
    create_mongo_mutil_instances(bk_biz_id, bk_cloud_id, MachineType.MONGODB.value, storages, machine_specs)

    all_storages, primaries = [], []
    for storage in storages:
        all_storages.extend(storage["nodes"])
        for shard in storage["nodes"]:
            if shard["role"] == InstanceRole.MONGO_M1:
                primaries.append({"ip": shard["ip"], "port": shard["port"], "shard": storage["shard"]})
    # 校验实例是否存在
    storage_objs = create_storage_precheck(all_storages)

    # 把新增分片加入到集群
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        cluster.storageinstance_set.add(*storage_objs)
        # 修改集群
        update_cluster_type(storage_objs, cluster_type)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongocluster add shard failed {}".format(e))

    # 写入shard分片规则
    mongos_objs = cluster.proxyinstance_set.all()
    for primary in primaries:
        primary_obj = StorageInstance.objects.get(
            machine__ip=primary["ip"], port=primary["port"], machine__bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id
        )
        cluster.nosqlstoragesetdtl_set.create(
            instance=primary_obj,
            bk_biz_id=bk_biz_id,
            seg_range=primary["shard"],
            creator=creator,
        )
        # 设置接入层后端,兼容DBHA接口
        primary_obj.proxyinstance_set.add(*mongos_objs)
    # 挪模块
    MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(storage_objs)
