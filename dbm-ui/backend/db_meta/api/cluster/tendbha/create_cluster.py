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
from django.utils.translation import ungettext as _

from backend.db_meta import request_validator
from backend.db_meta.api import common
from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
)
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance, StorageInstance, StorageInstanceTuple

logger = logging.getLogger("root")


@transaction.atomic
def create_precheck(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    slave_domain: Optional[str] = None,
):
    """
    流程未执行不知道 ip, 也没有实例
    所以只做 name, 域名的唯一性检查
    """
    precheck_errors = []

    # bk_biz_id, db_module_id, name 唯一性检查
    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, name=name, cluster_type=ClusterType.TenDBHA.value, db_module_id=db_module_id
    ).exists():
        precheck_errors.append(_("集群名 {} 在 bk_biz_id:{} db_module_id:{} 已存在").format(name, bk_biz_id, db_module_id))

    # 域名唯一性检查
    if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=immute_domain).exists():
        precheck_errors.append(_("域名 {} 已存在").format(immute_domain))

    if slave_domain:
        if ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value, entry=slave_domain).exists():
            precheck_errors.append(_("域名 {} 已存在").format(immute_domain))

    if precheck_errors:
        raise DBMetaException(message=", ".join(precheck_errors))


@transaction.atomic
def create(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    major_version: str,
    db_module_id: int,
    bk_cloud_id: int,
    time_zone: str,
    region: str,
    slave_domain: Optional[str] = None,
    proxies: Optional[List] = None,
    storages: Optional[List] = None,
    creator: str = "",
) -> Cluster:
    """
    注册 TenDBHA 集群
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)

    if slave_domain:
        slave_domain = request_validator.validated_domain(slave_domain)

    proxy_objs = common.filter_out_instance_obj(proxies, ProxyInstance.objects.all())
    storage_objs = common.filter_out_instance_obj(storages, StorageInstance.objects.all())
    master_storage_obj = storage_objs.get(instance_inner_role=InstanceInnerRole.MASTER)
    slave_storage_objs = storage_objs.filter(instance_inner_role=InstanceInnerRole.SLAVE)

    # 创建集群, 添加存储和接入实例

    cluster = Cluster.objects.create(
        bk_biz_id=bk_biz_id,
        name=name,
        cluster_type=ClusterType.TenDBHA.value,
        db_module_id=db_module_id,
        immute_domain=immute_domain,
        creator=creator,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        bk_cloud_id=bk_cloud_id,
        time_zone=time_zone,
        major_version=major_version,
        region=region,
    )
    cluster.proxyinstance_set.add(*proxy_objs)
    cluster.storageinstance_set.add(*storage_objs)

    # 设置接入层后端
    master_storage_obj.proxyinstance_set.add(*proxy_objs)

    # 设置同步关系
    for slave_storage_obj in slave_storage_objs:
        StorageInstanceTuple.objects.create(ejector=master_storage_obj, receiver=slave_storage_obj)

    cluster_entry = ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
    )
    cluster_entry.proxyinstance_set.add(*proxy_objs)

    if slave_domain:
        cluster_slave_entry = ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS,
            entry=slave_domain,
            creator=creator,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        )
        cluster_slave_entry.storageinstance_set.add(*slave_storage_objs)

    # 直到这里才有明确的 db module
    for ins in proxy_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    for ins in storage_objs:
        m = ins.machine
        ins.db_module_id = db_module_id
        m.db_module_id = db_module_id
        ins.save(update_fields=["db_module_id"])
        m.save(update_fields=["db_module_id"])

    return cluster


@transaction.atomic
def cluster_add_storage(cluster_list: List):
    for one_cluster in cluster_list:
        storage = StorageInstance.objects.get(machine__ip=one_cluster["ip"], port=one_cluster["port"])
        cluster = Cluster.objects.get(id=one_cluster["cluster_id"])
        cluster.storageinstance_set.add(storage)


@transaction.atomic
def cluster_remove_storage(cluster_id: int, ip: str, port: int):
    cluster = Cluster.objects.get(id=cluster_id)
    storage = StorageInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=cluster.bk_cloud_id)
    cluster.storageinstance_set.remove(storage)
