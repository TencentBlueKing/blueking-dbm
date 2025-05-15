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
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import addr, create_failed_record, dev_debug
from backend.db_report.enums.mongodb_check_sub_type import MongodbBackupCheckSubType
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")


class CheckMongoBackupRecordTask:
    def __init__(self):
        pass

    def start(self):
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db
        """

        """
        删除时间大于60天的记录,全备份和binlog都是同一张表，这里操作就好
        """
        failed_records = []
        MongodbBackupCheckReport.objects.filter(create_at__lte=timezone.now() - timedelta(days=60)).delete()

        # 构建查询条件: 集群创建时间大于8小时
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=8)
        )
        cluster_list = Cluster.objects.filter(query)
        batch_size = 100
        for c in cluster_list:
            cluster = MongoRepository.fetch_one_cluster(withDomain=False, id=c.id)
            ret = self.check_one(cluster)
            failed_records.extend(ret)
            if len(failed_records) > batch_size:
                dev_debug("cluster {} failed_records {}".format(cluster.cluster_id, len(failed_records)))
                # 批量插入备份失败记录
                MongodbBackupCheckReport.objects.bulk_create(failed_records)
                failed_records = []

        if len(failed_records) > 0:
            dev_debug("cluster {} failed_records {}".format(cluster.cluster_id, len(failed_records)))
            # 批量插入备份失败记录
            MongodbBackupCheckReport.objects.bulk_create(failed_records)

    @staticmethod
    def check_one(cluster: MongoDBCluster):
        """
        1. 获得所有的分片的m1节点. 和 backup节点
        2. 允许所有的分片都没有backup节点，这种情况跳过检查。
        3. 允许配置为不备份 -- 但目前没有地方存放这种配置 todo
        4. 检查所有的分片的backup节点是否存在全备文件记录
        5. 检查所有的分片的backup节点的增量备份记录是否连续 todo
        """
        dev_debug(f"=== check_one {cluster.cluster_id} {cluster.immute_domain} === ")
        failed_records = []
        backup_records = fetch_backup_record_by_cluster(cluster)
        full_backup = MongodbBackupCheckSubType.FullBackup.value

        if backup_records is None:
            backup_records = {}
        msg = ""

        for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
            shard_id = shard.set_name
            if shard_id is None:
                # error
                continue
            node = shard.get_backup_node()
            if node is None:
                msg = "no backup node"
            else:
                rows = backup_records.get(shard_id, None)
                if rows is None:
                    msg = "no-full-backup-file"
                else:
                    msg = "ok"

            failed_records.append(create_failed_record(cluster, shard_id, addr(node), msg == "ok", msg, full_backup))

        return failed_records


# fetch_backup_record_by_cluster
def fetch_backup_record_by_cluster(cluster: MongoDBCluster) -> (dict, dict):
    current_datetime = timezone.now()

    backup_log = MongoDBRestoreHandler.query_clusters_backup_log(
        [cluster.cluster_id],
        cluster.cluster_type,
        current_datetime - timedelta(days=2),
        current_datetime,
        "src=daily",
    )
    # msg
    if backup_log[cluster.cluster_id] is None or len(backup_log[cluster.cluster_id]) == 0:
        logger.error(
            "fetch_backup_record_by_cluster cluster_Id: {} fulls: {}".format(
                cluster.cluster_id, len(backup_log[cluster.cluster_id])
            )
        )
        return None

    cluster_backup_log = backup_log[cluster.cluster_id]
    # a[b][c][d] = []
    records = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # find full
    for row in cluster_backup_log:
        """check daily backup"""
        set_name = row.get("set_name")
        pitr_fullname = row.get("pitr_fullname")
        pitr_file_type = row.get("pitr_file_type")

        if set_name is None or pitr_fullname is None:
            # warning
            continue
        records[set_name][pitr_fullname][pitr_file_type].append(row)
    return records
