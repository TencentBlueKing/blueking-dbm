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
from collections import defaultdict
from datetime import datetime, timedelta

from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MysqlBackupCheckSubType
from backend.db_report.models import MysqlBackupCheckReport

from .bklog_query import ClusterBackup


def check_binlog_backup():
    _check_tendbha_binlog_backup()
    _check_tendbcluster_binlog_backup()


def _check_tendbha_binlog_backup():
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    return _check_binlog_backup(ClusterType.TenDBHA)


def _check_tendbcluster_binlog_backup():
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    return _check_binlog_backup(ClusterType.TenDBCluster)


def _check_binlog_backup(cluster_type):
    """
    master 实例必须要有备份binlog
    且binlog序号要连续
    """
    for c in Cluster.objects.filter(cluster_type=cluster_type):
        backup = ClusterBackup(c.id, c.immute_domain)
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)

        items = backup.query_binlog_from_bklog(start_time, end_time)
        instance_binlogs = defaultdict(list)
        shard_binlog_stat = {}
        for i in items:
            instance = "{}:{}".format(i.get("mysql_host"), i.get("mysql_port"))
            if i.get("mysql_role") == "master" and i.get("backup_status") == 4:
                instance_binlogs[instance].append(i.get("file_name"))
        backup.success = True

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
                cluster_type=ClusterType.TenDBCluster,
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
