import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Tuple

from django.core.exceptions import ObjectDoesNotExist

from backend import env
from backend.components import DRSApi
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.db_report.enums import ReportStateType
from backend.db_report.models import ChecksumCheckReport, ChecksumInstance
from backend.flow.consts import InstanceStatus
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
        self.instances = []
        inner_role_filter = [InstanceInnerRole.SLAVE.value, InstanceInnerRole.REPEATER.value]

        # 只获取 standby master 的下级实例
        i_set = set()
        for ins in self.cluster.storageinstance_set.filter(instance_inner_role__in=inner_role_filter).exclude(
            status=InstanceStatus.UNAVAILABLE
        ):
            if StorageInstanceTuple.objects.filter(
                receiver=ins, ejector__instance_inner_role=InstanceInnerRole.MASTER
            ).exists():
                i_set.add(ins)
        self.instances = list(i_set)
        machines = [inst.machine.ip for inst in self.instances]
        self.slaves = list(dict.fromkeys(machines))

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

    def query_checksum_via_drs(
        self, bk_cloud_id: int  # , start_time: datetime, end_time: datetime
    ) -> Tuple[List[ChecksumResult], List[ChecksumResult]]:
        fail: List[ChecksumResult] = []
        not_reported: List[ChecksumResult] = []

        for inst in self.instances:  # 这是集群的 slave, repeater
            ip = inst.machine.ip
            port = inst.port

            try:
                # 如果 dbha 了是没有的
                master_ins = StorageInstanceTuple.objects.get(receiver=inst).ejector
            except ObjectDoesNotExist:
                continue

            master_ip = master_ins.machine.ip
            master_port = master_ins.port

            checksum = ChecksumResult(master_ip=master_ip, master_port=master_port, ip=ip, port=port)

            drs_raw_res = DRSApi.rpc(
                {
                    "bk_cloud_id": bk_cloud_id,
                    "addresses": [inst.ip_port],
                    "cmds": [
                        "SELECT COUNT(*) AS cnt FROM infodba_schema.checksum_history \
                        WHERE ts >= DATE_SUB(NOW(), INTERVAL 24 HOUR) AND (master_ip = '{}' AND master_port = {})".format(
                            master_ip,
                            master_port,
                        ),
                        "SELECT db, tbl, COUNT(*) AS inconsistent_cnt FROM infodba_schema.checksum_history \
                        WHERE ts >= DATE_SUB(NOW(), INTERVAL 24 HOUR) \
                        AND (this_cnt <> master_cnt OR this_crc <> master_crc) \
                        AND (master_ip = '{}' AND master_port = {}) GROUP BY db, tbl".format(
                            master_ip,
                            master_port,
                        ),
                    ],
                }
            )

            if drs_raw_res[0]["error_msg"]:
                raise Exception(drs_raw_res[0]["error_msg"])  # noqa
            cmd_results = drs_raw_res[0]["cmd_results"]

            if cmd_results[0]["error_msg"]:
                raise Exception(cmd_results[0]["error_msg"])  # noqa
            checksum_cnt = int(cmd_results[0]["table_data"][0]["cnt"])

            if checksum_cnt <= 0:
                not_reported.append(checksum)
            else:
                if cmd_results[1]["error_msg"]:
                    raise cmd_results[1]["error_msg"]  # noqa

                if len(cmd_results[1]["table_data"]) > 0:
                    checksum.reported = True
                    checksum.master_ip = master_ip
                    checksum.master_port = master_port
                    for inconsistent_row in cmd_results[1]["table_data"]:
                        checksum.add_not_consistent_table(inconsistent_row["db"], inconsistent_row["tbl"])

                    fail.append(checksum)

        return fail, not_reported

    def create_report_and_instances(
        self,
        fail_list: List[ChecksumResult],
        not_reported_list: List[ChecksumResult],
        start_time: datetime,
        end_time: datetime,
        # log_start_time: datetime,
        # log_end_time: datetime,
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
            err_msg += "no checksum logs found [{}]>[{}]".format(datetime2str(start_time), datetime2str(end_time))

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
                failed_days=self.calculate_failed_days(end_time),
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
            except Exception:  # noqa
                logger.exception(
                    "failed to create ChecksumInstance for cluster %s instance %s:%s",
                    self.cluster.immute_domain,
                    r.ip,
                    r.port,
                )

        return report
