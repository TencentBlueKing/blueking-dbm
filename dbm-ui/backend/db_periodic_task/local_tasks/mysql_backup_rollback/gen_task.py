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
import json
import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, Union

from django.db.models import Count, Q
from django.forms.models import model_to_dict
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.models import ExerciseIgnoreConfig, MySQLBackupRecoverTask, TaskStatus
from backend.db_report.models.mysql_backup_result import MysqlBackupResult
from backend.env import MYSQL_BACKUPRECOVER_BIZ_ID, MYSQL_BACKUPRECOVER_MCH_LABELS_ID
from backend.flow.consts import RollbackType
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
    logger.info(_("apply details: {}").format(details))
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
    today = datetime.now(django_timezone.utc)
    # Find the most recent Monday (0=Monday, 6=Sunday)
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)

    # Set time to start of day (00:00:00)
    start_time = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    # Set time to end of day (23:59:59.999999)
    end_time = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_time, end_time


def should_ignore_cluster_for_exercise(cluster) -> tuple:
    """
    检查集群是否应该被忽略演练

    Args:
        cluster: 集群对象

    Returns:
        tuple: (should_ignore: bool, reason: str)
    """
    # 检查业务级别忽略
    if ExerciseIgnoreConfig.is_biz_ignored(cluster.bk_biz_id):
        return True, _("业务 {} 被忽略配置排除").format(cluster.bk_biz_id)

    # 检查集群级别忽略
    if ExerciseIgnoreConfig.is_cluster_ignored(cluster.id):
        return True, _("集群 {} 被忽略配置排除").format(cluster.immute_domain)

    return False, ""


def cluster_has_backup_record(cluster_id: int) -> bool:
    """
    查询集群是否存在备份记录
    """
    start_time, end_time = get_last_week_range()

    # 先查询出已经回档过的备份ID，直接在查询时排除
    exercised_backup_ids = set(
        MySQLBackupRecoverTask.objects.filter(
            task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS]
        ).values_list("backup_id", flat=True)
    )

    # 构建查询条件
    cluster = Cluster.objects.get(id=cluster_id)
    conditions = Q(
        cluster_id=cluster_id,
        cluster_address=cluster.immute_domain,
        is_full_backup=1,  # 全备
        backup_consistent_time__range=(start_time, end_time),  # 在时间范围内
    ) | Q(
        cluster_id=cluster_id,
        cluster_address=cluster.immute_domain,
        backup_consistent_time__range=(start_time, end_time),
    ) & ~Q(
        mysql_role__in=["spider_master", "TDBCTL"]
    )  # 排除 spider_master 和 TDBCTL 角色

    # 查询备份记录，直接排除已回档的备份ID
    backup_records = (
        MysqlBackupResult.objects.filter(conditions)
        .exclude(backup_id__in=exercised_backup_ids)
        .order_by("-backup_consistent_time")
    )

    return backup_records.exists()


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
        # 再次检查集群是否被忽略配置排除（双重保险）
        should_ignore, ignore_reason = should_ignore_cluster_for_exercise(cluster)
        if should_ignore:
            logger.info(_("跳过演练: {}").format(ignore_reason))
            continue
        # 查询备份记录
        start_time, end_time = get_last_week_range()

        # 先查询出已经回档过的备份ID，直接在查询时排除
        exercised_backup_ids = set(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS]
            ).values_list("backup_id", flat=True)
        )

        # 构建查询条件：基础条件
        base_conditions = Q(
            cluster_id=cluster.id,
            cluster_address=cluster.immute_domain,
            backup_consistent_time__range=(start_time, end_time),
            is_full_backup=1,  # 全备
        )

        # 排除特殊角色的条件
        exclude_special_roles = ~Q(mysql_role__in=["spider_master", "TDBCTL", "spider_mnt"])

        # 最终条件：基础条件 AND 排除特殊角色
        conditions = base_conditions & exclude_special_roles

        # 查询备份记录，直接排除已回档的备份ID
        backup_results = (
            MysqlBackupResult.objects.filter(conditions)
            .exclude(backup_id__in=exercised_backup_ids)
            .order_by("backup_consistent_time")[:10]
        )

        if not backup_results.exists():
            continue

        # 选择第一个备份记录生成回档任务
        backup_result = backup_results.first()

        # 格式化备份信息，保持与原有格式兼容
        backup_record = model_to_dict(backup_result)

        # 解析JSON字段
        backup_record["binlog_info"] = json.loads(backup_record["binlog_info"])
        backup_record["file_list"] = json.loads(backup_record["file_list"])
        backup_record["extra_fields"] = json.loads(backup_record["extra_fields"])

        # 添加兼容字段
        backup_record["consistent_backup_time"] = backup_record["backup_consistent_time"]
        backup_record["backup_time"] = backup_record["backup_consistent_time"]
        backup_record["bk_cloud_id"] = backup_record["extra_fields"].get("bk_cloud_id")
        backup_record["encrypt_enable"] = backup_record["extra_fields"].get("encrypt_enable")
        backup_record["time_zone"] = backup_record["extra_fields"].get("time_zone", "")
        backup_record["backup_charset"] = backup_record["extra_fields"].get("backup_charset", "")
        backup_record["backup_tool"] = backup_record["extra_fields"].get("backup_tool", "")
        backup_record["sql_mode"] = backup_record["extra_fields"].get("sql_mode", "")
        data_dir_size_mb = backup_record["extra_fields"].get("data_dir_size_mb", 0)
        # 格式化时间字段
        if isinstance(backup_record["backup_consistent_time"], datetime):
            backup_record["backup_consistent_time"] = backup_record["backup_consistent_time"].isoformat()
        if isinstance(backup_record["backup_begin_time"], datetime):
            backup_record["backup_begin_time"] = backup_record["backup_begin_time"].isoformat()
        if isinstance(backup_record["backup_end_time"], datetime):
            backup_record["backup_end_time"] = backup_record["backup_end_time"].isoformat()
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
        if data_dir_size_mb > 0:
            # 扩大1.5倍并转换为GB (MB转GB需要除以1024)
            logger.info("data_dir_size_mb: {}".format(data_dir_size_mb))
            min_disk_size = int((data_dir_size_mb * 1.5) / 1024)
        else:
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
                "labels": mch_info["labels"],
                "rollback_type": RollbackType.REMOTE_AND_BACKUPID,
            }
            task.exercise_host_ip = mch_info["ip"]
            task.task_status = TaskStatus.COMMIT_SUCCESS
            task.save()
            flow = MySQLRollbackExerciseFlow(root_id=root_id, data=flow_context)
            flow.run()
        except Exception as e:
            logger.exception(_("回档演练流程运行失败: {}").format(e))

            # 演练失败时归还资源
            resource_return_info = ""
            try:
                return_params = {
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
                return_resource(return_params)
                resource_return_info = _("资源归还成功: IP {}").format(mch_info["ip"])
                logger.info(_("演练失败，已成功归还资源: {}").format(mch_info["ip"]))
            except Exception as return_e:
                resource_return_info = _("资源归还失败: {}").format(str(return_e))
                logger.error(_("归还资源失败: {}").format(str(return_e)))

            task.task_status = TaskStatus.COMMIT_FAILED
            task.task_info = _("演练流程失败: {}; {}").format(str(e), resource_return_info)
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


def _prepare_cluster_data(num: int):
    """准备集群选择所需的基础数据"""
    exclude_biz_ids = MySQLBackupRecoverTask.get_all_practiced_biz_ids()
    exclude_cluster_id = MySQLBackupRecoverTask.get_all_practiced_cluster_ids()
    recent_task_cluster_ids = MySQLBackupRecoverTask.get_recent_24h_task_cluster_ids()
    exclude_cluster_id.extend(recent_task_cluster_ids)

    # 添加演练忽略配置的业务和集群
    ignored_biz_ids = ExerciseIgnoreConfig.get_ignored_biz_ids()
    ignored_cluster_ids = ExerciseIgnoreConfig.get_ignored_cluster_ids()

    exclude_biz_ids.extend(ignored_biz_ids)
    exclude_cluster_id.extend(ignored_cluster_ids)

    logger.info(
        _("演练忽略配置: 忽略业务 {} 个 {}, 忽略集群 {} 个 {}").format(
            len(ignored_biz_ids), ignored_biz_ids, len(ignored_cluster_ids), ignored_cluster_ids
        )
    )

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

    return exclude_biz_ids, exclude_cluster_id, target_tendbcluster, target_tendbha, recover_success_map


def _collect_unpracticed_clusters(exclude_biz_ids, exclude_cluster_id, cluster_biz_map):
    """收集未演练的集群"""
    count = 0
    clusters = Cluster.objects.exclude(
        bk_biz_id__in=exclude_biz_ids,
        id__in=exclude_cluster_id,
    ).filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])

    for cluster in clusters:
        # 未演练过的集群权重最高
        heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(1000, cluster))
        count += 1

    return count


def _collect_practiced_clusters(exclude_cluster_id, cluster_biz_map, recover_success_map, count, num):
    """收集已演练的集群"""
    if count <= num * 3:
        # 如果都演练过的话,则选择没有演练过的集群
        clusters = Cluster.objects.exclude(
            id__in=exclude_cluster_id,
        ).filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])

        for cluster in clusters:
            recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
            # 根据演练成功次数调整优先级，演练次数越多优先级越低
            priority = max(500 - recover_success_cnt * 50, 100)
            heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
            count += 1

    return count


def _collect_all_clusters(cluster_biz_map, recover_success_map, count, num):
    """收集所有集群"""
    if count <= num * 3:
        clusters = Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
        for cluster in clusters:
            recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
            # 根据演练成功次数调整优先级，演练次数越多优先级越低
            priority = max(200 - recover_success_cnt * 20, 50)
            heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
            count += 1
            if count >= num * 3:
                break

    return count


def _collect_valid_candidates(cluster_biz_map, target_tendbcluster, target_tendbha):
    """收集有效的候选集群"""
    all_candidates = []
    tendbcluster_count = 0
    tendbha_count = 0

    # 计算需要的最大集群数量（预留一些余量以防部分集群没有有效备份）
    max_needed_tendbcluster = target_tendbcluster * 2  # 2倍余量
    max_needed_tendbha = target_tendbha * 2  # 2倍余量

    for bk_biz_id, pq in cluster_biz_map.items():
        while pq:
            task = heapq.heappop(pq)
            cluster = task.cluster

            # 检查集群是否被忽略配置排除
            should_ignore, ignore_reason = should_ignore_cluster_for_exercise(cluster)
            if should_ignore:
                logger.debug(_("候选集群筛选: {}").format(ignore_reason))
                continue

            # 根据集群类型检查是否已收集足够数量
            if cluster.cluster_type == ClusterType.TenDBCluster:
                if tendbcluster_count >= max_needed_tendbcluster:
                    continue
            elif cluster.cluster_type == ClusterType.TenDBHA:
                if tendbha_count >= max_needed_tendbha:
                    continue

            # 检查集群是否有有效的备份记录
            logger.debug(_("检查集群{}:{} 是否有备份记录").format(cluster.immute_domain, cluster.id))
            if cluster_has_backup_record(cluster.id):
                all_candidates.append(cluster)
                if cluster.cluster_type == ClusterType.TenDBCluster:
                    tendbcluster_count += 1
                elif cluster.cluster_type == ClusterType.TenDBHA:
                    tendbha_count += 1

            # 如果两种类型都收集够了，提前退出
            if tendbcluster_count >= max_needed_tendbcluster and tendbha_count >= max_needed_tendbha:
                break

    logger.info(_("检查了集群备份记录，收集到 TenDBCluster {} 个，TenDBHA {} 个有效候选集群").format(tendbcluster_count, tendbha_count))

    return all_candidates


def _select_clusters_by_type(candidates, cluster_type, target_count, recover_success_map):
    """按类型选择集群"""
    if not candidates or target_count <= 0:
        return []

    weights = []
    for cluster in candidates:
        success_count = recover_success_map.get(cluster.immute_domain, 0)
        weight = calculate_cluster_weight(cluster, success_count)
        weights.append(weight)

    # 加权随机选择
    selected = weighted_random_choice(candidates, weights, target_count)

    logger.info(_("{}选择详情: 候选{}个, 目标{}个, 实际选择{}个").format(cluster_type, len(candidates), target_count, len(selected)))

    return selected


def _supplement_selection(all_candidates, current_selection, num, recover_success_map):
    """补充选择不足的集群"""
    if len(current_selection) >= num:
        return current_selection

    remaining_needed = num - len(current_selection)
    selected_ids = {cluster.id for cluster in current_selection}

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
        current_selection.extend(additional_selected)

        logger.info(
            _("补充选择: 需要{}个, 候选{}个, 实际补充{}个").format(
                remaining_needed, len(remaining_candidates), len(additional_selected)
            )
        )

    return current_selection


def get_exercise_clusters(num: int) -> list:
    """
    获取待演练的集群，根据最近2小时演练情况动态调整集群类型分配
    已演练成功的集群被选中的概率更低
    """
    # 准备基础数据
    (
        exclude_biz_ids,
        exclude_cluster_id,
        target_tendbcluster,
        target_tendbha,
        recover_success_map,
    ) = _prepare_cluster_data(num)

    # 收集候选集群
    cluster_biz_map = defaultdict(list)
    count = _collect_unpracticed_clusters(exclude_biz_ids, exclude_cluster_id, cluster_biz_map)
    count = _collect_practiced_clusters(exclude_cluster_id, cluster_biz_map, recover_success_map, count, num)
    _collect_all_clusters(cluster_biz_map, recover_success_map, count, num)

    # 收集有效候选集群
    all_candidates = _collect_valid_candidates(cluster_biz_map, target_tendbcluster, target_tendbha)

    # 按集群类型分组
    tendbcluster_candidates = [c for c in all_candidates if c.cluster_type == ClusterType.TenDBCluster]
    tendbha_candidates = [c for c in all_candidates if c.cluster_type == ClusterType.TenDBHA]

    logger.info(
        _("找到候选集群: TenDBCluster {} 个, TenDBHA {} 个").format(len(tendbcluster_candidates), len(tendbha_candidates))
    )

    # 根据动态目标进行加权随机选择
    rs = []

    # 选择TenDBCluster集群
    selected_tendbcluster = _select_clusters_by_type(
        tendbcluster_candidates, "TenDBCluster", target_tendbcluster, recover_success_map
    )
    rs.extend(selected_tendbcluster)

    # 选择TenDBHA集群
    selected_tendbha = _select_clusters_by_type(tendbha_candidates, "TenDBHA", target_tendbha, recover_success_map)
    rs.extend(selected_tendbha)

    # 如果还没达到目标数量，从剩余候选中补充
    rs = _supplement_selection(all_candidates, rs, num, recover_success_map)

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
