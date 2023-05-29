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
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisBackupCheckSubType
from backend.db_report.models import RedisBackupCheckReport

from .bklog_query import ClusterBackup

logger = logging.getLogger("root")


def check_full_backup():
    _check_tendis_full_backup()


class BackupFile:
    def __init__(self, file_name: str, file_size: int, file_type=""):
        self.file_name = file_name
        self.file_size = file_size
        self.file_type = file_type


def _check_tendis_full_backup():
    """
    tendisplus,ssd,cache 三种架构：
    1、针对集群全部查询出来：
        1.1 然后过滤失败的，直接写入库：不可能同一时间点，又存在失败的，又存在成功的，所以有失败的直接入库了
        1.2、再过滤成功的部分，去校验，(如果不加这个逻辑的话，可能备份记录没上报的情况)
                1.2.1 每天最少有3份全备份(新部署的集群可能没有3份，所以这里需要获取集群部署时间吗？)
                        所以这里获取部署时间超过1天的集群，最少有3份；部署时间小于1天的集群，暂时不考虑这个校验咯，如果有失败的1.1会记录
                1.2.2 Q:需要针对时间点去查询吗？这样子的话就是写死3个时间点了，但是机器的crontab可能被改动？
                A:没必要，有些集群可能会设置业务低峰期备份
                1.2.3 小于的这种情况，可能是在master上的备份，这种情况下，再去校验一下master的备份情况
                1.2.4  过滤掉 刚扩容，重建热备-> 创建时间小于24小时的节点

    备份规则：
    redis cache 全备份每天三次，一般的时间点如下：
    cron: 0 5,13,21 * * *
    ssd，plus 每天一次全备份,早上五点
    """

    """
    删除时间大于60天的记录,全备份和binlog都是同一张表，这里操作就好
    """
    RedisBackupCheckReport.objects.filter(create_at__lte=timezone.now() - timedelta(days=60)).delete()

    # 构建查询条件:tendisplus,ssd,cache,集群创建时间大于1天，巡检0点发起
    query = (
        Q(cluster_type=ClusterType.TendisPredixyTendisplusCluster)
        | Q(cluster_type=ClusterType.TwemproxyTendisSSDInstance)
        | Q(cluster_type=ClusterType.TendisTwemproxyRedisInstance)
    ) & Q(create_at__lt=timezone.now() - timedelta(days=1))
    # 遍历集群
    for c in Cluster.objects.filter(query):
        logger.info("+===+++++===  start check {} full backup +++++===++++ ".format(c.immute_domain))
        logger.info("+===+++++===  cluster type is: {} +++++===++++ ".format(c.cluster_type))
        cluster_slave_instance = []  # 初始化集群slave列表
        cluster_master_instance = []  # 初始化集群master列表
        cluster_all_instance = []
        bklog_success_instance_count = {}  # 初始化字典：节点和对应的备份次数
        slave_ins_map = defaultdict()  # 主从节点对应关系

        for master_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            current_datetime = timezone.now()
            # 计算时间差
            time_difference = current_datetime - slave_obj.create_at
            # 判断时间差是否大于等于24小时  # 过滤掉 刚扩容，重建热备-> 创建时间小于24小时
            if time_difference >= timedelta(hours=24):
                # 进行相应的操作
                cluster_slave_instance.append("{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port))
                cluster_master_instance.append(
                    "{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)
                )
                slave_ins_map[
                    "{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)
                ] = "{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)

        cluster_all_instance.extend(cluster_slave_instance)
        cluster_all_instance.extend(cluster_master_instance)
        logger.info("+===+++++===  cluster slave instance  is: {} +++++===++++ ".format(cluster_slave_instance))

        # 初始化所有 instance 的计数为 0
        for instance in cluster_all_instance:
            bklog_success_instance_count[instance] = 0

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day).astimezone(timezone.utc)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59).astimezone(timezone.utc)
        #  	 +===+++++=== start_time is: 2023-10-25 00:00:00 ,end_time is :2023-10-25 23:59:59 +++++===++++
        logger.info("+===+++++=== start_time is: {} ,end_time is :{} +++++===++++ ".format(start_time, end_time))
        # 集群前一天对应的集群备份记录
        backup = ClusterBackup(c.id, c.immute_domain)
        # 集群纬度的，假设一开始是备份完整的，后面会去校验对这个值进行赋值，如果有存在异常会赋值为False

        bklogs = backup.query_full_log_from_bklog(start_time, end_time)
        # 如果集群维度没有数据，就不用在看节点维度了
        if not bklogs:
            msg = _("无法查找到在时间范围内{}-{}，集群{}的全备份日志").format(start_time, end_time, c.immute_domain)
            logger.error(msg)
            instance = "all instance"
            full_backup_failed_record(c, instance, msg)
            continue

        logger.info(_("+===+++++===  {} 集群维度日志不为空 +++++===++++ ".format(c.immute_domain)))
        for bklog in bklogs:
            # 失败的记录，直接记录:同一条记录，不可能又存在失败的，又存在成功的，所以有失败的直接入库了
            if bklog.get("backup_status", "") == "to_backup_system_failed":
                logger.error("+===+++++=== to_backup_system_failed bklog: {} +++++===++++ ".format(bklog))
                msg = bklog["backup_status_info"]
                instance = bklog["redis_ip"] + IP_PORT_DIVIDER + str(bklog["redis_port"])
                full_backup_failed_record(c, instance, msg)

            # 对成功的进行处理
            if bklog.get("backup_status", "") == "to_backup_system_success":
                # 集群的master和slave 都进行统计
                for instance in cluster_all_instance:
                    ip, port = instance.split(":")
                    if ip == bklog["redis_ip"] and int(port) == bklog["redis_port"]:
                        # 找到匹配的项，更新计数
                        bklog_success_instance_count[instance] += 1
        # 校验instance和对应的计数：可能存在master备份，也可能存在slave的备份
        for instance, count in bklog_success_instance_count.items():
            # 默认是对slave进行备份，slave进行校验
            if instance not in cluster_slave_instance:
                continue
            logger.info(_("+===++==={}正常备份次数{}，集群类型{} ++++++++ ".format(instance, count, c.cluster_type)))
            # ssd,plus 每天备份一次
            if c.cluster_type in (ClusterType.TendisPredixyTendisplusCluster, ClusterType.TwemproxyTendisSSDInstance):
                expect_count = 1
            # cahce 每天备份三次
            elif c.cluster_type == ClusterType.TendisTwemproxyRedisInstance:
                expect_count = 3
            else:
                continue
            master_instance = slave_ins_map[instance]
            master_backup_count = bklog_success_instance_count[master_instance]

            if count < expect_count and master_backup_count < expect_count:
                msg = """slave:{} the number of files successfully backed is:{},
                master:{} the number of files successfully backed is:{}：
                There are no backup files {} times, please check! """.format(
                    instance, count, master_instance, master_backup_count, expect_count
                )
                # 记录备份失败的集群和实例
                full_backup_failed_record(c, instance, msg)


def full_backup_failed_record(c: Cluster, instance: str, msg: str):
    """
    记录全备备份失败的集群和实例
    """
    logger.info(_("+===++===  实例{}全备份失败，集群类型{}写入表 ++++++++ ".format(instance, c.cluster_type)))
    RedisBackupCheckReport.objects.create(
        creator=c.creator,
        bk_biz_id=c.bk_biz_id,
        bk_cloud_id=c.bk_cloud_id,
        cluster=c.immute_domain,
        cluster_type=c.cluster_type,
        instance=instance,
        status=False,
        msg=msg,
        subtype=RedisBackupCheckSubType.FullBackup.value,
    )
