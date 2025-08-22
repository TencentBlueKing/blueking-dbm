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
import random
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
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse
from backend.ticket.constants import ResourceApplyErrCode, TicketType
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


def build_resource_apply_params(task_id: str, min_disk_size: int, mysql_version: str) -> Dict[str, Union[str, Any]]:
    """Build resource application parameters

    Args:
        task_id: The unique task identifier
        min_disk_size: Minimum disk size required in GB
        mysql_version: MySQL version string

    Returns:
        Dict containing all parameters needed for resource application
    """

    # 基础参数
    details = {
        "count": 1,
        "group_mark": "backup_recovery_exercise_0",
        "labels": [MYSQL_BACKUPRECOVER_MCH_LABELS_ID],
        "os_type": "Linux",
        "storage_spec": [
            {
                "max": 2147483647,
                "min": min_disk_size,
            }
        ],
    }

    # 如果MySQL版本大于等于8.0，则排除tlinux 1.2操作系统

    if mysql_version and mysql_version_parse(mysql_version) >= 8000000:
        details["os_names"] = ["tliunx-1.2", ""]
        details["exclude_os_name"] = True

    return {
        "for_biz_id": MYSQL_BACKUPRECOVER_BIZ_ID,
        "resource_type": "mysql",
        "task_id": task_id,
        "operator": "system",
        "details": [details],
    }


def calculate_min_disk_size(total_filesize: int) -> int:
    """Calculate minimum disk size required for backup recovery

    Args:
        total_filesize: Backup file size in bytes

    Returns:
        Minimum disk size required in GB
    """
    min_disk_size = bytes_to_gb(total_filesize) * 6  # Double the backup size
    return int(max(min_disk_size, 200))  # Ensure minimum of 50GB


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


# 查询集群是否存在备份记录
def cluster_has_backup_record(cluster_id: int) -> bool:
    """
    查询集群是否存在备份记录
    """
    handler = FixPointRollbackHandler(cluster_id, check_full_backup=True)
    start_time, end_time = get_last_week_range()
    backup_records = handler.query_recover_backup_logs(start_time, end_time)
    if not backup_records:
        return False
    backup_ids = [record["backup_id"] for record in backup_records]
    # 最近一周回档过就忽略
    if MySQLBackupRecoverTask.objects.filter(
        backup_id__in=backup_ids, task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS]
    ).exists():
        logger.info(f"backup_id {backup_ids} already exists, skip.")
        return False
    return True


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
        backup_file_size_gb = bytes_to_gb(backup_record["total_filesize"])
        root_id = generate_root_id()
        task = MySQLBackupRecoverTask(
            bk_biz_id=backup_record["bk_biz_id"],
            cluster_id=cluster.id,
            cluster_domain=backup_record.get("cluster_address", ""),
            cluster_type=cluster.cluster_type,
            charset=backup_record.get("backup_charset", ""),
            mysql_version=backup_record.get("mysql_version", ""),
            sql_mode=backup_record.get("sql_mode", ""),
            backup_id=backup_id,
            backup_begin_time=backup_record["backup_begin_time"],
            backup_end_time=backup_record["backup_end_time"],
            backup_total_size=int(backup_file_size_gb),
            backup_host=backup_record.get("backup_host", ""),
            backup_host_role=backup_record.get("mysql_role", ""),
            backup_type=backup_record.get("backup_type", ""),
            backup_tool=backup_record.get("backup_tool", ""),
            time_zone=backup_record.get("time_zone", ""),
            task_id=root_id,
            task_status=TaskStatus.GENERATED,
            creator="system",
            updater="system",
        )
        # Calculate minimum disk size required
        min_disk_size = calculate_min_disk_size(backup_record["total_filesize"])
        # 申请资源
        mysql_version = backup_record.get("mysql_version", "")
        apply_params = build_resource_apply_params(root_id, min_disk_size, mysql_version)
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
                "ticket_type": TicketType.MYSQL_ROLLBACK_EXERCISE,
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

    # 定义比较规则（优先级数字大先出队）
    def __lt__(self, other):
        return self.priority > other.priority


def calculate_cluster_weight(cluster, recover_success_count: int) -> float:
    """
    计算集群的选择权重，演练成功次数越多，权重越低

    Args:
        cluster: 集群对象
        recover_success_count: 该集群的演练成功次数

    Returns:
        float: 集群的选择权重，范围(0, 1]
    """
    # 基础权重为1.0，演练成功次数越多，权重越低
    # 使用指数衰减函数：weight = 1.0 / (1 + success_count * decay_factor)
    decay_factor = 0.5  # 衰减因子，可以调整以控制衰减速度
    weight = 1.0 / (1 + recover_success_count * decay_factor)

    # 确保权重在合理范围内，最小权重为0.1
    min_weight = 0.1
    return max(weight, min_weight)


def weighted_random_choice(candidates: list, weights: list, num_select: int) -> list:
    """
    根据权重进行随机选择

    Args:
        candidates: 候选对象列表
        weights: 对应的权重列表
        num_select: 要选择的数量

    Returns:
        list: 选择的对象列表
    """
    if not candidates or not weights or len(candidates) != len(weights):
        return []

    selected = []
    remaining_candidates = candidates.copy()
    remaining_weights = weights.copy()

    for i in range(min(num_select, len(candidates))):
        if not remaining_candidates:
            break

        # 使用random.choices进行加权随机选择
        chosen = random.choices(remaining_candidates, weights=remaining_weights, k=1)[0]
        selected.append(chosen)

        # 移除已选择的候选者和对应权重
        idx = remaining_candidates.index(chosen)
        remaining_candidates.pop(idx)
        remaining_weights.pop(idx)

    return selected


def calculate_dynamic_cluster_type_targets(num: int, recent_stats: dict) -> tuple:
    """
    根据最近2小时的演练情况动态计算各集群类型的目标数量

    Args:
        num: 总需要选择的集群数量
        recent_stats: 最近2小时的演练统计信息

    Returns:
        tuple: (tendbcluster_target, tendbha_target)
    """
    tendbcluster_recent = recent_stats["tendbcluster_count"]
    tendbha_recent = recent_stats["tendbha_count"]
    total_recent = recent_stats["total_count"]

    logger.info(
        _("最近2小时演练统计: TenDBCluster {} 次, TenDBHA {} 次, 总计 {} 次").format(
            tendbcluster_recent, tendbha_recent, total_recent
        )
    )

    if total_recent == 0:
        # 如果最近2小时没有演练，则平均分配
        tendbcluster_target = num // 2
        tendbha_target = num - tendbcluster_target
        logger.info(_("最近2小时无演练记录，采用平均分配策略"))
    else:
        # 计算演练比例，优先选择演练较少的类型
        tendbcluster_ratio = tendbcluster_recent / total_recent
        tendbha_ratio = tendbha_recent / total_recent

        # 反向调整：演练多的类型分配少一些，演练少的类型分配多一些
        # 使用 sigmoid 函数进行平滑调整
        balance_factor = 0.7  # 调节因子，控制调整幅度

        if tendbcluster_ratio > tendbha_ratio:
            # TenDBCluster 演练较多，应该减少其比例
            adjustment = (tendbcluster_ratio - tendbha_ratio) * balance_factor
            target_tendbcluster_ratio = 0.5 - adjustment
        else:
            # TenDBHA 演练较多，应该减少其比例
            adjustment = (tendbha_ratio - tendbcluster_ratio) * balance_factor
            target_tendbcluster_ratio = 0.5 + adjustment

        # 确保比例在合理范围内 [0.2, 0.8]
        target_tendbcluster_ratio = max(0.2, min(0.8, target_tendbcluster_ratio))

        tendbcluster_target = int(num * target_tendbcluster_ratio)
        tendbha_target = num - tendbcluster_target

        logger.info(
            _("动态调整策略: TenDBCluster目标比例 {:.1%}, 目标数量 {}, TenDBHA目标数量 {}").format(
                target_tendbcluster_ratio, tendbcluster_target, tendbha_target
            )
        )

    return tendbcluster_target, tendbha_target


def get_exercise_clusters(num: int) -> list:
    """
    获取待演练的集群，根据最近2小时演练情况动态调整集群类型分配
    已演练成功的集群被选中的概率更低
    """
    count = 0
    cluster_biz_map = defaultdict(list)
    recover_success_map = {}
    exclude_biz_ids = MySQLBackupRecoverTask.get_all_practiced_biz_ids()
    exclude_cluster_id = MySQLBackupRecoverTask.get_all_practiced_cluster_ids()
    recent_task_cluster_ids = MySQLBackupRecoverTask.get_recent_24h_task_cluster_ids()
    exclude_cluster_id.extend(recent_task_cluster_ids)

    # 获取最近2小时的演练统计信息
    recent_stats = MySQLBackupRecoverTask.get_recent_2h_exercise_cluster_type_stats()

    # 动态计算各集群类型的目标数量
    target_tendbcluster, target_tendbha = calculate_dynamic_cluster_type_targets(num, recent_stats)

    # 获取所有集群的演练成功次数统计
    result = (
        MySQLBackupRecoverTask.objects.filter(
            task_status__in=[TaskStatus.RESOURCE_RETURN_SUCCESS, TaskStatus.RECOVER_SUCCESS],
        )
        .values("cluster_domain")
        .annotate(total=Count("*"))
    )
    recover_success_map = {item["cluster_domain"]: item["total"] for item in result}

    # 先获取未演练的业务的集群
    clusters = Cluster.objects.exclude(
        bk_biz_id__in=exclude_biz_ids,
        id__in=exclude_cluster_id,
    ).filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
    if len(clusters) >= 0:
        for cluster in clusters:
            # 未演练过的集群权重最高
            heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(1000, cluster))
            count = count + 1
    if count <= num * 3:
        # 如果都演练过的话,则选择没有演练过的集群
        clusters = Cluster.objects.exclude(
            id__in=exclude_cluster_id,
        ).filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
        if len(clusters) >= 0:
            for cluster in clusters:
                recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
                # 根据演练成功次数调整优先级，演练次数越多优先级越低
                priority = max(500 - recover_success_cnt * 50, 100)
                heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
                count = count + 1
        if count <= num * 3:
            clusters = Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
            for cluster in clusters:
                recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
                # 根据演练成功次数调整优先级，演练次数越多优先级越低
                priority = max(200 - recover_success_cnt * 20, 50)
                heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
                count = count + 1
                if count >= num * 3:
                    break

    # 收集所有候选集群及其权重
    all_candidates = []
    for bk_biz_id, pq in cluster_biz_map.items():
        while pq:
            task = heapq.heappop(pq)
            if cluster_has_backup_record(task.cluster.id):
                all_candidates.append(task.cluster)

    # 按集群类型分组
    tendbcluster_candidates = [c for c in all_candidates if c.cluster_type == ClusterType.TenDBCluster]
    tendbha_candidates = [c for c in all_candidates if c.cluster_type == ClusterType.TenDBHA]

    logger.info(
        _("找到候选集群: TenDBCluster {} 个, TenDBHA {} 个").format(len(tendbcluster_candidates), len(tendbha_candidates))
    )

    # 根据动态目标进行加权随机选择
    rs = []

    # 为TenDBCluster候选集群计算权重并选择
    if tendbcluster_candidates and target_tendbcluster > 0:
        tendbcluster_weights = []
        for cluster in tendbcluster_candidates:
            success_count = recover_success_map.get(cluster.immute_domain, 0)
            weight = calculate_cluster_weight(cluster, success_count)
            tendbcluster_weights.append(weight)

        # 加权随机选择TenDBCluster
        selected_tendbcluster = weighted_random_choice(
            tendbcluster_candidates, tendbcluster_weights, target_tendbcluster
        )
        rs.extend(selected_tendbcluster)

        logger.info(
            _("TenDBCluster选择详情: 候选{}个, 目标{}个, 实际选择{}个").format(
                len(tendbcluster_candidates), target_tendbcluster, len(selected_tendbcluster)
            )
        )

    # 为TenDBHA候选集群计算权重并选择
    if tendbha_candidates and target_tendbha > 0:
        tendbha_weights = []
        for cluster in tendbha_candidates:
            success_count = recover_success_map.get(cluster.immute_domain, 0)
            weight = calculate_cluster_weight(cluster, success_count)
            tendbha_weights.append(weight)

        # 加权随机选择TenDBHA
        selected_tendbha = weighted_random_choice(tendbha_candidates, tendbha_weights, target_tendbha)
        rs.extend(selected_tendbha)

        logger.info(
            _("TenDBHA选择详情: 候选{}个, 目标{}个, 实际选择{}个").format(
                len(tendbha_candidates), target_tendbha, len(selected_tendbha)
            )
        )

    # 如果还没达到目标数量，从剩余候选中补充
    if len(rs) < num:
        remaining_needed = num - len(rs)
        selected_ids = {cluster.id for cluster in rs}

        # 收集未选中的候选集群
        remaining_candidates = [c for c in all_candidates if c.id not in selected_ids]

        if remaining_candidates:
            remaining_weights = []
            for cluster in remaining_candidates:
                success_count = recover_success_map.get(cluster.immute_domain, 0)
                weight = calculate_cluster_weight(cluster, success_count)
                remaining_weights.append(weight)

            # 从剩余候选中加权随机选择
            additional_selected = weighted_random_choice(remaining_candidates, remaining_weights, remaining_needed)
            rs.extend(additional_selected)

            logger.info(
                _("补充选择: 需要{}个, 候选{}个, 实际补充{}个").format(
                    remaining_needed, len(remaining_candidates), len(additional_selected)
                )
            )

    # 统计最终结果
    tendbcluster_final_count = sum(1 for c in rs if c.cluster_type == ClusterType.TenDBCluster)
    tendbha_final_count = sum(1 for c in rs if c.cluster_type == ClusterType.TenDBHA)

    logger.info(
        _("最终选择的集群: TenDBCluster {} 个, TenDBHA {} 个, 总计 {} 个").format(
            tendbcluster_final_count, tendbha_final_count, len(rs)
        )
    )

    # 记录演练成功次数统计
    for cluster in rs:
        success_count = recover_success_map.get(cluster.immute_domain, 0)
        logger.info(_("选中集群 {} ({}): 历史演练成功次数 {}").format(cluster.immute_domain, cluster.cluster_type, success_count))

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
            "labels": mch_info["labels"],
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
