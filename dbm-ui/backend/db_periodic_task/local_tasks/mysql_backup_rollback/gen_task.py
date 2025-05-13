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
import heapq
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Union

from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskStatus
from backend.db_services.mysql.fixpoint_rollback.handlers import FixPointRollbackHandler
from backend.env import MYSQL_BACKUPRECOVER_BIZ_ID, MYSQL_BACKUPRECOVER_MCH_LABELS_ID
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise import MySQLRollbackExerciseFlow
from backend.ticket.constants import ResourceApplyErrCode
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


# 定义任务状态的常量


def get_resource_list() -> list:
    """
    获取资源列表
    """
    params = {
        "resource_type": "mysql",
        "for_bizs": [MYSQL_BACKUPRECOVER_BIZ_ID],
        "labels": [MYSQL_BACKUPRECOVER_MCH_LABELS_ID],
    }
    resp = DBResourceApi.resource_list(params=params, raw=True)
    if resp["code"] != 0:
        logger.error(_("获取资源列表失败: {}").format(resp.get("message", "")))
        return []
    resource_list = resp.get("data", [])
    if not resource_list:
        logger.info(_("没有可用的资源_"))
        return []
    return resource_list


# bytes 转成 GB
def bytes_to_gb(bytes: int) -> float:
    return bytes / 1024 / 1024 / 1024


def build_resource_apply_params(task_id: str, min_disk_size: float) -> Dict[str, Union[str, Any]]:
    """Build resource application parameters

    Args:
        task_id: The unique task identifier
        min_disk_size: Minimum disk size required in GB

    Returns:
        Dict containing all parameters needed for resource application
    """
    return {
        "for_biz_id": MYSQL_BACKUPRECOVER_BIZ_ID,
        "resource_type": "mysql",
        "task_id": task_id,
        "operator": "system",
        "details": [
            {
                "count": 1,
                "group_mark": "backup_recovery_exercise_0",
                "labels": [MYSQL_BACKUPRECOVER_MCH_LABELS_ID],
                "storage_spec": [
                    {
                        "max": 2147483647,
                        "min": min_disk_size,
                    }
                ],
            }
        ],
    }


def calculate_min_disk_size(total_filesize: int) -> float:
    """Calculate minimum disk size required for backup recovery

    Args:
        total_filesize: Backup file size in bytes

    Returns:
        Minimum disk size required in GB
    """
    min_disk_size = bytes_to_gb(total_filesize) * 2  # Double the backup size
    return max(min_disk_size, 50)  # Ensure minimum of 50GB


def get_last_week_range():
    """
    Get the start (Monday) and end (Sunday) datetime of last week
    Returns:
        tuple: (start_time, end_time) where both are datetime objects in UTC
    """
    today = datetime.now(timezone.utc)
    # Find the most recent Monday (0=Monday, 6=Sunday)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    # Set time to start of day (00:00:00)
    start_time = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # Set time to end of day (23:59:59.999999)
    end_time = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_time, end_time


# 查询备份记录生成回档任务
def gen_rollback_task():
    rs_list = get_resource_list()
    if not rs_list:
        logger.info(_("没有可用的资源_，跳过回档任务生成_"))
        return
    rs_count = rs_list["count"]
    if rs_count == 0:
        logger.info(_("没有可用的资源，跳过回档任务生成"))
        return
    clusters = get_exercise_clusters(rs_count)
    for cluster in clusters:
        handler = FixPointRollbackHandler(cluster.id, check_full_backup=True)
        start_time, end_time = get_last_week_range()
        backup_records = handler.query_recover_backup_logs(start_time, end_time)
        if not backup_records:
            continue
        backup_records.sort(key=lambda x: x["backup_time"], reverse=False)
        # 选择第一个备份记录生成回档任务
        backup_record = backup_records[0]
        if not backup_record:
            logger.info("no backup record found")
            continue
        logger.info("exercise backup_record: {}".format(backup_record))
        backup_id = backup_record["backup_id"]
        root_id = generate_root_id()
        task = MySQLBackupRecoverTask(
            bk_biz_id=backup_record["bk_biz_id"],
            cluster_id=cluster.id,
            cluster_domain=backup_record.get("cluster_address", ""),
            cluster_type=cluster.cluster_type,
            backup_id=backup_id,
            backup_begin_time=backup_record["backup_begin_time"],
            backup_end_time=backup_record["backup_end_time"],
            backup_total_size=backup_record["total_filesize"],
            backup_type=backup_record["backup_type"],
            backup_tool=backup_record["backup_tool"],
            time_zone=backup_record["time_zone"],
            task_id=root_id,
            task_status=TaskStatus.GENERATED,
            creator="system",
            updater="system",
        )
        # Calculate minimum disk size required
        min_disk_size = calculate_min_disk_size(backup_record["total_filesize"])
        # 申请资源
        apply_params = build_resource_apply_params(root_id, min_disk_size)
        resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
        if resp["code"] != 0:
            if resp["code"] == ResourceApplyErrCode.RESOURCE_LAKE:
                logger.error(_("资源不足申请失败，请前往补货后重试{}").format(resp.get("message")))
                continue
            elif resp["code"] in ResourceApplyErrCode.get_values():
                logger.error(
                    _("资源池服务出现系统错误，请联系管理员或稍后重试。错误信息: [{}]{}").format(
                        ResourceApplyErrCode.get_choice_label(resp["code"]), resp.get("message")
                    )
                )
                continue
            else:
                logger.error(_("资源池相关服务出现未知异常，请联系管理员处理。错误信息: [{}]{}").format(resp["code"], resp.get("message")))
                continue
        else:
            task.task_status = TaskStatus.RESOURCE_APPLIED
            task.save()
        # 申请资源成功后，获取资源申请结果
        try:
            resource_request_id, apply_data = resp["request_id"], resp["data"]
            logger.info(f"resource_request_id: {resource_request_id}, apply_data: {apply_data}")
            mch_info = apply_data[0]["data"][0]
            rollback_host = {
                "ip": mch_info["ip"],
                "bk_host_id": mch_info["bk_host_id"],
                "bk_cloud_id": mch_info["bk_cloud_id"],
                "bk_biz_id": mch_info["bk_biz_id"],
            }
            # 提交演练任务

            flow_context = {
                "uid": root_id,
                "ticket_type": "MYSQL_ROLLBACK_EXERCISE",
                "exercise_cluster_id": cluster.id,
                "backup_id": backup_id,
                "rollback_host": rollback_host,
                "bk_biz_id": MYSQL_BACKUPRECOVER_BIZ_ID,
                "backupinfo": backup_record,
                "created_by": "system",
                "backupinfo": backup_record,
                "labels": mch_info["labels"],
            }
            task.task_status = TaskStatus.COMMIT_SUCCESS
            task.save()
            flow = MySQLRollbackExerciseFlow(root_id=root_id, data=flow_context)
            flow.run()
        except Exception as e:
            logger.exception("rollback exercise flow run failed: {}".format(e))
            task.task_status = TaskStatus.COMMIT_FAILED
            task.task_info = str(e)
            task.save()


class Task:
    def __init__(self, priority, cluster):
        self.priority = priority
        self.cluster = cluster

    # 定义比较规则（优先级数字小的先出队）
    def __lt__(self, other):
        return self.priority < other.priority


def get_exercise_clusters(num: int) -> list:
    """_summary_
    获取待演练的集群
    """
    recover_success_map = {}
    exclude_biz_ids = MySQLBackupRecoverTask.get_all_practiced_biz_ids()
    exclude_cluster_id = MySQLBackupRecoverTask.get_all_practiced_cluster_ids()
    # 先获取未演练的业务的集群
    clusters = Cluster.objects.exclude(
        bk_biz_id__in=exclude_biz_ids,
    )
    if not clusters.exists():
        # 如果都演练过的话,则选择没有演练过的集群
        clusters = Cluster.objects.exclude(
            id__in=exclude_cluster_id,
        )
        if not clusters.exists():
            clusters = Cluster.objects.filter(
                cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA, ClusterType.TenDBSingle]
            )
            result = (
                MySQLBackupRecoverTask.objects.filter(
                    task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS],
                )
                .values("cluster_domain")
                .annotate(total=Count("*"))
                .order_by("total")
            )
            recover_success_map = {item["cluster_domain"]: item["total"] for item in result}

    cluster_biz_map = defaultdict(list)
    for cluster in clusters:
        recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
        heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(100 - recover_success_cnt, cluster))

    rs = []
    for bk_biz_id, pq in cluster_biz_map.items():
        if not pq:
            break
        task = heapq.heappop(pq)
        rs.append(task.cluster)
        if len(rs) >= num:
            break
    return rs


def return_resource(params: Dict[str, Any]) -> None:
    """
    归还资源
    :param params: 归还资源的参数
        params = {
            "resource_type": "mysql",
            "for_biz": MYSQL_BACKUPRECOVER_BIZ_ID,
            "bk_biz_id": mch_info["bk_biz_id"],
            "hosts": [
                {
                    "ip": mch_info["ip"],
                    "bk_host_id": mch_info["bk_host_id"],
                    "bk_cloud_id": mch_info["bk_cloud_id"],
                }
            ],
            "labels": mch_info["lables"],
            "operator": "system",
        }
    """
    try:
        resp = DBResourceApi.resource_import(params=params, raw=True)
        if resp["code"] != 0:
            logger.error(_("归还资源失败: {}").format(resp.get("message", "")))
    except Exception as e:
        logger.exception(_("归还资源时发生异常: {e}"))
        raise e
