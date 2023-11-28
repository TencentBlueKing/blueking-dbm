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
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType
from backend.db_report.models import MetaCheckReport

logger = logging.getLogger("root")


def check_redis_instance():
    _check_redis_instance()


def _check_redis_instance():
    """
    孤立实例检查 （孤立的proxy小于2个proxy，孤立的master，孤立的slave）
     ALONE_PROXY
     ALONE_MASTER
     ALONE_SLAVE

    实例状态异常检查， （不属于RUNNING状态）
     STATUS_ABNORMAL

    """

    # 构建查询条件:tendisplus,ssd,cache 三种类型一起检查,巡检0点发起
    query = (
        Q(cluster_type=ClusterType.TendisPredixyTendisplusCluster)
        | Q(cluster_type=ClusterType.TwemproxyTendisSSDInstance)
        | Q(cluster_type=ClusterType.TendisTwemproxyRedisInstance)
    )
    # 遍历集群
    for c in Cluster.objects.filter(query):
        logger.info("+===+++++===  start check {} db meta  +++++===++++ ".format(c.immute_domain))
        logger.info("+===+++++===  cluster type is: {} +++++===++++ ".format(c.cluster_type))
        # proxy节点数不能小于2
        if c.proxyinstance_set.count() < 2:
            msg = _("集群 {} proxy numbers 小于2, only  {}").format(c.immute_domain, c.proxyinstance_set.count())
            MetaCheckReport.objects.create(
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                ip="none",
                cluster=c.immute_domain,
                cluster_type=c.cluster_type,
                status=False,
                msg=msg,
                subtype=MetaCheckSubType.AloneInstance.value,
            )

        # 检查master对应的slave是否缺失
        master_slave_map, slave_master_map = defaultdict(), defaultdict()
        for master_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            try:
                slave_obj = master_obj.as_ejector.get().receiver
            except ObjectDoesNotExist:
                logger.error("Error occurred while getting slave_obj")
                msg = _("集群{}的master：{} 获取slave失败").format(c.immute_domain, master_obj)
                create_meta_alone_report(c, master_obj, msg)
                raise NotImplementedError(_("集群{}的master{}get slave_obj failed".format(c.immute_domain, master_obj)))

            # 集群不支持一个主多个从架构
            ifslave = master_slave_map.get(master_obj.machine.ip)
            if ifslave and ifslave != slave_obj.machine.ip:
                msg = _("unsupport mutil slave with cluster {} 4:{}".format(c.immute_domain, master_obj.machine.ip))
                create_meta_alone_report(c, master_obj, msg)
                raise Exception(
                    "unsupport mutil slave with cluster {} 4:{}".format(c.immute_domain, master_obj.machine.ip)
                )
            else:
                master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip
            # 没获取到对应端口
            if master_obj.port != slave_obj.port:
                msg = _("集群{}的master实例：{} 没有slave").format(c.immute_domain, master_obj)
                create_meta_alone_report(c, master_obj, msg)

        # 检查slave对应的master是否缺失
        for slave_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value):
            try:
                master_obj = slave_obj.as_receiver.get().ejector
            except ObjectDoesNotExist:
                logger.error("Error occurred while getting master_obj")
                msg = _("集群{}的slave：{} 获取master失败").format(c.immute_domain, slave_obj)
                create_meta_alone_report(c, slave_obj, msg)
                raise NotImplementedError(_("集群{}的slave{} get master_obj failed".format(c.immute_domain, slave_obj)))

            # 不支持一从多主
            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                msg = _("unsupport mutil master with cluster {} 4:{}".format(c.immute_domain, slave_obj.machine.ip))
                create_meta_alone_report(c, slave_obj, msg)
                raise Exception(
                    "unsupport mutil master for cluster {}:{}".format(c.immute_domain, slave_obj.machine.ip)
                )
            else:
                slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip
            # 没获取到对应端口
            if slave_obj.port != master_obj.port:
                msg = _("集群{}的slave实例：{} 没有master").format(c.immute_domain, slave_obj)
                create_meta_alone_report(c, slave_obj, msg)
        # 实例状态异常
        for instance_obj in c.storageinstance_set.filter():
            create_meta_statue_report(c, instance_obj)
        # proxy状态异常
        for instance_obj in c.proxyinstance_set.filter():
            create_meta_statue_report(c, instance_obj)


def create_meta_statue_report(c, instance_obj):
    """
    实例状态不为running的写入表中
    """
    if instance_obj.status != InstanceStatus.RUNNING:
        msg = _("集群{}的实例:{}实例状态异常:{}").format(c.immute_domain, instance_obj.ip_port, instance_obj.status)
        MetaCheckReport.objects.create(
            bk_biz_id=c.bk_biz_id,
            bk_cloud_id=c.bk_cloud_id,
            ip=instance_obj.machine.ip,
            port=instance_obj.port,
            cluster=c.immute_domain,
            cluster_type=c.cluster_type,
            status=False,
            msg=msg,
            subtype=MetaCheckSubType.StatusAbnormal.value,
        )


def create_meta_alone_report(c, instance_obj, msg):
    """
    孤立实例写入表中
    """
    MetaCheckReport.objects.create(
        bk_biz_id=c.bk_biz_id,
        bk_cloud_id=c.bk_cloud_id,
        ip=instance_obj.machine.ip,
        port=instance_obj.port,
        cluster=c.immute_domain,
        cluster_type=c.cluster_type,
        status=False,
        msg=msg,
        subtype=MetaCheckSubType.AloneInstance.value,
    )
