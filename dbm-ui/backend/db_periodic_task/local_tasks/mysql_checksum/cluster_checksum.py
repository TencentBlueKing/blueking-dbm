import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_report.enums import ReportStateType
from backend.db_report.models import ChecksumCheckReport, ChecksumInstance
from backend.utils.time import datetime2str

logger = logging.getLogger("celery")

# 最大从 bklog 拉取的条数
BKLOG_MAX_SIZE = 10000
BKLOG_INDEX = "{}_bklog.mysql_checksum_result".format(env.DBA_APP_BK_BIZ_ID)


@dataclass
class ChecksumResult:
    ip: str
    port: int
    master_ip: str = "0.0.0.0"
    master_port: int = 0
    reported: bool = False
    details: Dict[str, List[str]] = field(default_factory=dict)

    def add_not_consistent_table(self, db: str, table: str) -> None:
        tables = self.details.setdefault(db, [])
        if table not in tables:
            tables.append(table)


class ChecksumService:
    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)
        inner_role_filter = [InstanceInnerRole.SLAVE.value, InstanceInnerRole.REPEATER.value]
        self.instances = list(self.cluster.storageinstance_set.filter(instance_inner_role__in=inner_role_filter))
        machines = [inst.machine.ip for inst in self.instances]
        self.slaves = list(dict.fromkeys(machines))

    @staticmethod
    def build_time_ranges(now: Optional[datetime] = None) -> Tuple[datetime, datetime, datetime, datetime]:
        """
        - now: 当前时间（带时区）
        - start_time/end_time: 前天 00:00:00 - 23:59:59，数据是否一致的时间范围
        - log_start_time/log_end_time: 避免日志上报延迟，获取多天日志
        返回（start_time, end_time, log_start_time, log_end_time）
        """
        yesterday = now - timedelta(days=1)
        before_yesterday = now - timedelta(days=2)
        log_start_time = datetime(before_yesterday.year, before_yesterday.month, before_yesterday.day).astimezone(
            timezone.utc
        )
        log_end_time = datetime(now.year, now.month, now.day, 23, 59, 59).astimezone(timezone.utc)
        # 检查前天的校验结果
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day).astimezone(timezone.utc)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59).astimezone(timezone.utc)
        logger.info(
            "[auto_check_checksum] now:{} log_start_time:{} start_time:{} end_time:{} log_end_time:{}".format(
                now, log_start_time, start_time, end_time, log_end_time
            )
        )
        return start_time, end_time, log_start_time, log_end_time

    def fetch_bklog_logs(self, log_start_time: datetime, log_end_time: datetime) -> List[dict]:
        """
        从 BKLogApi 查询校验日志
        """
        if not self.slaves:
            return []

        machine_filter = [
            {"field": "serverIp", "operator": "is one of", "value": self.slaves},
            {"field": "cloudId", "operator": "is", "value": self.cluster.bk_cloud_id},
        ]
        try:
            resp = BKLogApi.esquery_search(
                {
                    "indices": BKLOG_INDEX,
                    "start_time": datetime2str(log_start_time),
                    "end_time": datetime2str(log_end_time),
                    "filter": machine_filter,
                    "start": 0,
                    "size": BKLOG_MAX_SIZE,
                    "sort_list": [["dtEventTimeStamp", "desc"]],
                }
            )
            hits = resp.get("hits", {}).get("hits", []) if resp else []
            return hits
        except Exception as e:
            logger.exception("failed to fetch logs from BKLogApi: %s", e)
            return []

    def calculate_failed_days(self, log_end_time: datetime) -> int:
        """
        计算连续失败天数：
        - 找最近一个正常（ReportStateType.NORMAL）的报告（按 id 倒序），如果找不到则取最早的一条报告（按 id 升序）
        - 以 log_end_time - report.create_at 的天数差返回
        - 如果没有任何报告则返回 1（首次失败）
        """
        report = (
            ChecksumCheckReport.objects.filter(cluster=self.cluster, state=ReportStateType.NORMAL.value)
            .order_by("-id")
            .first()
        )
        if not report:
            report = ChecksumCheckReport.objects.filter(cluster=self.cluster).order_by("id").first()
        if not report:
            return 1
        # 确保天数差至少为 1
        delta_days = max(1, (log_end_time - report.create_at).days)
        return delta_days

    def parse_logs_for_instances(
        self, hits: List[dict], start_time: datetime, end_time: datetime
    ) -> Tuple[List[ChecksumResult], List[ChecksumResult]]:
        """
        解析日志，返回 (fail_list, not_reported_list)
        - fail_list: 数据不一致的实例
        - not_reported_list: 没有上报的实例
        """
        # 初始化每个备库实例
        by_key = {}  # 键： (ip, port) -> ChecksumResult
        for inst in self.instances:
            key = (inst.machine.ip, inst.port)
            by_key[key] = ChecksumResult(ip=inst.machine.ip, port=inst.port)

        # 解析日志
        for hit in hits:
            src = hit.get("_source", {})
            log_raw = src.get("log")
            if not log_raw:
                continue
            log = json.loads(log_raw)
            if log.get("cluster_id", 0) == self.cluster.cluster_id:
                continue
            ip = log.get("ip")
            port = log.get("port")
            if ip is None or port is None:
                continue
            key = (ip, port)
            checksum = by_key.get(key)
            if not checksum:
                continue
            # 标记已上报，记录 master 信息
            checksum.reported = True
            checksum.master_ip = log.get("master_ip", "0.0.0.0")
            checksum.master_port = int(log.get("master_port") or 0)
            ts = log.get("ts")
            log_datetime = datetime.fromisoformat(ts)
            is_consistent = log.get("master_crc") == log.get("this_crc") and log.get("master_cnt") == log.get(
                "this_cnt"
            )
            if start_time <= log_datetime <= end_time and not is_consistent:
                checksum.add_not_consistent_table(log.get("db"), log.get("tbl"))
        fail = []
        not_reported = []
        for checksum in by_key.values():
            if not checksum.reported:
                not_reported.append(checksum)
            elif checksum.details:
                fail.append(checksum)

        return fail, not_reported

    def create_report_and_instances(
        self,
        fail_list: List[ChecksumResult],
        not_reported_list: List[ChecksumResult],
        start_time: datetime,
        end_time: datetime,
        log_start_time: datetime,
        log_end_time: datetime,
    ) -> ChecksumCheckReport:
        """
        在 db_report 中创建 ChecksumCheckReport 以及对应的 ChecksumInstance
        """
        err_msg = ""
        status = True
        state = ReportStateType.NORMAL.value

        if fail_list:
            status = False
            state = ReportStateType.ABNORMAL.value
            err_msg = "data is not consistent [{}]>[{}]".format(datetime2str(start_time), datetime2str(end_time))

        if not_reported_list:
            status = False
            state = ReportStateType.ABNORMAL.value
            if err_msg:
                err_msg += "; "
            err_msg += "no checksum logs found [{}]>[{}]".format(
                datetime2str(log_start_time), datetime2str(log_end_time)
            )

        if err_msg == "":
            err_msg = "success"

        fail_list.extend(not_reported_list)
        try:
            report = ChecksumCheckReport.objects.create(
                bk_biz_id=self.cluster.bk_biz_id,
                bk_cloud_id=self.cluster.bk_cloud_id,
                cluster=self.cluster.immute_domain,
                cluster_type=self.cluster.cluster_type,
                status=status,
                msg=err_msg,
                fail_slaves=len(fail_list),
                failed_days=self.calculate_failed_days(log_end_time),
                state=state,
            )
        except Exception:
            logger.exception("failed to create ChecksumCheckReport for cluster %s", self.cluster.immute_domain)
            raise

        # 创建每个失败或未上报实例的 ChecksumInstance
        for r in fail_list:
            try:
                ChecksumInstance.objects.create(
                    ip=r.ip,
                    port=r.port,
                    master_ip=r.master_ip,
                    master_port=r.master_port,
                    details=r.details,
                    report=report,
                )
            except Exception:
                logger.exception(
                    "failed to create ChecksumInstance for cluster %s instance %s:%s",
                    self.cluster.immute_domain,
                    r.ip,
                    r.port,
                )

        return report
