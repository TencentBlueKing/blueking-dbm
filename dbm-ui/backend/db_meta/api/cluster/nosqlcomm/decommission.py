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
from collections import defaultdict
from typing import Dict, List

from django.db import transaction
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.api import common
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceStatus
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


@transaction.atomic
def decommission_proxies(cluster: Cluster, proxies: List[Dict], is_all: bool = False):
    """
    1. 支持集群中部分proxy 下架 (故障、裁撤、替换等场景)
    2. 支持整个集群proxy下架 (但需要有检查) (集群下架场景)

    要求：
    1. 默认不允许全部下架,只允许下架一部分
    2. 集群整体下架时,   允许下架所有proxy实例
    3. 非集群整体下架时,不允许下架所有proxy实例
    """
    logger.info("user request decmmission proxies {} {}".format(cluster.immute_domain, proxies))
    try:
        proxy_objs = common.filter_out_instance_obj(proxies, cluster.proxyinstance_set.all())
        _t = common.not_exists(proxies, proxy_objs)
        if _t:
            raise Exception(_("{} 存在不是本集群的实例下架列表").format(_t))

        remain_objs = common.remain_instance_obj(proxies, cluster.proxyinstance_set.all())
        if not is_all and not remain_objs:
            raise Exception(_("非集群下架模式,不允许直接下架所有实例 {}"), remain_objs)

        machine_obj = defaultdict(dict)
        cc_manage = CcManage(cluster.bk_biz_id)
        cc_manage.delete_service_instance(bk_instance_ids=[obj.bk_instance_id for obj in proxy_objs])
        for proxy_obj in proxy_objs:
            logger.info("cluster proxy {} for cluster {}".format(proxy_obj, cluster.immute_domain))
            cluster.proxyinstance_set.remove(proxy_obj)

            logger.info(
                "proxy storage {} for {} storageinstance {}".format(
                    proxy_obj, cluster.immute_domain, proxy_obj.storageinstance.all()
                )
            )
            proxy_obj.storageinstance.clear()

            logger.info(
                "proxy bind {} for {} cluster_bind_entry {}".format(
                    proxy_obj, cluster.immute_domain, proxy_obj.bind_entry.all()
                )
            )
            proxy_obj.bind_entry.clear()

            logger.info("proxy instance {} ".format(proxy_obj))
            proxy_obj.delete()

            machine_obj[proxy_obj.machine.ip] = proxy_obj.machine

            # 需要检查， 是否该机器上所有实例都已经清理干净，
            if ProxyInstance.objects.filter(machine__ip=proxy_obj.machine.ip).exists():
                logger.info("ignore storage machine {} , another instance existed.".format(proxy_obj.machine))
            else:
                logger.info("proxy machine {}".format(proxy_obj.machine))
                cc_manage.recycle_host([proxy_obj.machine.bk_host_id])
                proxy_obj.machine.delete()
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def decommission_backends(cluster: Cluster, backends: List[Dict], is_all: bool = False):
    """
    1. 扩缩容替换场景
    2. 裁撤替换场景
    3. 故障自愈场景
    4. 集群下架场景

    要求：
        1. 如果是下架集群， 必须先下架proxy,然后再下架 backends
        2. 不允许直接下架RUNNING状态实例
    """
    logger.info("user request decmmission backends {} {}".format(cluster.immute_domain, backends))
    cc_manage = CcManage(cluster.bk_biz_id)
    try:
        storage_objs = common.filter_out_instance_obj(backends, cluster.storageinstance_set.all())
        _t = common.not_exists(backends, storage_objs)
        if _t:
            raise Exception("{} not match".format(_t))

        running_obj = storage_objs.filter(status=InstanceStatus.RUNNING).first()
        if not is_all and running_obj:
            raise Exception(_("非集群下架单,不允许直接下架状态为RUNNING状态实例 {}"), running_obj)

        cc_manage.delete_service_instance(bk_instance_ids=[obj.bk_instance_id for obj in storage_objs])
        machines = []
        for storage_obj in storage_objs:
            logger.info("cluster storage instance {} for cluster {}".format(storage_obj, cluster.immute_domain))
            cluster.storageinstance_set.remove(storage_obj)

            machines.append(storage_obj.machine)
            logger.info("remove storage instance {} ".format(storage_obj))
            storage_obj.delete()

        # 需要检查， 是否该机器上所有实例都已经清理干净，
        for machine in machines:
            if StorageInstance.objects.filter(machine__ip=machine.ip).exists():
                logger.info("ignore storage machine {} , another instance existed.".format(machine))
            else:
                logger.info("storage machine {} ".format(machine))
                cc_manage.recycle_host([machine.bk_host_id])
                machine.delete()
    except Exception as e:
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def decommission_cluster(cluster: Cluster):
    logger.info("user request decmmission cluster {}".format(cluster.immute_domain))

    try:
        if cluster.cluster_type not in (ClusterType.MongoReplicaSet.value):
            proxies = [
                {"ip": proxy_obj.machine.ip, "port": proxy_obj.port} for proxy_obj in cluster.proxyinstance_set.all()
            ]
            decommission_proxies(cluster, proxies, True)

        storages = [
            {"ip": storage_obj.machine.ip, "port": storage_obj.port}
            for storage_obj in cluster.storageinstance_set.all()
        ]
        decommission_backends(cluster, storages, True)

        for cluster_entry_obj in cluster.clusterentry_set.all():
            logger.info("cluster entry {} for cluster {}".format(cluster_entry_obj, cluster.immute_domain))
            cluster_entry_obj.delete()

        logger.info("cluster {}".format(cluster.__dict__))
        db_type = DBType.Redis.value
        if cluster.cluster_type in (ClusterType.MongoReplicaSet.value, ClusterType.MongoShardedCluster.value):
            db_type = DBType.MongoDB.value
        CcManage(cluster.bk_biz_id).delete_cluster_modules(db_type=db_type, cluster=cluster)
        cluster.delete()

    except Exception as e:
        logger.error(traceback.format_exc())
        raise e


@transaction.atomic
def decommission_instances(ip: str, bk_cloud_id: int, ports: List) -> bool:
    """
    #### Redis/Proxy 实例下架
    #### 主机转移
    TODO (安全性检查)
    {"ip":"","ports":[]}
    """

    machine_obj = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    keep_machine = False
    if machine_obj.access_layer == AccessLayer.PROXY:
        logger.info(" proxyInstance {}:{}".format(ip, ports))
        ProxyInstance.objects.filter(machine=machine_obj, port__in=ports).delete()
        if ProxyInstance.objects.filter(machine=machine_obj).exists():
            keep_machine = True
            logger.info("ignore proxy machine {} , another instance existed.".format(ip))

    elif machine_obj.access_layer in [AccessLayer.STORAGE, AccessLayer.CONFIG]:
        logger.info(" storageInstance {}:{}".format(ip, ports))
        StorageInstance.objects.filter(machine=machine_obj, port__in=ports).delete()
        if StorageInstance.objects.filter(machine=machine_obj).exists():
            keep_machine = True
            logger.info("ignore stroage machine {} , another instance existed.".format(ip))

    if not keep_machine:
        logger.info(" machine {}".format(ip))
        CcManage(machine_obj.bk_biz_id).recycle_host([machine_obj.bk_host_id])
        machine_obj.delete()

    return True
