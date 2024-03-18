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
from typing import Dict, List

from django.db import transaction

from backend.db_meta.api import common
from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    SyncType,
)
from backend.db_meta.models import Cluster, StorageInstance, StorageInstanceTuple
from backend.flow.utils.redis.redis_module_operate import RedisCCTopoOperator

logger = logging.getLogger("flow")


@transaction.atomic
def redo_slaves(cluster: Cluster, tendisss: List[Dict], created_by: str = ""):
    """
    PRECHECK:
    1. 只允许1个master有且仅有1个slave(slave状态为running)
    DO:
    1. 修改新实例角色为slave,并且创建tuple关系
    2. 新实例加入到 集群表 (storageinstance_cluster)
    """

    logger.info("user request redo slaves cluster {} , link info {}".format(cluster.immute_domain, tendisss))
    ejector_objs, receiver_objs = precheck(cluster, tendisss)

    # 检查 ejecter 角色
    for ej_obj in ejector_objs:
        if ej_obj.instance_inner_role != InstanceInnerRole.MASTER:
            raise Exception("ejector {} is not master ,but {}".format(ej_obj, ej_obj.instance_inner_role))
        if ej_obj.as_ejector and ej_obj.as_ejector.first():
            slave = ej_obj.as_ejector.get().receiver
            if slave.status == InstanceStatus.RUNNING:
                raise Exception("master {} has slave {} which status is running.".format(ej_obj, slave))

    try:
        # 修改表 db_meta_storageinstance
        for rec_obj in receiver_objs:
            rec_obj.instance_role = InstanceRole.REDIS_SLAVE
            rec_obj.instance_inner_role = InstanceInnerRole.SLAVE
            rec_obj.save(update_fields=["instance_role", "instance_inner_role"])
            logger.info(
                "reset storageinstance role {}:{} {}".format(
                    rec_obj.machine.ip, rec_obj.port, InstanceRole.REDIS_SLAVE
                )
            )

        # 修改表 db_meta_storageinstancetuple ,## 这个时候会出现一主多从 ！
        for ms_pair in tendisss:
            ejector_obj = StorageInstance.objects.get(
                machine__ip=ms_pair["ejector"]["ip"], port=ms_pair["ejector"]["port"]
            )
            receiver_obj = StorageInstance.objects.get(
                machine__ip=ms_pair["receiver"]["ip"], port=ms_pair["receiver"]["port"]
            )
            StorageInstanceTuple.objects.create(ejector=ejector_obj, receiver=receiver_obj, creator=created_by)
            logger.info("create link info {} -> {}".format(ejector_obj, receiver_obj))
        # 修改表 db_meta_storageinstance_cluster
        cluster.storageinstance_set.add(*receiver_objs)

        # 更新 nodes. 域名对应的 cluster_entry信息
        cluster_entry = cluster.clusterentry_set.filter(role=ClusterEntryRole.NODE_ENTRY.value).first()
        if cluster_entry and cluster_entry.entry.startswith("nodes."):
            cluster_entry.storageinstance_set.add(*receiver_objs)

        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(receiver_objs)
        logger.info("cluster {} add storageinstance {}".format(cluster.immute_domain, receiver_objs))
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def make_sync(cluster: Cluster, tendisss: List[Dict]):
    """这一步 新的实例会添加到集群 关联关系表中"""
    logger.info("user request make sync , cluster {} ,{}".format(cluster.immute_domain, tendisss))

    ejector_objs, receiver_objs = precheck(cluster, tendisss)

    new_recevers_objs = []
    # 检查 receiver_objs 必须是 master ； 且必须有slave
    for receiver_obj in receiver_objs:
        if receiver_obj.instance_inner_role != InstanceInnerRole.MASTER:
            raise Exception(
                "make sync require : receiver {} mast be master ,but {}".format(
                    receiver_obj, receiver_obj.instance_inner_role
                )
            )
        new_recever_obj = receiver_obj.as_ejector.get().receiver
        if not new_recever_obj:
            raise Exception("make sync require : {} does not has slave [?] ".format(receiver_obj))
        new_recevers_objs.append(new_recever_obj)
    try:
        # 修改表 db_meta_storageinstance_cluster ; (仅仅为了DBHA能获取密码！)
        cluster.storageinstance_set.add(*receiver_objs)
        logger.info("cluster {} add storageinstance {}".format(cluster.immute_domain, receiver_objs))

        # 修改表 db_meta_storageinstance_cluster ; (仅仅为了DBHA能获取密码！)
        cluster.storageinstance_set.add(*new_recevers_objs)
        logger.info("cluster {} add storageinstance {}".format(cluster.immute_domain, new_recevers_objs))
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def make_sync_msms(cluster: Cluster, tendisss: List[Dict]):
    """
    TendisCache 建立Sync 关系为： M1->S1->M2->S2
    所以：
    0. 输入 S1,M2
    1. 修改 S1、M2 角色为 repeter
    2. 创建 tuple关系 S1->M2
    3. 新实例 M2,S2 加入到 集群表 (storageinstance_cluster) ##考虑到密码获取方式
    """
    return make_sync(cluster, tendisss, SyncType.SMS)


@transaction.atomic
def make_sync_mms(cluster: Cluster, tendisss: List[Dict]):
    """
    TendisPlus 建立Sync 关系为： M1->M2->S2
    所以：
    0. 输入 M1,M2
    1. 新实例 M2,S2 加入到 集群表 (storageinstance_cluster) ##考虑到密码获取方式
    """
    return make_sync(cluster, tendisss, SyncType.MMS)


@transaction.atomic
def switch_tendis(cluster: Cluster, tendisss: List[Dict], switch_type: str = SyncType.MMS.value):
    """
    TendisCache 建立Sync 关系为： M1->S1->M2->S2
    TendisPlus 建立Sync 关系为：  M1->M2->S2
    所以：
    输入： M1 ; M2
    0. (这里不做)检查同步状态 --> 需要切换前检查同步信息
    1. 修改 db_meta_storagesetdtl 把 M1 改成 M2
    2. 修改 db_meta_proxyinstance_storageinstance
    3. 如果sync 时修改了角色，需要改回去
    """
    logger.info("user request switch msms , cluster {} , link info {}".format(cluster.immute_domain, tendisss))
    old_ejector_objs, new_ejector_objs = precheck(cluster, tendisss)

    bad_ejc_obj = old_ejector_objs.filter(status=InstanceInnerRole.SLAVE).first()
    if bad_ejc_obj:
        raise Exception("some old ejector role not master {}".format(bad_ejc_obj))

    bad_ejc_obj = new_ejector_objs.filter(status=InstanceInnerRole.SLAVE).first()
    if bad_ejc_obj:
        raise Exception("some new ejector role not master {}".format(bad_ejc_obj))
    try:
        # 执行切换，修改元数据
        for ms_pair in tendisss:
            old_ejector_obj = StorageInstance.objects.get(
                machine__ip=ms_pair["ejector"]["ip"], port=ms_pair["ejector"]["port"]
            )
            tmp_proxy_objs = list(old_ejector_obj.proxyinstance_set.all())
            logger.info(
                "clean cluster {} proxys {} link with storage {}".format(cluster, tmp_proxy_objs, old_ejector_obj)
            )
            old_ejector_obj.proxyinstance_set.clear()

            new_ejector_obj = StorageInstance.objects.get(
                machine__ip=ms_pair["receiver"]["ip"], port=ms_pair["receiver"]["port"]
            )
            logger.info(
                "add cluster {} proxys {} link with storage {}".format(cluster, tmp_proxy_objs, new_ejector_obj)
            )
            new_ejector_obj.proxyinstance_set.add(*tmp_proxy_objs)

            if cluster.cluster_type in [
                ClusterType.TendisTwemproxyRedisInstance,
                ClusterType.TwemproxyTendisSSDInstance,
                ClusterType.TendisTwemproxyTendisplusIns,
            ]:
                logger.info(
                    "change cluster {} setdtl master from {} to {}".format(cluster, old_ejector_obj, new_ejector_obj)
                )
                cluster.nosqlstoragesetdtl_set.filter(instance=old_ejector_obj).update(instance=new_ejector_obj)
        # 给新实例创建服务实例
        ejector_objs, receiver_objs = [], []
        for ms_pair in tendisss:
            new_ejector_obj = StorageInstance.objects.get(
                machine__ip=ms_pair["receiver"]["ip"], port=ms_pair["receiver"]["port"]
            )
            if switch_type != SyncType.MS.value:
                logger.info("switch for sync {} need move cc module & add cc instance".format(switch_type))
                new_receiver_obj = new_ejector_obj.as_ejector.get().receiver
                ejector_objs.append(new_ejector_obj)
                receiver_objs.append(new_receiver_obj)
            else:
                logger.info(
                    "switch for sync {} need update role info {} 2 master".format(switch_type, ms_pair["receiver"])
                )
                new_ejector_obj.instance_role = InstanceRole.REDIS_MASTER.value
                new_ejector_obj.instance_inner_role = InstanceInnerRole.MASTER.value
                new_ejector_obj.save(update_fields=["instance_role", "instance_inner_role"])

        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(ejector_objs)
        RedisCCTopoOperator(cluster).transfer_instances_to_cluster_module(receiver_objs)
    except Exception as e:  # NOCC:broad-except(检查工具误报)
        logger.error(traceback.format_exc())
        raise e


def precheck(cluster: Cluster, tendisss: List[Dict]):
    """_summary_
        需检查，输入的第一个实例 属于本集群
    Args:
        cluster  (Cluster):    models.Cluster
        tendisss (List[Dict]): [{"ejector":{},"":{receiver}}]

    Raises:
        Exception: 实例不存在
        Exception: 第一位实例不属于集群

    Returns:
        _type_: QuerySet, QuerySet
    """
    ejectors, receivers = [], []
    for tendis in tendisss:
        ejectors.append(tendis["ejector"])
        receivers.append(tendis["receiver"])
    ejector_objs = common.filter_out_instance_obj(ejectors, StorageInstance.objects.all())
    receiver_objs = common.filter_out_instance_obj(receivers, StorageInstance.objects.all())

    none_obj = common.not_exists(ejectors, ejector_objs)
    if none_obj:
        raise Exception("some ejectors {} does not exists".format(none_obj))

    none_obj = common.not_exists(receivers, receiver_objs)
    if none_obj:
        raise Exception("some receivers {} does not exists".format(none_obj))

    # 需检查，输入的第一个实例 属于本集群
    cluster_storage_objs = common.filter_out_instance_obj(ejectors, cluster.storageinstance_set.all())
    none_obj = common.not_exists(ejectors, cluster_storage_objs)
    if none_obj:
        raise Exception("some ejectors {} does not exists in cluster".format(none_obj))

    return ejector_objs, receiver_objs
