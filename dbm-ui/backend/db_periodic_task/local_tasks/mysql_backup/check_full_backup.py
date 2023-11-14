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

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MysqlBackupCheckSubType
from backend.db_report.models import MysqlBackupCheckReport

from .bklog_query import ClusterBackup


def check_full_backup():
    _check_tendbha_full_backup()
    _check_tendbcluster_full_backup()


class BackupFile:
    def __init__(self, file_name: str, file_size: int, file_type=""):
        self.file_name = file_name
        self.file_size = file_size
        self.file_type = file_type


class MysqlBackup:
    def __init__(self, cluster_id: int, cluster_domain: str, backup_id=""):
        self.cluster_id = cluster_id
        self.cluster_domain = cluster_domain
        self.backup_id = backup_id
        self.backup_type = ""
        self.backup_role = ""
        self.data_schema_grant = ""
        self.consistent_backup_time = ""
        self.shard_value = -1
        # self.file_index = BackupFile()
        # self.file_priv = BackupFile()
        self.file_tar = []


def _check_tendbha_full_backup():
    """
    tendbha 必须有一份完整的备份
    """
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBHA):
        backup = ClusterBackup(c.id, c.immute_domain)
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)

        items = backup.query_backup_log_from_bklog(start_time, end_time)
        # print("cluster={} backup_items:{}".format(c.immute_domain, items))
        for i in items:
            if i.get("data_schema_grant", "") == "all":
                bid = i.get("backup_id")
                if bid not in backup.backups:
                    backup.backups[bid] = MysqlBackup(i["cluster_id"], i["cluster_domain"], i["backup_id"])

                bf = BackupFile(i.get("file_name"), i.get("file_size"))
                backup.backups[bid].data_schema_grant = i.get("data_schema_grant")
                if i.get("file_type") == "index":
                    backup.backups[bid].file_index = bf
                elif i.get("file_type") == "priv":
                    backup.backups[bid].file_priv = bf
                elif i.get("file_type") == "tar":
                    backup.backups[bid].file_tar.append(bf)
                else:
                    pass
        for bid, bk in backup.backups.items():
            if bk.data_schema_grant == "all":
                if bk.file_index and bk.file_priv and bk.file_tar:
                    backup.success = True
                    break
        if not backup.success:
            MysqlBackupCheckReport.objects.create(
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                cluster=c.immute_domain,
                cluster_type=ClusterType.TenDBHA,
                status=False,
                msg="no success full backup found",
                subtype=MysqlBackupCheckSubType.FullBackup.value,
            )


def _check_tendbcluster_full_backup():
    """
    tendbcluster 集群必须有完整的备份
    """
    for c in Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster):
        backup = ClusterBackup(c.id, c.immute_domain)
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)

        items = backup.query_backup_log_from_bklog(start_time, end_time)
        # print("cluster={} backup_items:{}".format(c.immute_domain, items))
        for i in items:
            if i.get("data_schema_grant", "") == "all":
                bid = "{}#{}".format(i.get("backup_id"), i.get("shard_value"))
                if bid not in backup.backups:
                    backup.backups[bid] = MysqlBackup(i["cluster_id"], i["cluster_domain"], i["backup_id"])

                bf = BackupFile(i.get("file_name"), i.get("file_size"))
                backup.backups[bid].data_schema_grant = i.get("data_schema_grant")
                if i.get("file_type") == "index":
                    backup.backups[bid].file_index = bf
                elif i.get("file_type") == "priv":
                    backup.backups[bid].file_priv = bf
                elif i.get("file_type") == "tar":
                    backup.backups[bid].file_tar.append(bf)
                else:
                    pass
        backup_id_stat = defaultdict(list)
        backup_id_invalid = {}
        for bid, bk in backup.backups.items():
            backup_id, shard_id = bid.split("#", 1)
            if bk.data_schema_grant == "all":
                if bk.file_index and bk.file_priv and bk.file_tar:
                    #  这一个 shard ok
                    backup_id_stat[backup_id].append({shard_id: True})
                else:
                    # 这一个 shard 不ok，整个backup_id 无效
                    backup_id_invalid[backup_id] = True
                    backup_id_stat[backup_id].append({shard_id: False})
        message = ""
        for backup_id, stat in backup_id_stat.items():
            if backup_id not in backup_id_invalid:
                backup.success = True
                message = "shard_id:{}".format(backup_id_stat[backup_id])
                break

        if not backup.success:
            MysqlBackupCheckReport.objects.create(
                bk_biz_id=c.bk_biz_id,
                bk_cloud_id=c.bk_cloud_id,
                cluster=c.immute_domain,
                cluster_type=ClusterType.TenDBCluster,
                status=False,
                msg="no success full backup found:{}".format(message),
                subtype=MysqlBackupCheckSubType.FullBackup.value,
            )
