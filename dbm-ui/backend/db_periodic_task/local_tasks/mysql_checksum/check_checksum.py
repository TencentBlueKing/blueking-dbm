import logging
from datetime import datetime
from typing import Optional

from blueapps.core.celery.celery import app
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.local_tasks.mysql_checksum.cluster_checksum import ChecksumService
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("celery")


def check_mysql_checksum():
    """
    检查是否存在校验报告，查询近3天的报告，避免上报延迟等情况
    检查是否存在数据不一致，检查前天的报告（主库执行校验任务，备库第二天上报校验结果，巡检再落后一天，所以检查前天报告）
    """

    now = datetime.now(timezone.utc)
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
                kwargs={"cluster_id": int(cluster_id), "now": now},
                countdown=countdown,
            )


@app.task
def check_cluster_checksum(cluster_id: int, now: Optional[datetime] = None):
    """
    单个集群的检查任务：
    - 获取集群、实例信息
    - 从 BKLog 拉取日志
    - 解析是否有数据不一致或未上报实例
    - 写入 db_report 表
    """
    cluster_task = ChecksumService(cluster_id)
    start_time, end_time, log_start_time, log_end_time = cluster_task.build_time_ranges(now)
    hits = cluster_task.fetch_bklog_logs(log_start_time, log_end_time)
    fail_list, not_reported_list = cluster_task.parse_logs_for_instances(hits, start_time, end_time)
    try:
        report = cluster_task.create_report_and_instances(
            fail_list, not_reported_list, start_time, end_time, log_start_time, log_end_time
        )
        logger.info(
            "created checksum report %d for cluster %s (fail_count=%d)",
            report.id,
            cluster_task.cluster.immute_domain,
            len(fail_list),
        )
    except Exception:
        logger.exception("failed to persist checksum report for cluster %s", cluster_task.cluster.immute_domain)
        return
