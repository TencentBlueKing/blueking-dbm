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
import logging
from django.utils import timezone
from backend.db_report.enums import ReportStateType
from backend import env
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoNode

logger = logging.getLogger("root")
dev_env = str(env.REPO_VERSION_FOR_DEV)


def dev_debug(msg: str):
    """
    A simple logging function to log debug messages.
    """
    if dev_env != "":
        # Only log in dev environment
        logger.debug("env:{} msg:{}".format(dev_env, msg))


def addr(node: MongoNode) -> str:
    """
    return the address of the node in the format "ip:port"
    """
    if node is None:
        return ""
    return f"{node.ip}:{node.port}"


class ClusterReport:
    cluster: MongoDBCluster
    report_day: int
    subtype: str
    records: dict[str, list[MongodbBackupCheckReport]]

    def __init__(self, cluster: MongoDBCluster, report_day: int, subtype: str):
        self.cluster = cluster
        self.report_day = report_day
        self.subtype = subtype
        self.records = {
            ReportStateType.NORMAL.value: [],
            ReportStateType.WARNING.value: [],
            ReportStateType.ABNORMAL.value: [],
        }

    def append(self, state: str, shard: str, instance: str, msg: str):
        """添加记录"""
        self.records[state].append(
            {
                "shard": shard,
                "instance": instance,
                "state": state,
                "msg": msg,
            }
        )

    def get_exceed_days(self, state: str):
        """生成连续天数"""
        return 0

    def make_skip_record(self, reason: str) -> list[MongodbBackupCheckReport]:
        """生成跳过记录"""
        return [
            MongodbBackupCheckReport(
                creator="",
                subtype=self.subtype,
                report_day=self.report_day,
                bk_biz_id=self.cluster.bk_biz_id,
                bk_cloud_id=self.cluster.bk_cloud_id,
                cluster=self.cluster.immute_domain,
                cluster_id=self.cluster.cluster_id,
                cluster_type=self.cluster.cluster_type,
                shard="all",
                instance="all",
                status=True,
                state=ReportStateType.NORMAL.value,
                msg=reason,
                failed_days=self.get_exceed_days(ReportStateType.NORMAL.value),
            )
        ]

    def make_records(self):
        """生成报告记录"""
        normal_num = len(self.records[ReportStateType.NORMAL.value])
        abnormal_num = len(self.records[ReportStateType.ABNORMAL.value])
        warning_num = len(self.records[ReportStateType.WARNING.value])
        total_num = normal_num + abnormal_num + warning_num
        cluster_state = ReportStateType.NORMAL.value
        cluster_status = True
        cluster_msg = f"{total_num} checks, normal: {normal_num}"

        if warning_num > 0:
            cluster_status = False
            cluster_state = ReportStateType.WARNING.value
            cluster_msg += f", warning: {warning_num}"

        if abnormal_num > 0:
            cluster_status = False
            cluster_state = ReportStateType.ABNORMAL.value
            cluster_msg += f", abnormal: {abnormal_num}"

        if total_num == 0:
            cluster_status = False
            cluster_state = ReportStateType.ABNORMAL.value
            cluster_msg = "no check record"

        records = []

        # 添加集群记录, 用于统计全局的正常、异常、警告数量
        # 可能会返回多条记录，第一条为集群记录，其他为分片的记录
        cluster_row = MongodbBackupCheckReport(
            creator="",
            subtype=self.subtype,
            report_day=self.report_day,
            bk_biz_id=self.cluster.bk_biz_id,
            bk_cloud_id=self.cluster.bk_cloud_id,
            cluster=self.cluster.immute_domain,
            cluster_id=self.cluster.cluster_id,
            cluster_type=self.cluster.cluster_type,
            shard="all",
            instance="all",
            status=cluster_status,
            state=cluster_state,
            msg=cluster_msg,
            failed_days=self.get_exceed_days(cluster_state),
        )
        records.append(cluster_row)
        # 处理异常和警告状态的记录
        for state_type in [ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value]:
            for record in self.records[state_type]:
                if record["shard"] == "all":
                    continue
                records.append(
                    MongodbBackupCheckReport(
                        creator="",
                        subtype=self.subtype,
                        report_day=self.report_day,
                        bk_biz_id=self.cluster.bk_biz_id,
                        bk_cloud_id=self.cluster.bk_cloud_id,
                        cluster=self.cluster.immute_domain,
                        cluster_id=self.cluster.cluster_id,
                        cluster_type=self.cluster.cluster_type,
                        shard=record["shard"],
                        instance=record["instance"],
                        status=record["state"] == ReportStateType.NORMAL.value,
                        state=record["state"],
                        msg=record["msg"],
                        failed_days=self.get_exceed_days(record["state"]),
                    )
                )
        return records


class RecordBatchOps:
    """记录批量操作类 用于批量操作记录, 用于处理failed_days字段"""

    records: list[MongodbBackupCheckReport] = []
    sub_type: str
    report_day: int

    def __init__(self, sub_type: str, report_day: int):
        self.sub_type = sub_type
        self.report_day = report_day
        self.records = []

    def append(self, record: MongodbBackupCheckReport):
        self.records.append(record)

    def bulk_create(self):
        if not self.records:
            return
        self.fill_failed_days()
        MongodbBackupCheckReport.objects.bulk_create(self.records)
        self.records = []

    def fill_failed_days(self):
        failed_days = self.get_continuous_days()
        for record in self.records:
            record.failed_days = failed_days.get(self.get_continuous_key(record), 0) + 1

    def get_prev_report_day(self) -> int:
        # yyyymmdd -1
        report_day = datetime.strptime(str(self.report_day), "%Y%m%d") - timedelta(days=1)
        return int(report_day.strftime("%Y%m%d"))

    def get_continuous_key(self, row: MongodbBackupCheckReport) -> str:
        return f"{row.cluster_id}:{row.shard}:{row.instance}:{row.state}"

    def get_continuous_days(self):
        rows = MongodbBackupCheckReport.objects.filter(
            cluster_id__in=[record.cluster_id for record in self.records],
            subtype=self.sub_type,
            report_day=self.get_prev_report_day(),
        )
        continuous_days = defaultdict(int)
        for row in rows:
            continuous_days[self.get_continuous_key(row)] = row.failed_days
        return continuous_days

    def delete_old_record(self, days: int = 360) -> int:
        """删除旧的记录"""
        deleted_count, unused = MongodbBackupCheckReport.objects.filter(
            create_at__lte=timezone.now() - timedelta(days=days), subtype=self.sub_type
        ).delete()
        return deleted_count

    def delete_today_record(self) -> int:
        """删除今天的记录"""
        deleted_count, unused = MongodbBackupCheckReport.objects.filter(
            report_day=self.report_day, subtype=self.sub_type
        ).delete()
        return deleted_count
