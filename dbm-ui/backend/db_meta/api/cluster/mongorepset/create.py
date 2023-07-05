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
from backend.db_meta.api.cluster.nosqlcomm.cc_ops import cc_add_instances
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_cluster_type
from backend.db_meta.api.cluster.nosqlcomm.create_instances import create_mongo_instances
from backend.db_meta.api.cluster.nosqlcomm.precheck import (
    before_create_domain_precheck,
    before_create_storage_precheck,
    create_domain_precheck,
    create_storage_precheck,
)
from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    DBCCModule,
    InstanceRole,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance

logger = logging.getLogger("flow")


@transaction.atomic
def pkg_create_mongoset(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    spec_id: int = 0,
    spec_config: str = "",
    cluster_type=ClusterType.MongoReplicaSet.value,
):
    """
    这里打包从头开始创建一个 MongoSet
    包括 machine、storage、tuple、cluster、cluster_entry等

    storages (_type_): _description_
        [{"ip":,"port":,"role":,"domain":},{},{}]
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    domains = []
    for storage in storages:
        domain = request_validator.validated_domain(storage["domain"])
        domains.append(domain)
        if storage["role"] == InstanceRole.MONGO_M1:
            if domain != immute_domain:
                raise Exception("input domain not match {} <> {}:{}".format(immute_domain, storage["ip"], domain))
    before_create_domain_precheck(domains)
    before_create_storage_precheck(storages)

    create_mongo_instances(bk_biz_id, bk_cloud_id, MachineType.MONGODB.value, storages, spec_id, spec_config)
    create_mongoset(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        storages=storages,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        region=region,
        cluster_type=cluster_type,
    )


@transaction.atomic
def create_mongoset(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    alias: str = "",
    major_version: str = "",
    storages: Optional[List] = None,
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.MongoReplicaSet.value,
):
    """创建副本集 MongoSet 实例
    1. 一般情况需要2到3个域名
    2. 可能需要支持多个 Secondary 节点

    Args:
        immute_domain (str): _description_
        storages (Optional[List], optional): => _description_
         [{"role":"mongo_m1","ip":"xx","port":20000,"domain":""},
          {"role":"mongo_m2","ip":"xx","port":20000,"domain":""},
          {"role":"mongo_m3","ip":"xx","port":20000,"domain":""},
          {"role":"mongo_backup","ip":"xx","port":20000,"domain":""}]
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    for storage in storages:
        domain = request_validator.validated_domain(storage["domain"])
        if storage["role"] == InstanceRole.MONGO_M1:
            if domain != immute_domain:
                raise Exception("input domain not match {} <> {}:{}".format(immute_domain, storage["ip"], domain))

    create_domain_precheck(bk_biz_id=bk_biz_id, name=name, immute_domain=immute_domain, cluster_type=cluster_type)
    storage_objs = create_storage_precheck(storages)
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
        cluster.storageinstance_set.add(*storage_objs)
        cluster.save()

        update_cluster_type(storage_objs, cluster_type)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongoset create failed {}".format(e))

    # 注册访问入口
    try:
        for storage in storages:
            cluster_entry = ClusterEntry.objects.create(
                cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=storage["domain"], creator=creator
            )
            cluster_entry.storageinstance_set.add(
                StorageInstance.objects.get(machine__ip=storage["ip"], port=storage["port"])
            )
            cluster_entry.save()
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise Exception("mongoset add dns entry failed {}".format(e))

    cc_add_instances(cluster, storage_objs, DBCCModule.MONGODB.value)
