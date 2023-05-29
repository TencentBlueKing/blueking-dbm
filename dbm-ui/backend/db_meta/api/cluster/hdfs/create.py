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
from django.utils.translation import ugettext_lazy as _

from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance

logger = logging.getLogger("root")


@transaction.atomic
def create_precheck(bk_biz_id: int, name: str, immute_domain: str, db_module_id: int):
    precheck_errors = []
    # bk_biz_id, db_module_id, name 唯一性检查
    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, name=name, cluster_type=ClusterType.Hdfs.value, db_module_id=db_module_id
    ).exists():
        precheck_errors.append(_("集群名 {} 在 bk_biz_id:{} db_module_id:{} 已存在").format(name, bk_biz_id, db_module_id))

    if precheck_errors:
        raise DBMetaException(message=", ".join(precheck_errors))


@transaction.atomic
def create(
    bk_cloud_id: int,
    bk_biz_id: int,
    name: str,
    alias: str,
    immute_domain: str,
    major_version: str,
    db_module_id: int,
    storages: Optional[List] = None,
    creator: str = "",
) -> int:
    """
    注册 HDFS 集群
    """

    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)

    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())

    # 创建集群, 添加存储和接入实例
    cluster = Cluster.objects.create(
        bk_biz_id=bk_biz_id,
        name=name,
        alias=alias,
        immute_domain=immute_domain,
        major_version=major_version,
        cluster_type=ClusterType.Hdfs,
        db_module_id=db_module_id,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
    )

    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
    )
    entry_instances = common.filter_out_instance_obj(
        storages, StorageInstance.objects.filter(instance_role=InstanceRole.HDFS_DATA_NODE)
    )
    if entry_instances.exists():
        cluster_entry.storageinstance_set.add(*entry_instances)
    cluster_entry.save()

    cluster.storageinstance_set.add(*storage_objs)
    cluster.save()
    for storage_instance in storage_objs:
        machine = storage_instance.machine
        storage_instance.db_module_id = db_module_id
        machine.db_module_id = db_module_id
        storage_instance.save()
        machine.save()

    return cluster.id
