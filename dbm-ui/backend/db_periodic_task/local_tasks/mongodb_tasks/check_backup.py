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
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import addr, create_failed_record, dev_debug
from backend.db_report.enums.mongodb_check_sub_type import MongodbBackupCheckSubType
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.db_services.mongodb.restore.handlers import MongoDBRestoreHandler
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository

logger = logging.getLogger("root")

# CheckMongoBackupRecordTask 用于检查备份记录，全备和增量备份都检查
# 检查结果:
# 1. 全备记录:1 - 增量备份记录连续
# 2. 全备记录:2 - 增量备份记录不连续，或者增量备份数量小于12个
# 3. 全备时长大于8小时
# 业务级检查结果:
# 业务id:{} 集群数量{} 已检查{} 成功{} 失败{}
# 平台级检查结果:
# 业务id:{} 集群数量{} 已检查{} 成功{} 失败{}
# 平台级检查结果:


class CheckMongoBackupRecordTask:
    def __init__(self):
        pass

    def start(self):
        """
        cluster_type: replicaset, sharded cluster
        1, list all cluster
        2, filter failed, write to db
        """

        """
        Delete records older than 60 days, both full backup and binlog are in the same table
        """
        failed_records = []
        MongodbBackupCheckReport.objects.filter(create_at__lte=timezone.now() - timedelta(days=60)).delete()

        # Build query conditions: cluster creation time greater than 8 hours
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]) & Q(
            create_at__lt=timezone.now() - timedelta(hours=8)
        )
        cluster_list = Cluster.objects.filter(query)
        batch_size = 100
        for c in cluster_list:
            cluster = MongoRepository.fetch_one_cluster(with_tags=True, id=c.id)
            ret = self.check_cluster(cluster)
            failed_records.extend(ret)
            if len(failed_records) > batch_size:
                dev_debug("cluster {} failed_records {}".format(cluster.cluster_id, len(failed_records)))
                # 批量插入备份失败记录
                MongodbBackupCheckReport.objects.bulk_create(failed_records)
                failed_records = []

        if failed_records:
            dev_debug("cluster {} failed_records {}".format(cluster.cluster_id, len(failed_records)))
            # 批量插入备份失败记录
            MongodbBackupCheckReport.objects.bulk_create(failed_records)

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

    def check_cluster(self, cluster: MongoDBCluster):
        """
        1. 获得所有的分片的m1节点. 和 backup节点
        2. 允许所有的分片都没有backup节点,这种情况跳过检查
        3. 允许配置为不备份 -- 但目前没有地方存放这种配置 todo
        4. 检查所有的分片的backup节点是否存在全备文件记录
        5. 检查所有的分片的backup节点的增量备份记录是否连续
        """
        full_backup = MongodbBackupCheckSubType.FullBackup.value
        failed_records = []

        skipped, reason = self.is_skip_check(cluster)
        if skipped:
            dev_debug(f"=== check_one {cluster.cluster_id} {cluster.immute_domain} {reason} === ")
            failed_records.append(create_failed_record(cluster, "all", "all", True, reason, full_backup))
            return failed_records

        msg = ""
        ok_num = 0
        shard_num = 0

        backup_records = fetch_backup_record_from_es(cluster) or {}

        dev_debug(f"cluster.tags {cluster.cluster_id} {cluster.immute_domain} tags: {cluster.tags}")

        for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
            shard_num += 1
            ok = False
            shard_id = shard.set_name
            if shard_id is None:
                msg = "no-shard-id"
            else:
                node = shard.get_backup_node()
                if node is None:
                    msg = "no backup node"
                else:
                    ok, msg = self.check_one_shard(cluster, shard_id, backup_records)

            if not ok:
                failed_records.append(
                    create_failed_record(cluster, shard_id, addr(node), msg == "ok", msg, full_backup)
                )
            else:
                ok_num += 1

        if shard_num == ok_num:
            failed_records.append(
                create_failed_record(cluster, "all", "all", True, "all {} shards are ok".format(ok_num), full_backup)
            )

        return failed_records

    def check_one_shard(self, cluster: MongoDBCluster, shard_id: str, backup_records: dict) -> (dict):
        """
        1. 获得所有的分片的m1节点. 和 backup节点
        2. 允许所有的分片都没有backup节点,这种情况跳过检查
        3. 允许配置为不备份 -- 但目前没有地方存放这种配置
        4. 检查所有的分片的backup节点是否存在全备文件记录
        """

        # records[set_name][pitr_fullname][node].append(row)
        shard_backup_records = backup_records.get(shard_id, None)
        if shard_backup_records is None:
            return False, "no-full-backup-file"

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
                        "ok": False,
                        "msg": "unusual full backup record: "
                        "pitr_fullname: {}, node_list: {}".format(pitr_fullname, node_list),
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

            ret, msg = BackupRecordStat(incr_list[0]).check_incremental_backup_record(incr_list)
            if msg == "skipped":
                continue
            ret_list.append({"ok": ret, "msg": msg})

        # 如果全备记录都ok，则返回ok
        # 如果没有正常的记录，返回其中一个异常的记录 msg

        all_ok = True
        msg = ""
        for ret in ret_list:
            if not ret["ok"]:
                all_ok = False
                msg = ret["msg"]
                break

        if all_ok:
            return True, "ok"
        if msg == "":
            msg = "unknown-error"
        return False, msg


# fetch_backup_record_from_es
def fetch_backup_record_from_es(cluster: MongoDBCluster) -> (dict):
    current_datetime = timezone.now()

    # 从es中获取备份记录
    backup_records = MongoDBRestoreHandler.query_clusters_backup_log(
        [cluster.cluster_id],
        cluster.cluster_type,
        current_datetime - timedelta(hours=36),  # 36 hours
        current_datetime,
        "src=daily",
    )
    # msg
    cluster_backup_records = backup_records.get(cluster.cluster_id, None)
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

    def check_incremental_backup_record(self, incr_list: list) -> tuple[bool, str]:
        if not incr_list:
            return False, "no incremental backup record"

        # incr_list sort by pitr_binlog_index
        incr_list.sort(key=lambda x: x.get("pitr_binlog_index", -1))

        if incr_list[0].get("pitr_file_type") != "FULL":
            return False, "skipped"

        max_duration = timedelta(hours=1)
        max_duration_file_name = ""
        # 检查增量备份记录是否连续
        for i, v in enumerate(incr_list):
            start_time, end_time, duration = self.get_backup_time(v)
            # duration 有可能是0，正常
            if not all([start_time, end_time]):
                return False, "get backup time error for record: {}".format(v)

            if i == 0:
                # 检查全备时长
                if duration > timedelta(hours=8):
                    return False, "full backup time too long: {} hours".format((duration).total_seconds() / 3600)

                continue

            idx = v.get("pitr_binlog_index", -2)
            prev_idx = incr_list[i - 1].get("pitr_binlog_index", -2)
            if int(idx) - int(prev_idx) != 1:
                return False, "incremental backup record not continuous"

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
            return False, "incremental backup time too long: {} hours file_name: {}".format(
                (max_duration).total_seconds() / 3600,
                max_duration_file_name,
            )

        return True, "ok"


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
