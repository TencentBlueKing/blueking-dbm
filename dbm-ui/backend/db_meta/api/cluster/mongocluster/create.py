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
from backend.db_meta.api.cluster.nosqlcomm.create_instances import create_mongo_mutil_instances, create_proxies
from backend.db_meta.api.cluster.nosqlcomm.precheck import (
    before_create_domain_precheck,
    before_create_proxy_precheck,
    before_create_storage_precheck,
    create_domain_precheck,
    create_proxies_precheck,
    create_storage_precheck,
)
from backend.db_meta.enums import ClusterEntryType, ClusterPhase, ClusterStatus, ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("flow")


@transaction.atomic
def create_mongo_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    proxies: Optional[List] = None,
    configs: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.MongoShardedCluster.value,
):
    """创建副本集 MongoSet 实例
    1. 一般情况需要2到3个域名
    2. 可能需要支持多个 Secondary 节点

    Args:
        immute_domain (str): _description_
        proxies: [{},{}]
        configes: [{"shard":"S1","nodes":[{"ip":,"port":,"role":},{},{}]},{},{}]
        storages: [{"shard":"S1","nodes":[{"ip":,"port":,"role":},{},{}]},]
    """

    all_storages, all_confies, primaries = [], [], []
    for storage in storages:
        all_storages.extend(storage["nodes"])
        for shard in storage["nodes"]:
            if shard["role"] == InstanceRole.MONGO_M1:
                primaries.append({"ip": shard["ip"], "port": shard["port"], "shard": storage["shard"]})
    for config in configs:
        all_confies.extend(config["nodes"])
        for shard in config["nodes"]:
            if shard["role"] == InstanceRole.MONGO_M1:
                primaries.append({"ip": shard["ip"], "port": shard["port"], "shard": config["shard"]})

    create_domain_precheck(bk_biz_id=bk_biz_id, name=name, immute_domain=immute_domain, cluster_type=cluster_type)
    storage_objs = create_storage_precheck(all_storages)
    config_objs = create_storage_precheck(all_confies)
    mongos_objs = create_proxies_precheck(proxies)

    # 创建集群, 添加存储和接入实例
    try:
        cluster = Cluster.objects.create(
            bk_biz_id=bk_biz_id,
            name=name,
            alias=alias,
            major_version=major_version,
            db_module_id=db_module_id,
            immute_domain=immute_domain,
            creator=creator,
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
            updater=creator,
            cluster_type=cluster_type,
            bk_cloud_id=bk_cloud_id,
            region=region,
        )
        cluster.proxyinstance_set.add(*mongos_objs)
        cluster.storageinstance_set.add(*config_objs)
        cluster.storageinstance_set.add(*storage_objs)
        cluster.save()

        update_cluster_type(mongos_objs, cluster_type)
        update_cluster_type(config_objs, cluster_type)
        update_cluster_type(storage_objs, cluster_type)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongocluster create failed {}".format(e))

    # 写入shard分片规则
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

    # 注册访问入口
    try:
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
        )
        cluster_entry.proxyinstance_set.add(*mongos_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongocluster add dns entry failed {}".format(e))

    cc_topo_operator = MongoDBCCTopoOperator(cluster)
    cc_topo_operator.transfer_instances_to_cluster_module(mongos_objs)
    cc_topo_operator.transfer_instances_to_cluster_module(config_objs)
    cc_topo_operator.transfer_instances_to_cluster_module(storage_objs)


@transaction.atomic
def pkg_create_mongo_cluster(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    proxies: Optional[List] = None,
    configs: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    machine_specs: Optional[Dict] = None,
    cluster_type=ClusterType.MongoShardedCluster.value,
):
    """创建副本集 MongoSet 实例
    1. 一般情况需要2到3个域名
    2. 可能需要支持多个 Secondary 节点

    Args:
        immute_domain (str): _description_
        proxies: [{},{}]
        configes: [{},{},{}]
        storages: [{"shard":"S1","nodes":[{"ip":,"port":,"role":},{},{}]},]
        machine_specs:{"mongos":{"spec_id":0,"spec_config":""},"mongo_config":{"spec_id":0,"spec_config":""}}
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_storage_list(proxies, allow_empty=False, allow_null=False)

    # 空实例检查
    before_create_domain_precheck([immute_domain])
    before_create_proxy_precheck(proxies)
    all_instances = []
    for storage in storages:
        all_instances.extend(storage["nodes"])
    for config in configs:
        all_instances.extend(config["nodes"])
    request_validator.validated_storage_list(all_instances, allow_empty=False, allow_null=False)
    before_create_storage_precheck(all_instances)

    # 实例创建，关系创建
    machine_specs = machine_specs or {}
    spec_id, spec_config = 0, {}
    if machine_specs.get(MachineType.MONGOS.value):
        spec_id = machine_specs[MachineType.MONGOS.value]["spec_id"]
        spec_config = machine_specs[MachineType.MONGOS.value]["spec_config"]
    create_proxies(bk_biz_id, bk_cloud_id, MachineType.MONGOS.value, proxies, spec_id, spec_config)

    create_mongo_mutil_instances(bk_biz_id, bk_cloud_id, MachineType.MONOG_CONFIG.value, configs, machine_specs)
    create_mongo_mutil_instances(bk_biz_id, bk_cloud_id, MachineType.MONGODB.value, storages, machine_specs)

    create_mongo_cluster(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        proxies=proxies,
        configs=configs,
        storages=storages,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        region=region,
        cluster_type=cluster_type,
    )
