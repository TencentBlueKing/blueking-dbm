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
from datetime import datetime, time, timedelta
from typing import Dict, List, Set

import pytz

from backend.components.bklog.handler import BKLogHandler
from backend.components.mysql_backup.client import SQLServerBackupApi
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.sqlserver_check_report import SqlserverFullBackupInfoReport, SqlserverLogBackupInfoReport

logger = logging.getLogger("root")


class CheckBackupInfo(object):
    """
    已dbm元数据为准
    检查实例的app_setting表的信息是否符合预期，如果存在信息不一致，则需要已某种方式输出告知相关DBA
    """

    def __init__(self):
        # 获取所有的online状态的cluster
        self.clusters = Cluster.objects.prefetch_related(
            "storageinstance_set",
            "storageinstance_set__machine",
        ).filter(phase=ClusterPhase.ONLINE, cluster_type__in=[ClusterType.SqlserverHA, ClusterType.SqlserverSingle])
        # 拼装查询的时间区间, 查找当前00点到前一天的00点
        tz = pytz.FixedOffset(480)
        today = datetime.now(tz).date()
        midnight_utc = datetime.combine(today, time(), tzinfo=tz)

        # 增量备份的时间段检查(从0点开始检查前一天)
        self.log_backup_start_time = midnight_utc - timedelta(days=1)
        self.log_backup_end_time = midnight_utc

        # 全量备份的时间段检查(检查当天的)
        self.full_backup_start_time = midnight_utc
        self.full_backup_end_time = datetime.now(tz)

    def __query_log_bk_log(self, cluster: Cluster, collector: str):
        if collector == "mssql_binlog_result":
            start_time = self.log_backup_start_time
            end_time = self.log_backup_end_time
        else:
            start_time = self.full_backup_start_time
            end_time = self.full_backup_end_time

        return BKLogHandler.query_logs(
            collector=collector,
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {cluster.id}",
            size=10000,
            sorting_rule="asc",
        )

    def check_task(self):
        for cluster in self.clusters:
            self.check_full_backup_info_cluster(cluster)
            self.check_log_backup_info_cluster(cluster)

    def check_full_backup_info_cluster(self, cluster: Cluster):
        """
        检查集群的全量备份文件周边信息是否存在
        1：对应的备份文件是否在备份记录
        2：对应的备份文件是否上传到备份系统
        """
        # 获取待巡检的全量备份信息
        backup_infos = self.__query_log_bk_log(cluster=cluster, collector="mssql_dbbackup_result")
        # 判断每一次的备份任务是否缺失记录
        check_result, is_normal = self.check_backup_info_in_bk_log(backup_infos, "full")
        # 写入到巡检表
        SqlserverFullBackupInfoReport.objects.create(
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            cluster=cluster.name,
            cluster_type=cluster.cluster_type,
            status=is_normal,
            msg=check_result,
        )
        return

    def check_log_backup_info_cluster(self, cluster: Cluster):
        """
        检查集群的增量备份文件周边信息是否存在
        1：对应的备份文件是否在备份记录
        2：对应的备份文件是否上传到备份系统
        """
        # 获取待巡检的全量备份信息
        backup_infos = self.__query_log_bk_log(cluster=cluster, collector="mssql_binlog_result")
        # 判断每一次的备份任务是否缺失记录
        check_result, is_normal = self.check_backup_info_in_bk_log(backup_infos, "log")
        # 写入到巡检表
        SqlserverLogBackupInfoReport.objects.create(
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            cluster=cluster.name,
            cluster_type=cluster.cluster_type,
            status=is_normal,
            msg=check_result,
        )
        return

    def check_backup_info_in_bk_log(self, backup_infos: list, tag: str):
        """
        判断从bk_log拉取出来的备份信息，根据backup_id聚合，判断合法性
        """
        if tag == "full":
            start_time = self.full_backup_start_time
            end_time = self.full_backup_end_time
        else:
            start_time = self.log_backup_start_time
            end_time = self.log_backup_end_time

        check_result = ""
        is_normal = True
        if not backup_infos:
            # 如果查询到的备份文件为空， 怎么提前返回结果
            return f"backup-info is null , check [{start_time}-{end_time}]", False

        # 根据backup id聚合备份记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_infos:
            backup_id__logs[log["backup_id"]].append(log)

        # 对每一份备份记录去重，相同的backup id不能出现重复的dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 遍历没有backup_id的备份任务
        for backup_id, logs in backup_id__valid_logs.items():
            # 按照备份任务，查询在备份系统上报情况
            task_ids = [i["task_id"] for i in logs]
            result = self.check_backup_file_in_backup_system(task_ids=task_ids)
            if result:
                check_result += f"[{backup_id}] {result}\n"
                is_normal = False

            # 判断每个备份任务的备份文件行数，跟bk_log上传的日志是否一致
            if len(logs) != logs[0]["file_cnt"]:
                check_result += f"Backup tasks[{backup_id}] are missing backup records, check\n"
                is_normal = False

        if not check_result:
            # 代表正常返回结果
            return f"backup info check ok [{start_time}-{end_time}]", is_normal

        return check_result, is_normal

    @staticmethod
    def check_backup_file_in_backup_system(task_ids: list):
        """
        根据传入的task_id列表，查询备份文件是否成功上传到备份系统
        """
        max_length = 100
        check_result = []
        if len(task_ids) > 100:
            # 如果大于最大长度，进行切分
            split_lists = [task_ids[i : i + max_length] for i in range(0, len(task_ids), max_length)]
        else:
            # 如果不大于最大长度，直接返回原列表
            split_lists = [task_ids]
        for task_list in split_lists:
            # 分批请求
            check_result.extend(SQLServerBackupApi.query_for_task_ids({"task_ids": task_list}))

        # 判断长度
        if len(task_ids) != len(check_result):
            # 如果传入的任务列表长度和返回的结果长度不一致，则必定是有缺漏，返回异常
            return "some backup files are not in the backup system, check"

        # 判断每个备份文件上传状态码，如果状态码不等于4（已上传完成），表示返回异常
        not_success_task_id_list = []
        for info in check_result:
            if info["status"] != 4:
                not_success_task_id_list.append(info["task_id"])
        if not_success_task_id_list:
            return f"some backup files failed to upload, check:{not_success_task_id_list}"

        return ""
