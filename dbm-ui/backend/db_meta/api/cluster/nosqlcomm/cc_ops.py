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
from dataclasses import asdict

from django.db import transaction
from django.db.models import QuerySet

from backend import env
from backend.components import CCApi
from backend.constants import CommonInstanceLabels
from backend.db_meta.api.common import add_service_instance
from backend.db_meta.api.db_module import get_or_create
from backend.db_meta.enums import AccessLayer, ClusterTypeMachineTypeDefine
from backend.db_meta.models import AppCache, Cluster, ClusterMonitorTopo, Machine
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


def cc_add_instance(cluster: Cluster, instance: object, module_name: str):
    cc_transfer_host(cluster, instance)
    cc_add_service_instance(cluster, instance, module_name)


def cc_add_instances(cluster: Cluster, instances: QuerySet, module_name: str):
    machines = {}
    for instance in instances:
        if not machines.get(instance.machine.ip):
            logger.info("transfer cc module for instance {}".format(instance))
            cc_transfer_host(cluster, instance)
        machines[instance.machine.ip] = instance
        cc_add_service_instance(cluster, instance, module_name)


def cc_add_service_instances(cluster: Cluster, instances: QuerySet, module_name: str):
    """兼容了 Storage/Proxy

    Args:
        cluster_obj (Cluster): _description_
        instances (QuerySet): _description_
    """
    for instance in instances:
        cc_add_service_instance(cluster, instance, module_name)


def cc_transfer_hosts(cluster: Cluster, instances: QuerySet, module_name: str):
    for instance in instances:
        cc_add_service_instance(cluster, instance, module_name)


@transaction.atomic
def cc_add_service_instance(cluster: Cluster, instance: object, module_name: str):
    """
    3. 新增服务实例
    4. 添加服务实例标签
    """
    machine_obj = instance.machine

    # 3. 新增服务实例 & 添加服务实例标签
    instance_role = instance.instance_role if instance.access_layer == AccessLayer.STORAGE else AccessLayer.PROXY.value

    bk_module_id = ClusterMonitorTopo.objects.get(
        cluster_id=cluster.id, bk_biz_id=cluster.bk_biz_id, machine_type=instance.machine.machine_type
    ).bk_module_id

    bk_instance_id = add_service_instance(
        bk_module_id=bk_module_id,
        bk_host_id=machine_obj.bk_host_id,
        listen_ip=machine_obj.ip,
        listen_port=instance.port,
        func_name=module_name,  # redis
        labels_dict=asdict(
            CommonInstanceLabels(
                app=AppCache.get_app_attr(cluster.bk_biz_id, default=cluster.bk_biz_id),
                app_id=str(cluster.bk_biz_id),
                app_name=AppCache.get_app_attr(cluster.bk_biz_id, "db_app_abbr", cluster.bk_biz_id),
                bk_biz_id=str(cluster.bk_biz_id),
                bk_cloud_id=str(cluster.bk_cloud_id),
                cluster_domain=cluster.immute_domain,
                cluster_name=cluster.name,
                cluster_type=cluster.cluster_type,
                instance_role=instance_role,
                instance_host=machine_obj.ip,
                instance=f"{machine_obj.ip}-{instance.port}",
            )
        ),
    )
    logger.info("added cc service instance for instance bk_instance_id:{}:{}".format(bk_instance_id, instance))
    instance.bk_instance_id = bk_instance_id
    instance.save(update_fields=["bk_instance_id"])


@transaction.atomic
def cc_transfer_host(cluster: Cluster, instance: object):
    """1. 创建主机模块
        2. 转移主机到模块

    Args:
        cluster (Cluster): _description_
        instance (object): _description_
    """
    # 更新DBMeta和创建cc目录，这里如果已经存在，则会报错
    get_or_create(
        **{
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_id": cluster.id,
            "cluster_type": cluster.cluster_type,
            "cluster_domain": cluster.immute_domain,
        }
    )

    bk_module_id = ClusterMonitorTopo.objects.get(
        cluster_id=cluster.id, bk_biz_id=cluster.bk_biz_id, machine_type=instance.machine.machine_type
    ).bk_module_id
    logger.info("transfer host with info : ip:{}, bkmoduleid:{}".format(instance.machine.ip, bk_module_id))
    CcManage.transfer_machines(
        bk_biz_id=cluster.bk_biz_id,
        ip_modules=[{"ips": [instance.machine.ip], "bk_module_id": bk_module_id}],
        bk_cloud_id=cluster.bk_cloud_id,
    )


@transaction.atomic
def cc_del_service_instances(instances: QuerySet):
    # 这里因为id不存在会导致接口异常退出，这里暂时接收所有错误，不让它直接退出
    bk_instances = [instance.bk_instance_id for instance in instances]
    ret = CCApi.delete_service_instance(
        {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "service_instance_ids": bk_instances,
        }
    )
    logger.info("del bk service instances {} result {}".format(instances, ret))


@transaction.atomic
def cc_transfer_idle(machine: Machine):
    ret = CCApi.transfer_host_to_recyclemodule(
        {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": [machine.bk_host_id]}
    )
    logger.info("transfer hosts to recycle module {} result {}".format(machine.ip, ret))


@transaction.atomic
def cc_del_module(cluster: Cluster):
    for machine_type in ClusterTypeMachineTypeDefine[cluster.cluster_type]:
        cluster_monitor_topo = ClusterMonitorTopo.objects.get(
            cluster_id=cluster.id, bk_biz_id=cluster.bk_biz_id, machine_type=machine_type
        )
        # .删除 cc 模块
        ret = CCApi.delete_module(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_set_id": cluster_monitor_topo.bk_set_id,
                "bk_module_id": cluster_monitor_topo.bk_module_id,
            }
        )
        logger.info("delete cc module for cluster {} {} result {}".format(cluster, cluster_monitor_topo, ret))
        cluster_monitor_topo.delete()
