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
import os
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
from backend.ticket.builders.common.constants import MySQLBackupSource
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


def backup_info_format(backup_info: dict) -> Dict[str, Any]:
    """
    备份信息格式化，兼容从es获取的备份信息
    @param backup_info:一条备份记录
    @return: 返回格式化后的备份信息
    """
    backup_info["binlog_info"] = json.loads(backup_info["binlog_info"])
    backup_info["file_list"] = json.loads(backup_info["file_list"])
    backup_info["extra_fields"] = json.loads(backup_info["extra_fields"])
    backup_info["consistent_backup_time"] = backup_info["backup_consistent_time"]
    backup_info["backup_time"] = backup_info["backup_consistent_time"]
    backup_info["bk_cloud_id"] = backup_info["extra_fields"]["bk_cloud_id"]
    backup_info["encrypt_enable"] = backup_info["extra_fields"]["encrypt_enable"]
    backup_info["time_zone"] = backup_info["extra_fields"]["time_zone"]
    backup_info["backup_charset"] = backup_info["extra_fields"]["backup_charset"]
    backup_info["backup_tool"] = backup_info["extra_fields"]["backup_tool"]
    backup_info["file_list_details"] = backup_info["file_list"]
    task_ids = []
    local_files = []
    for file in backup_info["file_list_details"]:
        task_ids.append(file["task_id"])
        local_files.append(os.path.join(backup_info["extra_fields"].get("original_backup_dir", ""), file["file_name"]))
        if file["file_type"] == "priv":
            file["mysql_role"] = backup_info["mysql_role"]
            file["backup_consistent_time"] = backup_info["backup_consistent_time"]
            backup_info["priv"] = file
        if file["file_type"] == "index":
            backup_info["index"] = file
    backup_info["task_ids"] = task_ids
    backup_info["local_files"] = local_files
    return backup_info


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


def cluster_has_backup_record(cluster_id: int) -> bool:
    """
    查询集群是否存在备份记录
    """
    import time

    func_start = time.time()
    start_time, end_time = get_last_week_range()

    # 构建查询条件
    cluster_query_start = time.time()
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_query_time = time.time() - cluster_query_start

    # 查询条件：只查询全备份记录，排除特定角色
    conditions = Q(
        cluster_id=cluster_id,
        cluster_address=cluster.immute_domain,
        is_full_backup=1,  # 只查询全备
        backup_consistent_time__range=(start_time, end_time),
    ) & ~Q(mysql_role__in=["spider_master", "spider_mnt", "TDBCTL"])

    # 最高效实现：直接使用 NOT IN + LIMIT 1，一次查询解决
    try:
        # 获取已演练的备份ID列表
        exercised_query_start = time.time()
        exercised_backup_ids = list(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS]
            ).values_list("backup_id", flat=True)
        )
        exercised_query_time = time.time() - exercised_query_start
    except Exception:
        # 如果MySQLBackupRecoverTask表不存在，说明没有演练过任何备份
        exercised_backup_ids = []
        exercised_query_time = 0

    # 使用 NOT IN 查询未演练的备份记录，LIMIT 1 找到第一条就返回
    backup_query_start = time.time()
    query = MysqlBackupResult.objects.filter(conditions)

    if exercised_backup_ids:
        # 排除已演练的备份ID
        query = query.exclude(backup_id__in=exercised_backup_ids)

    # 只需要知道是否存在，exists() 比 count() 更高效
    result = query.exists()
    backup_query_time = time.time() - backup_query_start

    total_time = time.time() - func_start

    # 如果查询耗时超过0.1秒，输出详细的性能日志
    if total_time > 0.1:
        logger.debug(
            _("集群 {} 备份检查耗时: {:.3f}秒 (集群查询:{:.3f}s, 已演练备份查询:{:.3f}s, 备份记录查询:{:.3f}s, 已演练备份数:{})").format(
                cluster.immute_domain,
                total_time,
                cluster_query_time,
                exercised_query_time,
                backup_query_time,
                len(exercised_backup_ids),
            )
        )

    return result


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
        # 注意：忽略检查已在 get_exercise_clusters 中完成，这里不需要重复检查
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
        if not backup_result:
            logger.info("no backup record found")
            continue

        # 格式化备份信息，保持与原有格式兼容
        backup_result.backup_consistent_time = backup_result.backup_consistent_time.isoformat()
        backup_result.backup_begin_time = backup_result.backup_begin_time.isoformat()
        backup_result.backup_end_time = backup_result.backup_end_time.isoformat()
        backup_record = model_to_dict(backup_result)
        backup_record["backup_source"] = MySQLBackupSource.REMOTE.value
        # 解析JSON字段
        try:
            tsk_backup_record = {}
            tsk_backup_record["binlog_info"] = json.loads(backup_record["binlog_info"])
            tsk_backup_record["file_list"] = json.loads(backup_record["file_list"])
            tsk_backup_record["extra_fields"] = json.loads(backup_record["extra_fields"])
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON fields: {e}, backup_record: {backup_record}")
            continue

        # task 需要填充的字段
        time_zone = tsk_backup_record["extra_fields"].get("time_zone", "")
        backup_charset = tsk_backup_record["extra_fields"].get("backup_charset", "")
        backup_tool = tsk_backup_record["extra_fields"].get("backup_tool", "")
        sql_mode = tsk_backup_record["extra_fields"].get("sql_mode", "")
        data_dir_size_mb = tsk_backup_record["extra_fields"].get("data_dir_size_mb", 0)
        storage_engine = tsk_backup_record["extra_fields"].get("storage_engine", "innodb")
        backup_id = backup_record["backup_id"]
        backup_file_size_gb = bytes_to_gb(backup_record["total_filesize"])

        # 打印备份信息
        logger.info("exercise backup_record: {}".format(backup_record))
        root_id = generate_root_id()
        task = MySQLBackupRecoverTask(
            bk_biz_id=backup_record["bk_biz_id"],
            cluster_id=cluster.id,
            cluster_domain=backup_record.get("cluster_address", ""),
            cluster_type=cluster.cluster_type,
            charset=backup_charset,
            mysql_version=backup_record.get("mysql_version", ""),
            sql_mode=sql_mode,
            backup_id=backup_id,
            backup_begin_time=backup_record["backup_begin_time"],
            backup_end_time=backup_record["backup_end_time"],
            backup_total_size=int(backup_file_size_gb),
            backup_host=backup_record.get("backup_host", ""),
            backup_host_role=backup_record.get("mysql_role", ""),
            backup_type=backup_record.get("backup_type", ""),
            backup_tool=backup_tool,
            time_zone=time_zone,
            task_id=root_id,
            task_status=TaskStatus.GENERATED,
            creator="system",
            updater="system",
        )
        # Calculate minimum disk size required
        if data_dir_size_mb > 0:
            # 扩大1.5倍并转换为GB (MB转GB需要除以1024)
            if storage_engine == "innodb":
                data_dir_size_mb = data_dir_size_mb * 1.3
            else:
                data_dir_size_mb = data_dir_size_mb * 2.3
            logger.info(_("计算后的数据目录大小: {} MB").format(data_dir_size_mb))
            min_disk_size = int(data_dir_size_mb / 1024)
            logger.info(_("计算后的最小磁盘大小: {} GB").format(min_disk_size))
        else:
            min_disk_size = calculate_min_disk_size(backup_record["total_filesize"])
        # 申请资源
        mysql_version = backup_record.get("mysql_version", "")
        apply_params = build_resource_apply_params(root_id, min_disk_size, mysql_version)
        resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
        if resp["code"] != 0:
            if resp["code"] == ResourceApplyErrCode.RESOURCE_LAKE:
                logger.error(_("资源不足申请失败，请前往补货后重试{}").format(resp.get("message")))
                task.task_status = TaskStatus.RESOURCE_INSUFFICIENT
                task.task_info = _("需要的最小磁盘大小是{}GB".format(min_disk_size))
                task.save()
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
                "backup_record": backup_info_format(backup_record),
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
                            "host_id": mch_info["bk_host_id"],
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
    running_task_cluster_ids = MySQLBackupRecoverTask.get_running_task_cluster_ids()

    exclude_cluster_id.extend(recent_task_cluster_ids)
    exclude_cluster_id.extend(running_task_cluster_ids)

    logger.info(_("并发控制: 排除正在执行的任务集群 {} 个").format(len(running_task_cluster_ids)))

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
    """收集从未演练过的业务的集群 - 最高优先级"""
    count = 0
    unpracticed_biz_clusters = 0

    # 使用 Q 对象实现 OR 逻辑：排除业务ID在列表中 OR 集群ID在列表中的集群
    exclude_condition = Q()
    if exclude_biz_ids:
        exclude_condition |= Q(bk_biz_id__in=exclude_biz_ids)
    if exclude_cluster_id:
        exclude_condition |= Q(id__in=exclude_cluster_id)

    clusters = Cluster.objects.exclude(exclude_condition).filter(
        cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA]
    )

    # 按业务分组统计
    unpracticed_biz_ids = set()

    for cluster in clusters:
        # 从未演练过的业务的集群获得绝对最高优先级
        heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(10000, cluster))
        unpracticed_biz_ids.add(cluster.bk_biz_id)
        unpracticed_biz_clusters += 1
        count += 1

    if unpracticed_biz_ids:
        logger.info(_("发现 {} 个从未演练过的业务，包含 {} 个集群，将获得最高优先级").format(len(unpracticed_biz_ids), unpracticed_biz_clusters))
        logger.info(_("从未演练过的业务ID列表: {}").format(sorted(list(unpracticed_biz_ids))))
    else:
        logger.info(_("未发现从未演练过的业务"))

    return count


def _collect_practiced_clusters(exclude_cluster_id, cluster_biz_map, recover_success_map, count, num):
    """收集已演练的集群 - 中等优先级"""
    if count <= num * 3:
        # 只排除集群ID，不排除业务ID（因为这些是已演练过的集群）
        clusters = Cluster.objects.exclude(
            id__in=exclude_cluster_id,
        ).filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])

        practiced_clusters = 0
        for cluster in clusters:
            recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
            # 降低已演练集群的优先级，与从未演练集群拉开更大差距
            priority = max(1000 - recover_success_cnt * 100, 200)  # 优先级范围 200-1000
            heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
            practiced_clusters += 1
            count += 1

        if practiced_clusters > 0:
            logger.info(_("收集了 {} 个已演练过的集群作为候补").format(practiced_clusters))

    return count


def _collect_all_clusters(cluster_biz_map, recover_success_map, count, num):
    """收集所有集群 - 最低优先级兜底"""
    if count <= num * 3:
        clusters = Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
        fallback_clusters = 0

        for cluster in clusters:
            recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
            # 兜底集群使用最低优先级
            priority = max(500 - recover_success_cnt * 50, 100)  # 优先级范围 100-500
            heapq.heappush(cluster_biz_map[cluster.bk_biz_id], Task(priority, cluster))
            fallback_clusters += 1
            count += 1
            if count >= num * 3:
                break

        if fallback_clusters > 0:
            logger.info(_("添加了 {} 个兜底集群").format(fallback_clusters))

    return count


def _collect_valid_candidates(cluster_biz_map, target_tendbcluster, target_tendbha):
    """收集有效的候选集群"""
    import time

    start_time = time.time()
    all_candidates = []
    tendbcluster_count = 0
    tendbha_count = 0

    # 性能统计变量
    total_clusters_checked = 0
    backup_check_time = 0
    no_backup_clusters = 0

    # 计算需要的最大集群数量（预留一些余量以防部分集群没有有效备份）
    max_needed_tendbcluster = target_tendbcluster * 2  # 2倍余量
    max_needed_tendbha = target_tendbha * 2  # 2倍余量

    # 统计待检查的集群总数
    total_candidate_clusters = sum(len(pq) for pq in cluster_biz_map.values())
    logger.info(_("开始检查候选集群，总计 {} 个集群待检查").format(total_candidate_clusters))

    for bk_biz_id, pq in cluster_biz_map.items():
        while pq:
            task = heapq.heappop(pq)
            cluster = task.cluster
            total_clusters_checked += 1

            # 注意：忽略检查已在数据准备阶段完成，这里不需要重复检查

            # 根据集群类型检查是否已收集足够数量
            if cluster.cluster_type == ClusterType.TenDBCluster:
                if tendbcluster_count >= max_needed_tendbcluster:
                    continue
            elif cluster.cluster_type == ClusterType.TenDBHA:
                if tendbha_count >= max_needed_tendbha:
                    continue

            # 检查集群是否有有效的备份记录
            backup_start = time.time()
            logger.debug(_("检查集群{}:{} 是否有备份记录").format(cluster.immute_domain, cluster.id))
            has_backup = cluster_has_backup_record(cluster.id)
            backup_check_time += time.time() - backup_start

            if has_backup:
                all_candidates.append(cluster)
                if cluster.cluster_type == ClusterType.TenDBCluster:
                    tendbcluster_count += 1
                elif cluster.cluster_type == ClusterType.TenDBHA:
                    tendbha_count += 1
                logger.debug(_("集群 {} 有备份记录，已添加到候选列表").format(cluster.immute_domain))
            else:
                no_backup_clusters += 1
                logger.debug(_("集群 {} 无有效备份记录，跳过").format(cluster.immute_domain))

            # 如果两种类型都收集够了，提前退出
            if tendbcluster_count >= max_needed_tendbcluster and tendbha_count >= max_needed_tendbha:
                logger.info(_("已收集足够数量的候选集群，提前退出检查"))
                break

        # 每处理完一个业务的集群就输出进度
        if total_clusters_checked % 50 == 0:  # 每50个集群输出一次进度
            logger.info(
                _("集群检查进度: {}/{}, 已找到有效候选 {} 个").format(
                    total_clusters_checked, total_candidate_clusters, len(all_candidates)
                )
            )

    total_time = time.time() - start_time

    # 输出详细的性能统计
    logger.info(_("集群候选筛选完成统计:"))
    logger.info(_("- 总耗时: {:.2f}秒").format(total_time))
    logger.info(_("- 检查集群总数: {}").format(total_clusters_checked))
    logger.info(
        _("- 备份检查耗时: {:.2f}秒 (平均 {:.3f}秒/集群)").format(
            backup_check_time, backup_check_time / max(total_clusters_checked, 1)
        )
    )
    logger.info(_("- 无备份集群数: {}").format(no_backup_clusters))
    logger.info(
        _("- 有效候选集群: TenDBCluster {} 个, TenDBHA {} 个, 总计 {} 个").format(
            tendbcluster_count, tendbha_count, len(all_candidates)
        )
    )
    logger.info(_("- 注意: 忽略配置检查已在数据准备阶段完成，无需重复检查"))

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
    获取待演练的集群，优先级策略：
    1. 绝对优先：从未演练过的业务的集群 (优先级: 10000)
    2. 中等优先：已演练过的集群，按演练次数递减 (优先级: 200-1000)
    3. 最低优先：所有集群作为兜底 (优先级: 100-500)
    """
    import time

    total_start_time = time.time()
    logger.info(_("开始集群选择，目标数量: {}，策略: 从未演练过的业务绝对优先").format(num))

    # 准备基础数据
    data_prep_start = time.time()
    (
        exclude_biz_ids,
        exclude_cluster_id,
        target_tendbcluster,
        target_tendbha,
        recover_success_map,
    ) = _prepare_cluster_data(num)
    data_prep_time = time.time() - data_prep_start

    logger.info(_("已演练过的业务数量: {}").format(len(exclude_biz_ids)))
    logger.info(_("演练策略 - TenDBCluster目标: {}, TenDBHA目标: {}").format(target_tendbcluster, target_tendbha))

    # 收集候选集群
    collect_start = time.time()
    cluster_biz_map = defaultdict(list)
    count = _collect_unpracticed_clusters(exclude_biz_ids, exclude_cluster_id, cluster_biz_map)
    count = _collect_practiced_clusters(exclude_cluster_id, cluster_biz_map, recover_success_map, count, num)
    _collect_all_clusters(cluster_biz_map, recover_success_map, count, num)
    collect_time = time.time() - collect_start

    # 收集有效候选集群（这是最耗时的步骤）
    validation_start = time.time()
    all_candidates = _collect_valid_candidates(cluster_biz_map, target_tendbcluster, target_tendbha)
    validation_time = time.time() - validation_start

    # 按集群类型分组
    selection_start = time.time()
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
    selection_time = time.time() - selection_start

    # 统计最终结果
    tendbcluster_final_count = sum(1 for c in rs if c.cluster_type == ClusterType.TenDBCluster)
    tendbha_final_count = sum(1 for c in rs if c.cluster_type == ClusterType.TenDBHA)

    total_time = time.time() - total_start_time

    # 输出详细的性能统计
    logger.info(_("集群选择流程完成，性能统计:"))
    logger.info(_("- 总耗时: {:.2f}秒").format(total_time))
    logger.info(_("- 数据准备耗时: {:.2f}秒 ({:.1%})").format(data_prep_time, data_prep_time / total_time))
    logger.info(_("- 候选收集耗时: {:.2f}秒 ({:.1%})").format(collect_time, collect_time / total_time))
    logger.info(_("- 备份验证耗时: {:.2f}秒 ({:.1%})").format(validation_time, validation_time / total_time))
    logger.info(_("- 最终选择耗时: {:.2f}秒 ({:.1%})").format(selection_time, selection_time / total_time))

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
                    "host_id": mch_info["bk_host_id"],
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
