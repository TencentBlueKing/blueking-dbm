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
from typing import List, Optional

from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta import request_validator
from backend.db_meta.api.cluster.nosqlcomm.cc_ops import cc_add_instance, cc_add_instances
from backend.db_meta.api.cluster.nosqlcomm.create_cluster import update_storage_cluster_type
from backend.db_meta.api.cluster.nosqlcomm.create_instances import create_tendis_instances
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
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance, StorageInstanceTuple

logger = logging.getLogger("flow")


@transaction.atomic
def pkg_create_single(
    bk_biz_id: int,
    name: str,
    db_module_id: int,
    immute_domain: str,
    slave_domain: Optional[str] = None,
    storages: Optional[List] = None,
    alias: str = "",
    major_version: str = "",
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.TendisRedisInstance.value,
):
    """一主一丛模式, Slave域名可选
    storages:[{"master":{"ip":"","port":""},"slave":{}}]
    """
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    checked_domains = [immute_domain]
    if slave_domain:
        slave_domain = request_validator.validated_domain(slave_domain)
        checked_domains.append(slave_domain)
        if not slave_domain.__contains__("-slave."):
            raise Exception("slave domain mast contain [-slave.] {}".format(slave_domain))
    if immute_domain.__contains__("-slave."):
        raise Exception("immute_domain mast not contain [-slave.] {}".format(immute_domain))
    all_instances = []
    for ins in storages:
        all_instances.append(ins["master"])
        all_instances.append(ins["slave"])
    request_validator.validated_storage_list(all_instances, allow_empty=False, allow_null=False)

    before_create_domain_precheck(checked_domains)
    before_create_storage_precheck(all_instances)

    create_tendis_instances(
        bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, machine_type=MachineType.TENDISCACHE.value, storages=storages
    )
    create_single(
        bk_biz_id=bk_biz_id,
        name=name,
        immute_domain=immute_domain,
        db_module_id=db_module_id,
        alias=alias,
        major_version=major_version,
        storages=storages,
        slave_domain=slave_domain,
        creator=creator,
        bk_cloud_id=bk_cloud_id,
        cluster_type=cluster_type,
        region=region,
    )


@transaction.atomic
def create_single(
    bk_biz_id: int,
    name: str,
    immute_domain: str,
    db_module_id: int,
    slave_domain: Optional[str] = None,
    storages: Optional[List] = None,
    alias: str = "",
    major_version: str = "",
    creator: str = "",
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID,
    region: str = "",
    cluster_type=ClusterType.TendisRedisInstance.value,
):
    """一主一丛模式, Slave域名可选"""
    bk_biz_id = request_validator.validated_integer(bk_biz_id)
    immute_domain = request_validator.validated_domain(immute_domain)
    db_module_id = request_validator.validated_integer(db_module_id)
    storages = request_validator.validated_storage_list(storages, allow_empty=False, allow_null=False)
    if slave_domain:
        slave_domain = request_validator.validated_domain(slave_domain)
        if not slave_domain.__contains__("-slave."):
            raise Exception("slave domain mast contain [-slave.] {}".format(slave_domain))
    if immute_domain.__contains__("-slave."):
        raise Exception("immute_domain mast not contain [-slave.] {}".format(immute_domain))

    create_domain_precheck(bk_biz_id=bk_biz_id, name=name, immute_domain=immute_domain, cluster_type=cluster_type)
    storage_objs = create_storage_precheck(storages=storages)
    # 创建单实例集群, 添加存储和接入实例
    try:
        master_obj = storage_objs.get(instance_inner_role=InstanceInnerRole.MASTER)
        slave_obj = master_obj.as_ejector.get().receiver

        cluster = Cluster.objects.create(
            bk_biz_id=bk_biz_id,
            name=name,
            alias=alias,
            major_version=major_version,
            db_module_id=db_module_id,
            immute_domain=immute_domain,
            creator=creator,
            cluster_type=cluster_type,
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
            updater=creator,
            bk_cloud_id=bk_cloud_id,
            region=region,
        )
        cluster.storageinstance_set.add(master_obj)
        cluster.storageinstance_set.add(slave_obj)

        update_storage_cluster_type(master_obj, cluster_type)

        # 这里看是否需要创建 slave 域名
        cluster_entry = ClusterEntry.objects.create(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=immute_domain, creator=creator
        )
        cluster_entry.storageinstance_set.add(master_obj)

        if slave_domain:
            cluster_entry = ClusterEntry.objects.create(
                cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, entry=slave_domain, creator=creator
            )
            cluster_entry.storageinstance_set.add(slave_obj)

    except IntegrityError as error:
        logger.warning("create single tendis cluster failed {} {}".format(storages, error))
        logger.error(traceback.format_exc())
        raise error

    # CC 诺模块，以及注册服务实例
    slave_objs = []
    for storage_obj in storage_objs:
        slave_obj = storage_obj.as_ejector.get().receiver
        slave_objs.append(slave_obj)
    cc_add_instances(cluster, slave_objs, DBCCModule.REDIS.value)
    cc_add_instances(cluster, storage_objs, DBCCModule.REDIS.value)


@transaction.atomic
def switch_2_slave(cluster: Cluster, params):
    """切换到slave 节点 m->s

    用途: 1.  切换到集群当前的 slave
         2.  切换到指定的 slave （已经建立好同步关系）
    裁撤 or 手动切换时用到, 后续需要用重建热备单据

    检测: slave 的状态 tuple 表

    修改项：
        1. 源master 状态 改为 Unavailable
        2. 目的slave 角色 改为master
        3. 关系表互换角色
        4. entry 入口指向
    """
    try:
        ejector_obj = switch_precheck(cluster, params)
        receiver_obj = StorageInstance.objects.filter(
            machine__ip=params["receiver"]["ip"],
            port=params["receiver"]["port"],
            instance_inner_role=InstanceInnerRole.SLAVE,
        ).get()

        ejector_obj.status = InstanceStatus.UNAVAILABLE
        ejector_obj.save(update_fields=["status"])

        receiver_obj.instance_role = InstanceRole.REDIS_MASTER
        receiver_obj.instance_inner_role = InstanceInnerRole.MASTER
        receiver_obj.save(update_fields=["instance_role", "instance_inner_role"])

        # 修改同步关系元数据
        StorageInstanceTuple.objects.filter(ejector=ejector_obj, receiver=receiver_obj).update(
            ejector=receiver_obj, receiver=ejector_obj
        )

        # 把master的域名元数据挪到 slave，slave上的域名不动
        for entry_obj in cluster.clusterentry_set.all():
            entry_obj.storageinstance_set.add(receiver_obj)
            entry_obj.storageinstance_set.remove(ejector_obj)
            logger.info("move entry {} from {} to {}".format(entry_obj, ejector_obj, receiver_obj))

    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def switch_2_pair(cluster: Cluster, params):
    """成对切换 m->s 切换到 m->s
    用途: 裁撤 or 扩缩容
    """
    try:
        ejector_obj = switch_precheck(cluster, params)
        receiver_obj = StorageInstance.objects.filter(
            machine__ip=params["receiver"]["ip"],
            port=params["receiver"]["port"],
            instance_inner_role=InstanceInnerRole.MASTER,
        ).get()
        if not receiver_obj.as_ejector.exists():
            raise Exception("expected slave for {}".format(params["receiver"]))

        new_slave_obj = receiver_obj.as_ejector.get().receiver

        old_slave_obj = ejector_obj.as_ejector.get().receiver
        ejector_obj.status = InstanceStatus.UNAVAILABLE
        old_slave_obj.status = InstanceStatus.UNAVAILABLE
        ejector_obj.save(update_fields=["status"])
        old_slave_obj.save(update_fields=["status"])

        receiver_obj.instance_inner_role = InstanceInnerRole.MASTER
        receiver_obj.save(update_fields=["instance_role", "instance_inner_role"])

        # 把master的域名元数据挪到 NewMaster，slave 的域名诺到NewSlave
        for entry_obj in cluster.clusterentry_set.all():
            entry_obj.storageinstance_set.add(receiver_obj)
            entry_obj.storageinstance_set.remove(ejector_obj)
            logger.info("move entry {} from {} to {}".format(entry_obj, ejector_obj, receiver_obj))
            if entry_obj.entry.__contains__("-slave."):
                entry_obj.storageinstance_set.add(new_slave_obj)
                entry_obj.storageinstance_set.remove(old_slave_obj)
                logger.info("move slave entry {} from {} to {}".format(entry_obj, new_slave_obj, old_slave_obj))
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


def switch_precheck(cluster, params):
    """
    检查:
        1. 实例存在性
        2. 源master 属于 cluster
    """
    # 检查 ，集群存在这个master节点
    if not cluster.storageinstance_set.filter(
        machine__ip=params["ejector"]["ip"],
        port=params["ejector"]["port"],
        instance_inner_role=InstanceInnerRole.MASTER,
    ).exists():
        raise Exception("switch from {} not master in cluster {}".format(params["ejector"], cluster))

    # 检查 ，集群存在这个slave节点 (mms,mss) (slave,REPEATER)
    if not cluster.storageinstance_set.filter(
        machine__ip=params["receiver"]["ip"], port=params["receiver"]["port"]
    ).exists():
        raise Exception("switch from {} not in cluster {}".format(params["receiver"], cluster))

    ejector_obj = StorageInstance.objects.filter(
        machine__ip=params["ejector"]["ip"],
        port=params["ejector"]["port"],
        instance_inner_role=InstanceInnerRole.MASTER,
    ).get()

    return ejector_obj


@transaction.atomic
def redo_slave(cluster: Cluster, params):
    """
    TODO待验证 !(这里还需要注意, 以前master故障的场景)!
    """
    # 检查 ，集群存在这个master节点
    if not cluster.storageinstance_set.filter(
        machine__ip=params["ejector"]["ip"],
        port=params["ejector"]["port"],
        instance_inner_role=InstanceInnerRole.MASTER,
    ).exists():
        raise Exception("for redo slave: {} not master in cluster {}".format(params["ejector"], cluster))

    if not StorageInstance.objects.filter(
        machine__ip=params["receiver"]["ip"], port=params["receiver"]["port"]
    ).exists():
        raise Exception("new receiver does not exist {}".format(params["receiver"]))
    # 只能有一个 Running 的slave
    ejector_obj = StorageInstance.objects.filter(
        machine__ip=params["ejector"]["ip"],
        port=params["ejector"]["port"],
        instance_inner_role=InstanceInnerRole.MASTER,
    ).get()
    old_slave_obj = ejector_obj.as_ejector.get().receiver
    if old_slave_obj.status == InstanceStatus.RUNNING:
        raise Exception("master {} has slave {} which status is running.".format(ejector_obj, old_slave_obj))

    try:
        new_receiver_obj = StorageInstance.objects.filter(
            machine__ip=params["receiver"]["ip"], port=params["receiver"]["port"]
        ).get()

        StorageInstanceTuple.objects.create(ejector=ejector_obj, receiver=new_receiver_obj)
        logger.info("add link info {} ==> {}".format(ejector_obj, new_receiver_obj))

        for entry_obj in cluster.clusterentry_set.all():
            # master 故障情况下，只能清理掉包含slave 的域名
            if entry_obj.entry.__contains__("-slave."):
                entry_obj.storageinstance_set.add(new_receiver_obj)
                logger.info("move entry {} from {} to {}".format(entry_obj, old_slave_obj, new_receiver_obj))
                entry_obj.storageinstance_set.remove(old_slave_obj)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e
