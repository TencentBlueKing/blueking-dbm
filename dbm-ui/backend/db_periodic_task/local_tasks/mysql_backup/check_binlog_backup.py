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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.constants import BACKUP_TASK_SUCCESS
from backend.db_report.enums import MysqlBackupCheckSubType
from backend.db_report.models import MysqlBackupCheckReport

from .bklog_query import ClusterBackup
from .check_full_backup import get_query_date_time

logger = logging.getLogger("root")


def check_binlog_backup(date_str: str):
    _check_tendbha_binlog_backup(date_str)
    _check_tendbcluster_binlog_backup(date_str)


def _check_tendbha_binlog_backup(date_str: str):
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    logger.info("==== start check binlog for cluster type {} ====".format(ClusterType.TenDBHA))
    return _check_binlog_backup(ClusterType.TenDBHA, date_str)


def _check_tendbcluster_binlog_backup(date_str: str):
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    logger.info("==== start check binlog for cluster type {} ====".format(ClusterType.TenDBCluster))
    return _check_binlog_backup(ClusterType.TenDBCluster, date_str)


def _check_binlog_backup(cluster_type, date_str):
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    start_time, end_time = get_query_date_time(date_str)
    logger.info(
        "==== start check binlog for cluster type {}, time range[{},{}] ====".format(
            cluster_type, start_time, end_time
        )
    )
    for c in Cluster.objects.filter(cluster_type=cluster_type):
        backup = ClusterBackup(c.id, c.immute_domain)
        logger.info(
            "==== start check binlog for cluster {}, time range[{},{}] ====".format(
                c.immute_domain, start_time, end_time
            )
        )
        # todo 需要获取集群的 master 分片实例，或者分片数

        items = backup.query_binlog_from_bklog(start_time, end_time)
        instance_binlogs = defaultdict(list)
        shard_binlog_stat = {}
        for i in items:
            instance = "{}:{}".format(i.get("mysql_host"), i.get("mysql_port"))
            if i.get("backup_status") == BACKUP_TASK_SUCCESS:
                instance_binlogs[instance].append(i.get("file_name"))
            else:
                instance_binlogs[instance].append("binlog.000001")  # 人为触发不连续

        backup.success = True
        if not instance_binlogs:
            backup.success = False

        for inst, binlogs in instance_binlogs.items():
            suffixes = [f.split(".", 1)[1] for f in binlogs]
            shard_binlog_stat[inst] = is_consecutive_strings(suffixes)
            if not shard_binlog_stat[inst]:
                backup.success = False

        if not backup.success:
            MysqlBackupCheckReport.objects.create(
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                cluster=c.immute_domain,
                cluster_type=cluster_type,
                status=False,
                msg="binlog is not consecutive:{}".format(shard_binlog_stat),
                subtype=MysqlBackupCheckSubType.BinlogSeq.value,
            )


def is_consecutive_strings(str_list: list):
    """
    判断字符串数字是否连续
    """
    int_list = [int(s) for s in str_list]
    int_sorted = list(set(int_list))
    int_sorted.sort()
    if len(int_sorted) == 0:
        return False
    if len(int_sorted) == 1:
        return True
    if len(int_sorted) == int_sorted[-1] - int_sorted[0] + 1:
        return True
    else:
        return False
