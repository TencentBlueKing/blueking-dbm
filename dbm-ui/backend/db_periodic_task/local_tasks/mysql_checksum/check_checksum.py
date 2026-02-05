import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from blueapps.core.celery.celery import app
from celery import shared_task
from django.utils.translation import gettext as _

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.local_tasks.mysql_checksum.cluster_checksum import ChecksumService
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.ticket.builders.common.constants import MYSQL_CHECKSUM_TABLE, MySQLDataRepairTriggerMode
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import date2str

logger = logging.getLogger("celery")


def check_mysql_checksum():
    """
    检查是否存在校验报告，查询近3天的报告，避免上报延迟等情况
    检查是否存在数据不一致，检查前天的报告（主库执行校验任务，备库第二天上报校验结果，巡检再落后一天，所以检查前天报告）
    """

    local_tz = datetime.now().astimezone().tzinfo
    now = datetime.now(local_tz)

    cluster_type_filter = [ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value]
    cluster_ids = list(Cluster.objects.filter(cluster_type__in=cluster_type_filter).values_list("id", flat=True))
    total = len(cluster_ids)
    logger.info("[auto_check_checksum] scheduling checksum check for %d clusters", total)
    for index, cluster_id in enumerate(cluster_ids):
        countdown = calculate_countdown(count=total, index=index, duration=TimeUnit.HOUR)
        logger.info("cluster(%s) checksum will be run after %s seconds.", cluster_id, countdown)
        # 每个集群在独立任务中执行
        with start_new_span(check_cluster_checksum):
            # 延迟调度，均摊到一小时
            check_cluster_checksum.apply_async(
                kwargs={"index": index, "cluster_id": int(cluster_id), "now": now},
                countdown=countdown,
            )


@app.task
def check_cluster_checksum(index: int, cluster_id: int, now: Optional[datetime] = None):
    """
    单个集群的检查任务：
    - 获取集群、实例信息
    - 解析是否有数据不一致或未上报实例
    - 写入 db_report 表
    """
    cluster_obj = Cluster.objects.get(pk=cluster_id)
    logger.info(
        "begin generate checksum report index = {}, immute_domain = {}".format(index, cluster_obj.immute_domain)
    )

    cluster_task = ChecksumService(cluster_id)

    end_time = now
    start_time = end_time - timedelta(hours=24)

    # start_time, end_time, log_start_time, log_end_time = cluster_task.build_time_ranges(now)
    # hits = cluster_task.fetch_bklog_logs(log_start_time, log_end_time)
    # fail_list, not_reported_list = cluster_task.parse_logs_for_instances(hits, start_time, end_time)
    fail_list, not_reported_list = cluster_task.query_checksum_via_drs(
        cluster_obj.bk_cloud_id
    )  # , start_time, end_time
    logger.info("query {} checksum result finish".format(cluster_obj.immute_domain))
    try:
        report = cluster_task.create_report_and_instances(
            fail_list, not_reported_list, start_time, end_time  # , log_start_time, log_end_time
        )
        logger.info(
            "created checksum report %d for index = %d cluster = %s (fail_count = %d)",
            report.id,
            index,
            cluster_task.cluster.immute_domain,
            len(fail_list),
        )
    except Exception:  # noqa
        logger.exception(
            "failed to persist checksum report for index = %d cluster = %s", index, cluster_task.cluster.immute_domain
        )
        return

    # 基于 fail_list 生成修复单据
    if not fail_list:
        return

    logger.info("found %d inconsistent instances for cluster %s", len(fail_list), cluster_task.cluster.immute_domain)

    db_type = ClusterType.cluster_type_to_db_type(cluster_obj.cluster_type)
    dba, second_dba, other_dba = DBAdministrator.get_dba_for_db_type(cluster_obj.bk_biz_id, db_type)

    try:
        # 按 master_ip:master_port 聚合不一致的 slave 实例
        master_to_slaves = defaultdict(set)
        for fail in fail_list:
            master_key = f"{fail.master_ip}:{fail.master_port}"
            master_to_slaves[master_key].add(f"{fail.ip}:{fail.port}")

        ticket_details = {
            # "非innodb表是否修复"这个参数与校验保持一致，默认为false
            "is_sync_non_innodb": False,
            "is_ticket_consistent": False,
            "checksum_table": MYSQL_CHECKSUM_TABLE,
            "trigger_type": MySQLDataRepairTriggerMode.ROUTINE.value,
            # 为了兼容时区问题, 修复范围扩大一天
            "start_time": date2str(now - timedelta(hours=24)),
            "end_time": date2str(now + timedelta(hours=24)),
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "master": _ip_port_to_repair_instance_info(cluster_obj, master),
                    "slaves": [
                        {
                            **_ip_port_to_repair_instance_info(cluster_obj, slave),
                            "is_consistent": False,
                        }
                        for slave in slaves
                    ],
                }
                for master, slaves in master_to_slaves.items()
            ],
        }
        ticket_type = getattr(TicketType, f"{db_type.upper()}_DATA_REPAIR")

        _create_ticket.apply_async(
            kwargs={
                "ticket_type": ticket_type,
                "creator": dba[0],
                "bk_biz_id": cluster_obj.bk_biz_id,
                "remark": _("集群存在数据不一致，自动创建的数据修复单据"),
                "details": ticket_details,
                "helpers": [*second_dba, *other_dba],
            }
        )

    except Exception:  # noqa
        logger.exception("failed to create data repair ticket for cluster %s", cluster_obj.immute_domain)


@shared_task
def _create_ticket(
    ticket_type, creator, bk_biz_id, remark, details, auto_execute=True, send_msg_config=None, helpers=None
) -> None:
    """创建一个新单据"""
    Ticket.create_ticket(ticket_type, creator, bk_biz_id, remark, details, auto_execute, send_msg_config, helpers)


def _ip_port_to_repair_instance_info(cluster_obj: Cluster, ip_port: str) -> dict:
    ip, port = ip_port.split(":")
    inst_obj = StorageInstance.objects.get(cluster=cluster_obj, machine__ip=ip, port=port)
    return {
        "id": inst_obj.id,
        "bk_biz_id": cluster_obj.bk_biz_id,
        "ip": ip,
        "port": int(port),
        "bk_host_id": inst_obj.machine.bk_host_id,
        "bk_cloud_id": cluster_obj.bk_cloud_id,
    }
