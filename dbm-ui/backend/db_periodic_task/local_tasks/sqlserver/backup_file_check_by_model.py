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
from typing import Dict, List, Set, Tuple

import pytz
from django.utils.translation import gettext as _

from backend.components.mysql_backup.client import SQLServerBackupApi
from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_report.enums import ReportStateType
from backend.db_report.models.sqlserver_check_report import (
    SqlserverFullBackupCheckReport,
    SqlserverLogBackupCheckReport,
)
from backend.db_report.models.sqlserver_full_backup_result import SQLServerBackupResult
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.flow.utils.sqlserver.sqlserver_db_function import get_app_setting_data, get_routine_backup_dbs

logger = logging.getLogger("root")


class CheckBackupInfoByModel(object):
    """
    基于 SQLServerBackupResult / SQLServerBinlogResult 模型查询的备份巡检
    以 dbm 元数据为准，检查集群的备份是否正常
    """

    def __init__(self):
        # 获取所有的 online 状态的 cluster
        self.clusters = Cluster.objects.prefetch_related(
            "storageinstance_set",
            "storageinstance_set__machine",
        ).filter(phase=ClusterPhase.ONLINE, cluster_type__in=[ClusterType.SqlserverHA, ClusterType.SqlserverSingle])

        # 拼装查询的时间区间，查找当前00点到前一天的00点
        tz = pytz.FixedOffset(480)
        today = datetime.now(tz).date()
        midnight_utc = datetime.combine(today, time(), tzinfo=tz)

        # 增量备份的时间段检查(从0点开始检查前一天)
        self.log_backup_start_time = midnight_utc - timedelta(days=1) + timedelta(seconds=300)
        self.log_backup_end_time = midnight_utc + timedelta(seconds=300)

        # 全量备份的时间段检查(检查当天的)
        self.full_backup_start_time = midnight_utc
        self.full_backup_end_time = datetime.now(tz)

    def check_task(self):
        """巡检入口：遍历所有集群，逐一检查备份情况"""
        for cluster in self.clusters:
            common_data = {
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "cluster": cluster.immute_domain,
                "cluster_type": cluster.cluster_type,
                "state": ReportStateType.NORMAL.value,
                "msg": "",
                "failed_days": 0,
            }

            # 如果集群的创建时间大于起始时间，则跳过这次巡检
            earliest_check_time = min(self.full_backup_start_time, self.log_backup_start_time)
            if cluster.create_at > earliest_check_time:
                common_data["state"] = ReportStateType.NORMAL.value
                common_data["msg"] = _("集群创建时间[{}]比检查起始时间[{}]晚，跳过本次检查".format(cluster.create_at, earliest_check_time))
                SqlserverFullBackupCheckReport.objects.create(**common_data)
                SqlserverLogBackupCheckReport.objects.create(**common_data)
                continue

            # 单节点集群的前置检查
            try:
                if cluster.cluster_type == ClusterType.SqlserverSingle:
                    instance = cluster.storageinstance_set.get(instance_role=InstanceRole.ORPHAN)
                    data, err = get_app_setting_data(instance=instance, bk_cloud_id=cluster.bk_cloud_id)
                    if err:
                        common_data["state"] = ReportStateType.ABNORMAL.value
                        common_data["msg"] = err
                        full_report = SqlserverFullBackupCheckReport.objects.create(**common_data)
                        log_report = SqlserverLogBackupCheckReport.objects.create(**common_data)
                        full_report.calc_failed_days()
                        log_report.calc_failed_days()
                        continue
                    if data["DATA_SCHEMA_GRANT"] != "all":
                        # 目前表示集群不做备份
                        common_data["state"] = ReportStateType.NORMAL.value
                        common_data["msg"] = "DATA_SCHEMA_GRANT != all, skip"
                        common_data["failed_days"] = 0
                        SqlserverFullBackupCheckReport.objects.create(**common_data)
                        SqlserverLogBackupCheckReport.objects.create(**common_data)
                        continue

                if len(get_routine_backup_dbs(cluster_id=cluster.id)) == 0:
                    common_data["state"] = ReportStateType.NORMAL.value
                    common_data["msg"] = _("检查到集群没有需要备份的数据库列表")
                    common_data["failed_days"] = 0
                    SqlserverFullBackupCheckReport.objects.create(**common_data)
                    SqlserverLogBackupCheckReport.objects.create(**common_data)
                    continue

            except Exception as err:
                # 如果校验发现失败了，记录当时的错误，不退出
                common_data["state"] = ReportStateType.ABNORMAL.value
                common_data["msg"] = str(err)
                full_report = SqlserverFullBackupCheckReport.objects.create(**common_data)
                log_report = SqlserverLogBackupCheckReport.objects.create(**common_data)
                full_report.calc_failed_days()
                log_report.calc_failed_days()
                continue

            try:
                # 完整备份校验
                self._check_full_backup_info_cluster(cluster)
            except Exception as err:
                # 如果校验发现失败了，记录当时的错误，不退出
                common_data["state"] = ReportStateType.ABNORMAL.value
                common_data["msg"] = str(err)
                full_report = SqlserverFullBackupCheckReport.objects.create(**common_data)
                full_report.calc_failed_days()
                continue

            try:
                # 日志备份校验
                self._check_log_backup_info_cluster(cluster)
            except Exception as err:
                # 如果校验发现失败了，记录当时的错误，不退出
                common_data["state"] = ReportStateType.ABNORMAL.value
                common_data["msg"] = str(err)
                log_report = SqlserverLogBackupCheckReport.objects.create(**common_data)
                log_report.calc_failed_days()
                continue

    # ==================== 全量备份校验 ====================

    def _check_full_backup_info_cluster(self, cluster: Cluster):
        """
        检查集群的全量备份文件信息是否存在
        1：对应的备份文件是否在备份记录（Model）
        2：对应的备份文件是否上传到备份系统
        """
        # 从 SQLServerBackupResult 模型查询全量备份记录
        backup_records = SQLServerBackupResult.objects.filter(
            cluster_id=cluster.id,
            backup_end_time__gte=self.full_backup_start_time,
            backup_end_time__lte=self.full_backup_end_time,
        ).values("backup_id", "dbname", "task_id", "file_cnt", "backup_host", "backup_port")
        backup_infos = list(backup_records)

        # 判断每一次的备份任务是否缺失记录
        check_result, is_normal = self._check_backup_info_from_model(backup_infos, "full")

        # 写入到巡检表
        full_report = SqlserverFullBackupCheckReport.objects.create(
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            cluster=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            state=ReportStateType.NORMAL.value if is_normal else ReportStateType.ABNORMAL.value,
            msg=check_result,
        )
        full_report.calc_failed_days()

    # ==================== 增量备份校验 ====================

    def _check_log_backup_info_cluster(self, cluster: Cluster):
        """
        检查集群的增量（日志）备份文件信息是否存在
        1：对应的备份文件是否在备份记录（Model）
        2：对应的备份文件是否上传到备份系统
        """
        # 从 SQLServerBinlogResult 模型查询日志备份记录
        backup_records = SQLServerBinlogResult.objects.filter(
            cluster_id=cluster.id,
            backup_end_time__gte=self.log_backup_start_time,
            backup_end_time__lte=self.log_backup_end_time,
        ).values("backup_id", "dbname", "task_id", "file_cnt", "host", "port")
        # 统一字段名，与全量备份保持一致（host/port -> backup_host/backup_port）
        backup_infos = []
        for record in backup_records:
            backup_infos.append(
                {
                    "backup_id": record["backup_id"],
                    "dbname": record["dbname"],
                    "task_id": record["task_id"],
                    "file_cnt": record["file_cnt"],
                    "backup_host": record["host"],
                    "backup_port": record["port"],
                }
            )

        # 判断每一次的备份任务是否缺失记录
        check_result, is_normal = self._check_backup_info_from_model(backup_infos, "log")

        # 写入到巡检表
        log_report = SqlserverLogBackupCheckReport.objects.create(
            bk_cloud_id=cluster.bk_cloud_id,
            bk_biz_id=cluster.bk_biz_id,
            cluster=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            state=ReportStateType.NORMAL.value if is_normal else ReportStateType.ABNORMAL.value,
            msg=check_result,
        )
        log_report.calc_failed_days()

    # ==================== 核心校验逻辑 ====================

    def _check_backup_info_from_model(self, backup_infos: list, tag: str) -> Tuple[str, bool]:
        """
        基于从 Model 查询出来的备份信息，按 backup_id 聚合后判断合法性
        @param backup_infos: 备份记录列表（dict 列表）
        @param tag: "full" 或 "log"，用于区分时间区间
        @return: (检查结果描述, 是否正常)
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
            # 如果查询到的备份文件为空，提前返回结果
            return _("查询集群没有备份记录 [{}-{}]".format(start_time, end_time)), False

        # 根据 backup_id 聚合备份记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_infos:
            backup_id__logs[log["backup_id"]].append(log)

        # 对每一份备份记录去重，相同的 backup_id 不能出现重复的 dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 遍历每个 backup_id 的备份任务
        for backup_id, logs in backup_id__valid_logs.items():
            if len(logs) == 0:
                # 如果这里聚合条数为0，直接返回异常
                check_result += _("备份 ID[{}] 找不到任何记录\n ".format(backup_id))
                is_normal = False
                continue

            # 按照备份任务，查询在备份系统上报情况
            task_ids = [i["task_id"] for i in logs]
            backup_host = logs[0]["backup_host"]
            backup_port = logs[0]["backup_port"]
            result = self._check_backup_file_in_backup_system(task_ids=task_ids)
            if result:
                check_result += f"[{backup_id}][{backup_host}:{backup_port}] {result}\n"
                is_normal = False

            # 判断每个备份任务的备份文件行数，跟 Model 中记录的 file_cnt 是否一致
            if len(logs) != logs[0]["file_cnt"]:
                check_result += _(
                    "备份 ID[{}][{}:{}] 备份文件记录数量不符合预期,预期数量: {}, 实际数量: {} \n ".format(
                        backup_id, backup_host, backup_port, logs[0]["file_cnt"], len(logs)
                    )
                )
                is_normal = False

        if not check_result:
            # 代表正常返回结果
            return _("备份ID [{}-{}] 检查正常".format(start_time, end_time)), is_normal

        return check_result, is_normal

    @staticmethod
    def _check_backup_file_in_backup_system(task_ids: list) -> str:
        """
        根据传入的 task_id 列表，查询备份文件是否成功上传到备份系统
        """
        max_length = 100
        check_result = []

        if len(task_ids) > max_length:
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
            return _("这次备份任务的某些文件在备份系统查询不到, 请检查")

        # 判断每个备份文件上传状态码，如果状态码不等于4（已上传完成），表示返回异常
        not_success_task_id_list = []
        for info in check_result:
            if info["status"] != 4:
                not_success_task_id_list.append(info["task_id"])
        if not_success_task_id_list:
            return _("部分文件上传状态不正常，请检查。 异常上传ID列表{}".format(not_success_task_id_list))

        return ""
