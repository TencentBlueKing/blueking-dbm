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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import ClusterReport, RecordBatchOps, addr, dev_debug
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mongodb_check_sub_type import MongodbBackupCheckSubType
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")

# CheckMongoBackupRecordTask 用于检查备份记录，全备和增量备份都检查
# 检查结果:
# 1. 全备
# - NORMAL: 存在，且备份时间小于8小时.
# - WARNING: 存在，且备份时间大于8小时.
# - ABNORMAL: 不存在.
# 2. 增量备份
# - NORMAL: 存在且连续
# - WARNING:
# - ABNORMAL: 不存在或不连续


class CheckMongoBackupRecordTask:
    """检查mongodb备份记录"""

    check_type: str

    def __init__(self):
        self.check_type = MongodbBackupCheckSubType.FullBackup.value

    def start(self, report_day: int = None, batch_size: int = 20):
        """
        cluster_type: replicaset, sharded cluster
        1, list all cluster
        2, filter failed, write to db
        """

        """
        Delete records older than 60 days, both full backup and binlog are in the same table
        """
        if report_day is None:
            report_day = int(timezone.now().date().strftime("%Y%m%d"))
        record_batch_ops = RecordBatchOps(self.check_type, report_day)
        deleted_count = record_batch_ops.delete_old_record(360)
        logger.info(
            f"CheckMongoBackupRecordTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"delete_old_record: {deleted_count}"
        )
        deleted_count = record_batch_ops.delete_today_record()
        logger.info(
            f"CheckMongoBackupRecordTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"delete_today_record: {deleted_count}"
        )
        # Build query conditions: cluster creation time greater than 8 hours
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=8)
        )

        app_total = {
            ReportStateType.NORMAL.value: 0,
            ReportStateType.WARNING.value: 0,
            ReportStateType.ABNORMAL.value: 0,
        }
        cluster_id_list = [c.id for c in Cluster.objects.filter(query)]  # fetch all cluster_id
        for i in range(0, len(cluster_id_list), batch_size):
            for cluster_id in cluster_id_list[i : i + batch_size]:
                cluster = MongoRepository.fetch_one_cluster(with_tags=True, id=cluster_id)
                ret = self.check_cluster(cluster, report_day)
                app_total[ret[0].state] += 1
                for record in ret:
                    record_batch_ops.append(record)
            record_batch_ops.bulk_create()
        logger.info(
            f"CheckMongoBackupRecordTask report_day: {report_day} "
            f"sub_type: {self.check_type} "
            f"app_total: {app_total}"
        )

    def is_skip_check(self, cluster: MongoDBCluster) -> tuple[bool, str]:
        """
        检查集群的tags是否为skip_check=true
        如果为true, 则返回True, "skipped by skip_check:true"
        如果为false, 则返回False, ""
        """
        tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
        v = tags.get("backup", "")
        if v in ["no", "false"]:
            return True, "skipped by backup:{}".format(v)
        v = tags.get("temporary", "")
        if v == "true":
            return True, "skipped by temporary:{}".format(v)
        return False, ""

    def check_cluster(self, cluster: MongoDBCluster, report_day: int):
        """
        1. 获得所有的分片的m1节点. 和 backup节点
        2. 允许所有的分片都没有backup节点,这种情况跳过检查
        3. 允许配置为不备份 -- 但目前没有地方存放这种配置 todo
        4. 检查所有的分片的backup节点是否存在全备文件记录
        5. 检查所有的分片的backup节点的增量备份记录是否连续
        """

        cluster_report = ClusterReport(cluster, report_day, self.check_type)
        skipped, skip_reason = self.is_skip_check(cluster)
        if skipped:
            dev_debug(f"=== check_one {cluster.cluster_id} {cluster.immute_domain} {skip_reason} === ")
            return cluster_report.make_skip_record(skip_reason)

        backup_records = fetch_backup_record_from_es(cluster) or {}

        dev_debug(f"cluster.tags {cluster.cluster_id} {cluster.immute_domain} tags: {cluster.tags}")

        for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
            msg = ""
            state = ReportStateType.NORMAL.value
            shard_id = shard.set_name
            if shard_id is None:
                msg = "no-shard-id"
                state = ReportStateType.ABNORMAL.value
            else:
                node = shard.get_backup_node()
                if node is None:
                    msg = "no backup node"
                    state = ReportStateType.ABNORMAL.value
                else:
                    state, msg = self.check_one_shard(cluster, shard_id, backup_records)

            cluster_report.append(state, shard_id, addr(node), msg)

        return cluster_report.make_records()

    def check_one_shard(self, cluster: MongoDBCluster, shard_id: str, backup_records: dict) -> (str, str):
        """
        1. 获得所有的分片的m1节点. 和 backup节点
        2. 允许所有的分片都没有backup节点,这种情况跳过检查
        3. 允许配置为不备份 -- 但目前没有地方存放这种配置
        4. 检查所有的分片的backup节点是否存在全备文件记录
        """

        # records[set_name][pitr_fullname][node].append(row)
        shard_backup_records = backup_records.get(shard_id, None)
        if shard_backup_records is None:
            return ReportStateType.ABNORMAL.value, "no-full-backup-file"

        # 全备记录. pitr_fullname_list的成员是一个yyyymmddhh格式的数字, 此处做个排序, 先分析最新的记录.
        pitr_fullname_list = sorted([int(x) for x in shard_backup_records.keys()], reverse=True)

        ret_list = []
        for i, pitr_fullname in enumerate(pitr_fullname_list):
            # do check full backup record
            node_list = list(shard_backup_records[str(pitr_fullname)].keys())
            # 一个pitr_fullname 只有一个节点，如果多个节点，则认为是异常
            if len(node_list) != 1:
                ret_list.append(
                    {
                        "state": ReportStateType.ABNORMAL.value,
                        "msg": "unusual full backup record: pitr_fullname: {}, node_list: {}".format(
                            pitr_fullname, node_list
                        ),
                    }
                )

            node = node_list[0]
            incr_list = shard_backup_records[str(pitr_fullname)][node]
            # check incremental backup record]
            for i, row in enumerate(incr_list):
                dev_debug(
                    "BackupRecordStat {} pitr_file_type {} pitr_fullname {} pitr_binlog_index: {} file_name: {} "
                    "file_size: {} backup_time: {} {}".format(
                        i,
                        row.get("pitr_file_type"),
                        row.get("pitr_fullname"),
                        row.get("pitr_binlog_index"),
                        row.get("file_name"),
                        row.get("file_size"),
                        row.get("start_time"),
                        row.get("end_time"),
                    )
                )

            state, msg = BackupRecordStat(incr_list[0]).check_incremental_backup_record(incr_list)
            if msg == "skipped":
                continue
            ret_list.append({"state": state, "msg": msg})

        # 如果全备记录都ok，则返回ok
        # 如果没有正常的记录，返回其中一个异常的记录 msg
        for s in [ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value, ReportStateType.NORMAL.value]:
            for ret in ret_list:
                if ret["state"] == s:
                    return ret["state"], ret["msg"]
        # 如果没有正常的记录，返回其中一个异常的记录 msg
        return ReportStateType.ABNORMAL.value, "no-incremental-backup-record"


# fetch_backup_record_from_es
def fetch_backup_record_from_es(cluster: MongoDBCluster) -> dict:
    """从ES获取备份记录"""
    current_datetime = timezone.now()

    # 从es中获取备份记录
    backup_records = MongoDBRestoreHandler.query_clusters_backup_log(
        [cluster.cluster_id],
        cluster.cluster_type,
        current_datetime - timedelta(hours=36),  # 36 hours
        current_datetime,
        "src=daily",
    )

    cluster_backup_records = backup_records.get(cluster.cluster_id)
    if not cluster_backup_records:
        logger.error(f"fetch_backup_record_from_es cluster_id: {cluster.cluster_id} fulls: 0")
        return None
    # records[set_name][pitr_fullname][node] = []
    records = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))

    # find full
    for row in cluster_backup_records:
        """check daily backup"""
        set_name = row.get("set_name")
        pitr_fullname = row.get("pitr_fullname")
        pitr_file_type = row.get("pitr_file_type")
        server_ip = row.get("server_ip")
        server_port = row.get("server_port")

        if pitr_file_type not in ["FULL", "INCR"] or not all([set_name, pitr_fullname, server_ip, server_port]):
            # warning
            logger.warning(
                f"fetch_backup_record_from_es bad record cluster_id: {cluster.cluster_id} "
                f"pitr_file_type: {pitr_file_type} "
                f"set_name: {set_name} "
                f"pitr_fullname: {pitr_fullname} "
                f"server_ip: {server_ip} "
                f"server_port: {server_port}"
            )
            continue
        node = server_ip + ":" + str(server_port)
        records[set_name][pitr_fullname][node].append(row)
    return records


# 备份记录统计
class BackupRecordStat:
    def __init__(self, row: dict):
        dev_debug("BackupRecordStat init row: {}".format(row))
        self.pitr_fullname = row.get("pitr_fullname")
        self.pitr_file_type = row.get("pitr_file_type")
        self.server_ip = row.get("server_ip")
        self.server_port = row.get("server_port")
        self.set_name = row.get("set_name")
        self.full_backup_time = None
        self.incremental_backup_time_list = []
        self.incremental_backup_count = 0
        self.incremental_backup_continuous_count = 0
        self.incremental_backup_continuous_count_max = 12
        self.incremental_backup_continuous = True

    # get backup time
    # return start_time, end_time tuple
    # if full_record is None, return None, None
    def get_backup_time(self, record: dict) -> tuple[datetime, datetime, timedelta]:
        if record is None:
            return None, None, None

        start_time_str = record.get("start_time")  # 2025-06-05T12:44:45+08:00
        end_time_str = record.get("end_time")  # 2025-06-05T12:44:45+08:00
        # parse time
        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S+08:00")
            end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M:%S+08:00")
            return start_time, end_time, end_time - start_time
        except Exception:
            return None, None, None

    def check_incremental_backup_record(self, incr_list: list) -> tuple[str, str]:
        if not incr_list:
            return ReportStateType.ABNORMAL.value, "no incremental backup record"

        # incr_list sort by pitr_binlog_index
        incr_list.sort(key=lambda x: x.get("pitr_binlog_index", -1))

        if incr_list[0].get("pitr_file_type") != "FULL":
            return ReportStateType.WARNING.value, "skipped"

        max_duration = timedelta(hours=1)
        max_duration_file_name = ""
        # 检查增量备份记录是否连续
        for i, v in enumerate(incr_list):
            start_time, end_time, duration = self.get_backup_time(v)
            # duration 有可能是0，正常
            if not all([start_time, end_time]):
                return ReportStateType.ABNORMAL.value, "get backup time error for record: {}".format(v)

            if i == 0:
                # 检查全备时长
                if duration > timedelta(hours=8):
                    return (ReportStateType.WARNING.value,)
                    "full backup time too long: {} hours".format(round((duration).total_seconds() / 3600, 2))

                continue

            idx = v.get("pitr_binlog_index", -2)
            prev_idx = incr_list[i - 1].get("pitr_binlog_index", -2)
            if int(idx) - int(prev_idx) != 1:
                return ReportStateType.ABNORMAL.value, "incremental backup record not continuous"

            if duration > max_duration:
                max_duration = duration
                max_duration_file_name = v.get("file_name")

        if max_duration_file_name != "":
            dev_debug(
                "incremental backup time too long: {} hours file_name: {}".format(
                    (max_duration).total_seconds() / 3600,
                    max_duration_file_name,
                )
            )
            return ReportStateType.WARNING.value, "incremental backup time too long: {} hours file_name: {}".format(
                round((max_duration).total_seconds() / 3600, 2),
                max_duration_file_name,
            )

        return ReportStateType.NORMAL.value, "ok"


def cluster_tags_is_skip_backup(cluster: MongoDBCluster) -> bool:
    """
    检查集群的tags
    """
    tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
    return tags.get("backup", "") in ["no", "false"]


def cluster_tags_is_temporary(cluster: MongoDBCluster) -> bool:
    """
    检查集群的tags是否为temporary=true
    """
    tags = {tag.key: tag.value for tag in cluster.tags} if cluster.tags else {}
    return tags.get("temporary", "") == "true"
