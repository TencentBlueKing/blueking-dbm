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
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_report.enums import MetaCheckSubType, ReportStateType
from backend.ticket.constants import TICKET_RUNNING_STATUS_SET, TicketType
from backend.ticket.models.ticket import ClusterOperateRecord

from .base import create_meta_check_report, delete_old_meta_check_reports, is_cluster_labeled_with

logger = logging.getLogger("root")


def get_supported_clusters():
    return [
        ClusterType.TendisTwemproxyRedisInstance.value,  # TendisCache 集群
        ClusterType.TwemproxyTendisSSDInstance.value,  # TendisSSD 集群
        ClusterType.TendisPredixyRedisCluster.value,  # RedisCluster 集群
        ClusterType.TendisPredixyTendisplusCluster.value,  # Tendisplus 集群
        ClusterType.TendisRedisInstance.value,  # Redis 主从
    ]


def check_redis_instance():
    """
    孤立实例检查 （孤立的proxy小于2个proxy，孤立的master，孤立的slave）
     ALONE_PROXY
     ALONE_MASTER
     ALONE_SLAVE

    实例状态异常检查，需要排除掉(禁用、删除中 状态集群) （不属于RUNNING状态）
     STATUS_ABNORMAL
     REDIS_INSTANCE_CLOSE = TicketEnumField("REDIS_INSTANCE_CLOSE", _("Redis 主从禁用"), register_iam=False)
     REDIS_PROXY_CLOSE = TicketEnumField("REDIS_PROXY_CLOSE", _("Redis 集群禁用"), register_iam=False)
     REDIS_DESTROY = TicketEnumField("REDIS_DESTROY", _("Redis 集群删除"), _("集群管理"))
     REDIS_INSTANCE_PROXY_CLOSE = TicketEnumField("REDIS_INSTANCE_PROXY_CLOSE", _("Redis 主从集群禁用"), register_iam=False)
     REDIS_INSTANCE_DESTROY = TicketEnumField("REDIS_INSTANCE_DESTROY", _("Redis 主从集群删除"), _("集群管理"))
    """
    cluster_types = get_supported_clusters()

    delete_old_meta_check_reports(MetaCheckSubType.AloneInstance, cluster_types=cluster_types, days=30)
    delete_old_meta_check_reports(MetaCheckSubType.StatusAbnormal, cluster_types=cluster_types, days=30)

    # 遍历集群
    query = Q(cluster_type__in=cluster_types)
    for c in Cluster.objects.filter(query):
        logger.info("instance_check: start by {}".format(c))
        if check_ignore(c):
            continue

        # Get cluster's DBA
        dba_list = DBAdministrator.get_biz_db_type_admins(bk_biz_id=c.bk_biz_id, db_type=DBType.Redis.value)
        creator = dba_list[0] if dba_list else "admin"

        cluster_has_lonely_issue = False

        # proxy节点数不能小于2
        skip_proxy_count_check = c.cluster_type == ClusterType.TendisRedisInstance.value or is_cluster_labeled_with(
            c,
            {"directmode": "true"},
        )
        if not skip_proxy_count_check and c.proxyinstance_set.count() < 2:
            cluster_has_lonely_issue = True
            msg = _("cluster:{} now had proxies[{}] < 2").format(c.immute_domain, c.proxyinstance_set.count())
            create_meta_check_report(
                cluster=c,
                ip="none",
                port=None,
                subtype=MetaCheckSubType.AloneInstance,
                msg=msg,
                state=ReportStateType.ABNORMAL,
                creator=creator,
            )
        else:
            msg = _("cluster:{} proxy count check passed, proxies count: {}").format(
                c.immute_domain, c.proxyinstance_set.count()
            )
            logger.info(msg)

        # 检查master对应的slave是否缺失
        master_slave_map, slave_master_map = defaultdict(), defaultdict()
        for master_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            try:
                try:
                    slave_obj = master_obj.as_ejector.get().receiver
                except ObjectDoesNotExist:
                    cluster_has_lonely_issue = True
                    logger.warning(
                        "Warning: cluster {} master {} failed to get slave_obj".format(c.immute_domain, master_obj)
                    )
                    msg = _("集群{}的master：{} 获取slave失败").format(c.immute_domain, master_obj)
                    create_single_node_record(c, master_obj, msg, creator)
                    continue

                # 集群不支持一个主多个从架构
                ifslave = master_slave_map.get(master_obj.machine.ip)
                if ifslave and ifslave != slave_obj.machine.ip:
                    cluster_has_lonely_issue = True
                    logger.warning(
                        "Warning: cluster {} unsupport multiple slaves for master {}".format(
                            c.immute_domain, master_obj.machine.ip
                        )
                    )
                    msg = _(
                        "unsupport mutil slave with cluster {} 4:{}".format(c.immute_domain, master_obj.machine.ip)
                    )
                    create_single_node_record(c, master_obj, msg, creator)
                    continue

                else:
                    master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip
                # 没获取到对应端口
                if master_obj.port != slave_obj.port:
                    cluster_has_lonely_issue = True
                    msg = _("集群{}的master实例：{} 没有slave").format(c.immute_domain, master_obj)
                    create_single_node_record(c, master_obj, msg, creator)
                else:
                    # Master-slave relationship is normal
                    logger.info(_("集群{}的master实例：{} slave关系正常").format(c.immute_domain, master_obj))
            except Exception as e:
                cluster_has_lonely_issue = True
                logger.warning(
                    "Warning: unexpected error while checking master {} in cluster {}: {}".format(
                        master_obj, c.immute_domain, str(e)
                    )
                )
                msg = _("集群{}的master实例：{} 检查时发生异常: {}").format(c.immute_domain, master_obj, str(e))
                create_single_node_record(c, master_obj, msg, creator)
                continue

        # 检查slave对应的master是否缺失
        for slave_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value):
            try:
                try:
                    master_obj = slave_obj.as_receiver.get().ejector
                except ObjectDoesNotExist:
                    cluster_has_lonely_issue = True
                    logger.warning(
                        "Warning: cluster {} slave {} failed to get master_obj".format(c.immute_domain, slave_obj)
                    )
                    msg = _("集群{}的slave：{} 获取master失败").format(c.immute_domain, slave_obj)
                    create_single_node_record(c, slave_obj, msg, creator)
                    continue

                # 不支持一从多主
                ifmaster = slave_master_map.get(slave_obj.machine.ip)
                if ifmaster and ifmaster != master_obj.machine.ip:
                    cluster_has_lonely_issue = True
                    logger.warning(
                        "Warning: cluster {} unsupport multiple masters for slave {}".format(
                            c.immute_domain, slave_obj.machine.ip
                        )
                    )
                    msg = _(
                        "unsupport mutil master with cluster {} 4:{}".format(c.immute_domain, slave_obj.machine.ip)
                    )
                    create_single_node_record(c, slave_obj, msg, creator)
                    continue

                else:
                    slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip
                # 没获取到对应端口
                if slave_obj.port != master_obj.port:
                    cluster_has_lonely_issue = True
                    msg = _("集群{}的slave实例：{} 没有master").format(c.immute_domain, slave_obj)
                    create_single_node_record(c, slave_obj, msg, creator)
                else:
                    logger.info(_("集群{}的slave实例：{} master关系正常").format(c.immute_domain, slave_obj))
            except Exception as e:
                cluster_has_lonely_issue = True
                logger.warning(
                    "Warning: unexpected error while checking slave {} in cluster {}: {}".format(
                        slave_obj, c.immute_domain, str(e)
                    )
                )
                msg = _("集群{}的slave实例：{} 检查时发生异常: {}").format(c.immute_domain, slave_obj, str(e))
                create_single_node_record(c, slave_obj, msg, creator)
                continue

        # Check instance status abnormality
        cluster_has_status_issue = check_cluster_instance_status(c, creator)

        if not cluster_has_lonely_issue:
            create_cluster_normal_report(c, MetaCheckSubType.AloneInstance.value, creator)

        if not cluster_has_status_issue:
            create_cluster_normal_report(c, MetaCheckSubType.StatusAbnormal.value, creator)


def check_cluster_instance_status(cluster: Cluster, creator: str = "admin") -> bool:
    """Check all instances (storage and proxy) status in the cluster"""
    cluster_has_status_issue = False

    # Check storage instance status
    for instance_obj in cluster.storageinstance_set.filter():
        try:
            if not check_status_create_abnormal(cluster, instance_obj, creator):
                cluster_has_status_issue = True
        except Exception as e:
            cluster_has_status_issue = True
            logger.warning(
                "Warning: unexpected error while checking storage instance {} in cluster {}: {}".format(
                    instance_obj, cluster.immute_domain, str(e)
                )
            )

    # Check proxy instance status
    for instance_obj in cluster.proxyinstance_set.filter():
        try:
            if not check_status_create_abnormal(cluster, instance_obj, creator):
                cluster_has_status_issue = True
        except Exception as e:
            cluster_has_status_issue = True
            logger.warning(
                "Warning: unexpected error while checking proxy instance {} in cluster {}: {}".format(
                    instance_obj, cluster.immute_domain, str(e)
                )
            )

    return cluster_has_status_issue


def check_ignore(cluster) -> bool:
    if cluster.phase != ClusterPhase.ONLINE.value:
        logger.info(
            f"instance_check: will ignore cluster {cluster}, " f"cluster phase is {cluster.phase} (not online)"
        )
        return True
    ignore_tickets = [
        TicketType.REDIS_INSTANCE_CLOSE.value,
        TicketType.REDIS_PROXY_CLOSE.value,
        TicketType.REDIS_DESTROY.value,
        TicketType.REDIS_INSTANCE_CLOSE.value,
        TicketType.REDIS_INSTANCE_DESTROY.value,
    ]
    if ClusterOperateRecord.objects.filter(
        ticket__ticket_type__in=ignore_tickets,
        ticket__status__in=TICKET_RUNNING_STATUS_SET,
        cluster_id=cluster.id,
    ).exists():
        logger.info("instance_check: will ignore cluster {} , 4 it has destory label".format(cluster))
        return True
    return False


def check_status_create_abnormal(c, instance_obj, creator="admin"):
    """
    实例状态检查并插入异常报告
    Returns:
        bool: True if instance status is normal, False if abnormal
    """
    if instance_obj.status != InstanceStatus.RUNNING:
        msg = _("集群{}的实例:{}实例状态异常:{}").format(c.immute_domain, instance_obj.ip_port, instance_obj.status)
        create_meta_check_report(
            cluster=c,
            ip=instance_obj.machine.ip,
            port=instance_obj.port,
            subtype=MetaCheckSubType.StatusAbnormal,
            msg=msg,
            state=ReportStateType.ABNORMAL,
            machine_type=instance_obj.machine_type,
            creator=creator,
        )
        return False
    return True


def create_single_node_record(c, instance_obj, msg, creator="admin"):
    """
    孤立实例写入表中
    """
    create_meta_check_report(
        cluster=c,
        ip=instance_obj.machine.ip,
        port=instance_obj.port,
        subtype=MetaCheckSubType.AloneInstance,
        msg=msg,
        state=ReportStateType.ABNORMAL,
        machine_type=instance_obj.machine_type,
        creator=creator,
    )


def create_cluster_normal_report(c, report_type, creator="admin"):
    """
    集群级别正常检查报告
    当集群下所有实例检查都通过时，创建集群级别的正常报告
    """
    msg = _("集群{}所有实例检查通过").format(c.immute_domain)
    create_meta_check_report(
        cluster=c,
        ip="all",
        port=None,
        subtype=report_type,
        msg=msg,
        state=ReportStateType.NORMAL,
        creator=creator,
    )
    logger.info("instance_check: cluster {} passed".format(c.immute_domain))
