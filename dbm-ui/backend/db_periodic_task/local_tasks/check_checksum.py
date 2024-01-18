import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKLogApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.db_report.models import ChecksumCheckReport, ChecksumInstance
from backend.utils.time import datetime2str

logger = logging.getLogger("celery")


class Checksum:
    """备库实例的校验结果"""

    def __init__(self, slave_ip, slave_port):
        self.ip = slave_ip
        self.port = slave_port
        self.master_ip = ""
        self.master_port = 0
        # 是否存在上报校验结果
        self.reported = False
        self.details = defaultdict(list)

    # 添加数据不一致的库、表
    def add_not_consistent_table(self, db, table):
        if table not in self.details[db]:
            self.details[db].append(table)


# @register_periodic_task(run_every=crontab(minute="*/1"))
@register_periodic_task(run_every=crontab(day_of_week="2,3,4,5,6", hour="3", minute="53"))
def auto_check_checksum():
    """检查每天的校验结果，存入db_report数据库"""
    # 主库执行校验任务，备库第二天上报校验结果
    # 周六、周日主库不校验、备库不上报
    # 日志平台获取日志
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    before_yesterday = now - timedelta(days=2)
    # 查询近两天的数据，避免日志上报延迟等情况
    log_start_time = datetime(before_yesterday.year, before_yesterday.month, before_yesterday.day).astimezone(
        timezone.utc
    )
    start_time = datetime(yesterday.year, yesterday.month, yesterday.day).astimezone(timezone.utc)
    end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59).astimezone(timezone.utc)
    logger.info(
        "[auto_check_checksum] now:{} log_start_time:{} start_time:{} end_time:{}".format(
            now, log_start_time, start_time, end_time
        )
    )
    cluster_type_filter = [ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value]
    cluster_ids = list(Cluster.objects.filter(cluster_type__in=cluster_type_filter).values_list("id", flat=True))
    count = len(cluster_ids)
    # 所有集群的校验结果检查，在一个小时内完成
    for index, cluster_id in enumerate(cluster_ids):
        countdown = calculate_countdown(count=count, index=index, duration=TimeUnit.HOUR)
        logger.info("cluster({}) checksum will be run after {} seconds.".format(cluster_id, countdown))
        check_cluster_checksum.apply_async(
            kwargs={
                "cluster_id": cluster_id,
                "start_time": start_time,
                "end_time": end_time,
                "log_start_time": log_start_time,
            },
            countdown=countdown,
        )


@app.task
def check_cluster_checksum(cluster_id: int, start_time: datetime, end_time: datetime, log_start_time: datetime):
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        # 忽略不在dbm meta信息中的集群
        logger.error(_("无法在dbm meta中查询到集群{}的相关信息，请排查该集群的状态".format(cluster_id)))
        return
    # 备库以及repeater上报校验数据
    inner_role_filter = [InstanceInnerRole.SLAVE.value, InstanceInnerRole.REPEATER.value]
    instances = cluster.storageinstance_set.filter(instance_inner_role__in=inner_role_filter)
    machines = [instance.machine.ip for instance in instances]
    machines = list(tuple(machines))
    if len(machines) <= 0:
        return
    # BKLogApi.esquery_search的过滤条件filter
    # 获取近2天的日志
    machine_filter = [
        {"field": "serverIp", "operator": "is one of", "value": machines},
        {"field": "cloudId", "operator": "is", "value": cluster.bk_cloud_id},
    ]

    resp = BKLogApi.esquery_search(
        {
            "indices": "{}_bklog.mysql_checksum_result".format(env.DBA_APP_BK_BIZ_ID),
            "start_time": datetime2str(log_start_time),
            "end_time": datetime2str(end_time),
            "filter": machine_filter,
        }
    )

    # 数据不一致的实例列表
    fail = []
    # 没有校验的实例列表
    not_reported = []
    err_msg = ""
    status = True
    # 检查每个备库实例的校验日志
    for instance in instances:
        slave_ip = instance.machine.ip
        slave_port = instance.port
        checksum = Checksum(slave_ip, slave_port)
        for hit in resp["hits"]["hits"]:
            log = json.loads(hit["_source"]["log"])
            print(log)
            # 过滤出本集群本实例的日志
            if log["cluster_id"] == cluster.id:
                if log["ip"] == slave_ip and log["port"] == slave_port:
                    checksum.reported = True
                    checksum.master_port = log["master_port"]
                    log_timestamp = round(int(hit["_source"]["dtEventTimeStamp"]) / 1000)
                    log_datetime = datetime.fromtimestamp(log_timestamp).astimezone(timezone.utc)
                    is_consistent = log["master_crc"] == log["this_crc"] and log["master_cnt"] == log["this_cnt"]
                    # 检查校验日志，数据是否一致；近1天上报的日志中数据不一致，记录到报告中
                    if (not is_consistent) and log_datetime >= start_time:
                        checksum.add_not_consistent_table(log["db"], log["tbl"])
        if not checksum.reported:
            not_reported.append(checksum)
        elif len(checksum.details) > 0:
            fail.append(checksum)

    if len(fail) > 0:
        err_msg = _("数据不一致")
        status = False
    if len(not_reported) > 0:
        status = False
        if err_msg == "":
            err_msg = _("近2天未校验")
        else:
            err_msg = err_msg + _(";近2天未校验")
    fail.extend(not_reported)
    # 集群的校验结果
    report = ChecksumCheckReport.objects.create(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        status=status,
        msg=err_msg,
        # 校验status失败的备库实例的个数
        fail_slaves=len(fail),
    )
    for f in fail:
        # 每个备库实例的校验结果
        ChecksumInstance.objects.create(
            ip=f.ip,
            port=f.port,
            master_ip=f.master_ip,
            master_port=f.master_port,
            details=f.details,
            report=report,
        )
