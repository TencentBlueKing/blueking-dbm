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
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set, Union

from django.db.models import Count, F, Func, Q
from django.forms.models import model_to_dict
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.models import ExerciseIgnoreConfig, MySQLBackupRecoverTask, TaskPhase, TaskStatus
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


def build_resource_apply_params(task_id: str, storage_spec: list, mysql_version: str) -> Dict[str, Union[str, Any]]:
    """Build resource application parameters

    Args:
        task_id: The unique task identifier
        storage_spec: 资源申请的磁盘规格列表，单项格式如:
            {"mount_point": "/data1", "disk_type": "ssd", "min": 200, "max": 2147483647}
            mount_point/disk_type 可选；单盘场景下可不带 mount_point 由资源池默认分配。
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
        "storage_spec": storage_spec,
    }
    logger.debug(_("apply details: {}").format(details))
    # 如果MySQL版本大于等于8.0，则排除tlinux 1.2操作系统

    if mysql_version and mysql_version_parse(mysql_version) >= 8000000:
        details["os_names"] = ["tlinux-1.2", ""]
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


def calculate_recovery_min_disk_size_gb(
    data_dir_size_mb: float,
    storage_engine: str,
    backup_type: str,
    total_filesize: int,
) -> int:
    """根据备份信息计算回档所需的最小磁盘大小(GB)

    优先按备份元信息中的 data_dir_size_mb 估算；如果没有，则按 total_filesize 兜底。

    @param data_dir_size_mb: 备份记录中数据目录大小(MB)
    @param storage_engine: 存储引擎(innodb / 其他)
    @param backup_type: 备份类型(logical / physical)
    @param total_filesize: 备份文件总大小(字节，data_dir_size_mb<=0 时作为兜底)
    @return: 最小磁盘大小(GB)
    """
    if data_dir_size_mb and data_dir_size_mb > 0:
        # 扩大并转换为 GB(MB 转 GB 需要除以 1024)
        if storage_engine == "innodb":
            data_dir_size_mb = data_dir_size_mb * 1.6
            if backup_type == "logical":
                data_dir_size_mb = data_dir_size_mb * 2.6
        else:
            data_dir_size_mb = data_dir_size_mb * 4.3
        logger.debug(_("计算后的数据目录大小: {} MB").format(data_dir_size_mb))
        min_disk_size = int(data_dir_size_mb / 1024)
    else:
        min_disk_size = calculate_min_disk_size(total_filesize)
    logger.debug(_("计算后的最小磁盘大小: {} GB").format(min_disk_size))
    return min_disk_size


def get_master_storage_spec(cluster: Cluster) -> list:
    """查询集群 master 节点的规格 storage_spec(可能多块盘)

    任何查询异常或缺失都会被吞掉并返回空列表，由调用方退避到原单盘模式。

    @param cluster: 待演练的集群
    @return: master 节点机器的 spec_config["storage_spec"] 列表，
        例如：[
            {"mount_point": "/data", "min": 100, "max": 500, "type": "ssd"},
            {"mount_point": "/data1", "min": 200, "max": 1000, "type": "ssd"},
        ]
        若未获取到则返回空列表
    """
    try:
        main_storage = cluster.main_storage_instances().first()
        if not main_storage:
            logger.debug(_("集群 {} 未找到 master 节点，退避为单盘模式申请").format(cluster.immute_domain))
            return []

        spec_config = main_storage.machine.spec_config or {}
        storage_spec = spec_config.get("storage_spec") or []
        if not storage_spec:
            logger.debug(
                _("集群 {} master 节点(IP {}) 无 storage_spec 信息，退避为单盘模式申请").format(
                    cluster.immute_domain, main_storage.machine.ip
                )
            )
            return []

        logger.debug(
            _("集群 {} master 节点(IP {}) storage_spec: {}").format(
                cluster.immute_domain, main_storage.machine.ip, storage_spec
            )
        )
        return list(storage_spec)
    except Exception as e:
        logger.warning(_("查询集群 {} master 节点规格异常，退避为单盘模式申请: {}").format(cluster.immute_domain, str(e)))
        return []


def build_recovery_storage_spec(
    cluster: Cluster,
    data_dir_size_mb: float,
    storage_engine: str,
    backup_type: str,
    total_filesize: int,
) -> list:
    """构建回档资源申请所需的 storage_spec

    优先从待演练集群的 master 节点规格中获取盘符布局，多块盘场景下：
    - 超过 2 块盘时只按原规格列表顺序取前 2 块申请，避免资源池按 3 盘及以上匹配失败
    - 数据盘(/data1 优先，否则 /data)按基于备份估算出的容量申请，且不小于原规格 min 值
    - 其它盘按原规格 min 值申请，保持 mount_point 与 master 一致
    - 演练场景只关心磁盘容量是否满足，不限定磁盘类型(SSD/HDD/CLOUD_SSD 等)
    如果未获取到 master 规格，则按单盘(无 mount_point)申请，由资源池默认处理。

    @param cluster: 待演练的集群
    @param data_dir_size_mb: 备份记录的数据目录大小(MB)
    @param storage_engine: 存储引擎
    @param backup_type: 备份类型
    @param total_filesize: 备份文件总大小(字节)
    @return: storage_spec 列表
    """
    min_disk_size_gb = calculate_recovery_min_disk_size_gb(
        data_dir_size_mb=data_dir_size_mb,
        storage_engine=storage_engine,
        backup_type=backup_type,
        total_filesize=total_filesize,
    )

    # 单盘原模式兜底（不指定 mount_point，由资源池默认处理）
    fallback_spec = [{"max": 2147483647, "min": min_disk_size_gb}]

    master_storage_spec = get_master_storage_spec(cluster)
    if not master_storage_spec:
        logger.debug(_("集群 {} 按单盘模式申请，最小容量: {} GB").format(cluster.immute_domain, min_disk_size_gb))
        return fallback_spec

    # 解析 master 规格构建多盘申请，任何异常都退避到单盘模式
    try:
        # 超过 2 块盘时只取列表前 2 项，再在保留盘中选择数据盘
        if len(master_storage_spec) > 2:
            original_disk_count = len(master_storage_spec)
            master_storage_spec = master_storage_spec[:2]
            truncated_mounts = [item.get("mount_point") for item in master_storage_spec]
            logger.debug(
                _("集群 {} master 规格共 {} 块盘，演练申请仅取前 2 块: {}").format(
                    cluster.immute_domain, original_disk_count, truncated_mounts
                )
            )

        # 选择数据盘 mount_point：优先 /data1，否则 /data，否则取第一块盘
        mount_points = [item.get("mount_point") for item in master_storage_spec]
        if "/data1" in mount_points:
            data_mount_point = "/data1"
        elif "/data" in mount_points:
            data_mount_point = "/data"
        else:
            data_mount_point = mount_points[0] if mount_points else None

        # 演练场景只关心磁盘容量是否满足，不限定磁盘类型(SSD/HDD/CLOUD_SSD 等)
        storage_spec_list = []
        for item in master_storage_spec:
            mount_point = item.get("mount_point")
            original_min = int(item.get("min", 0) or 0)

            # 数据盘按计算值申请，且不小于原规格 min；其它盘保持原规格 min
            if mount_point == data_mount_point:
                spec_min = max(min_disk_size_gb, original_min)
            else:
                spec_min = original_min

            spec_item = {
                "max": 2147483647,
                "min": spec_min,
            }
            if mount_point:
                spec_item["mount_point"] = mount_point
            storage_spec_list.append(spec_item)

        if not storage_spec_list:
            logger.warning(_("集群 {} 解析 master 规格后为空，退避为单盘模式申请").format(cluster.immute_domain))
            return fallback_spec

        logger.debug(_("集群 {} 申请 storage_spec(基于 master 盘符布局): {}").format(cluster.immute_domain, storage_spec_list))
        return storage_spec_list
    except Exception as e:
        logger.warning(
            _("集群 {} 解析 master 规格异常，退避为单盘模式申请: {}, 原始规格: {}").format(
                cluster.immute_domain, str(e), master_storage_spec
            )
        )
        return fallback_spec


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


def get_recent_5days_range():
    """
    获取当前时间往前5天的时间范围
    Returns:
        tuple: (start_time, end_time) where both are datetime objects in UTC
    """
    now = datetime.now(django_timezone.utc)
    # 往前推5天
    start_time = now - timedelta(days=7)
    # 结束时间为当前时间
    end_time = now - timedelta(days=1)

    return start_time, end_time


# 已演练 backup_id 只取近 N 天：候选/生成用的备份时间窗约 1 周，2 个月足够覆盖，避免全表加载数万历史 ID
EXERCISED_BACKUP_ID_LOOKBACK_DAYS = 90


def _load_exercised_backup_ids_for_candidate() -> Set[str]:
    """
    从主库加载近 3 个月已成功演练的 backup_id 集合（只加载一次）。

    注意：MysqlBackupResult 在 report 库，MySQLBackupRecoverTask 在主库，
    不能用跨库 Subquery；这里拉到 Python set 后在应用层过滤。
    禁止再把它塞进 report 库的巨大 NOT IN。
    """
    try:
        since = django_timezone.now() - timedelta(days=EXERCISED_BACKUP_ID_LOOKBACK_DAYS)
        return set(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[TaskStatus.COMMIT_SUCCESS, TaskStatus.RECOVER_SUCCESS],
                create_at__gte=since,
            ).values_list("backup_id", flat=True)
        )
    except Exception:
        return set()


def _load_exercised_backup_ids_for_task_gen() -> Set[str]:
    """任务生成阶段：近 3 个月、更宽状态的已演练 backup_id（主库，只加载一次）。"""
    try:
        since = django_timezone.now() - timedelta(days=EXERCISED_BACKUP_ID_LOOKBACK_DAYS)
        return set(
            MySQLBackupRecoverTask.objects.filter(
                task_status__in=[
                    TaskStatus.COMMIT_SUCCESS,
                    TaskStatus.RECOVER_SUCCESS,
                    TaskStatus.RESOURCE_RETURN_SUCCESS,
                    TaskStatus.GENERATED,
                    TaskStatus.DEPLOY_SUCCESS,
                ],
                phase=TaskPhase.DONE,
                create_at__gte=since,
            ).values_list("backup_id", flat=True)
        )
    except Exception:
        return set()


def _cluster_has_backup_record(
    cluster_id: int,
    cluster_address: str,
    exercised_backup_ids: Optional[Set[str]] = None,
) -> bool:
    """
    查询集群是否存在可用的全备记录。

    - 只查 report 库的 MysqlBackupResult（按 cluster_id 点查）
    - 已演练 backup_id 在 Python set 中过滤，避免跨库 Subquery / 巨大 NOT IN
    """
    start_time, end_time = get_last_week_range()
    if exercised_backup_ids is None:
        exercised_backup_ids = _load_exercised_backup_ids_for_candidate()

    conditions = Q(
        cluster_id=cluster_id,
        cluster_address=cluster_address,
        is_full_backup=1,
        backup_consistent_time__range=(start_time, end_time),
    ) & ~Q(mysql_role__in=["spider_master", "spider_mnt", "TDBCTL"])

    backup_ids = (
        MysqlBackupResult.objects.filter(conditions)
        .annotate(json_valid=Func(F("extra_fields"), function="JSON_VALID"))
        .filter(json_valid=1)
        .values_list("backup_id", flat=True)
        .iterator(chunk_size=50)
    )
    for backup_id in backup_ids:
        if backup_id not in exercised_backup_ids:
            return True
    return False


def cluster_has_backup_record(cluster_id: int) -> bool:
    """
    查询集群是否存在备份记录（兼容旧调用方）。
    """
    func_start = time.time()
    cluster = Cluster.objects.get(id=cluster_id)
    exercised_backup_ids = _load_exercised_backup_ids_for_candidate()
    result = _cluster_has_backup_record(cluster.id, cluster.immute_domain, exercised_backup_ids)
    total_time = time.time() - func_start
    if total_time > 0.1:
        logger.debug(
            _("集群 {} 备份检查耗时: {:.3f}秒, 已演练备份数:{}").format(cluster.immute_domain, total_time, len(exercised_backup_ids))
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

    # 第一阶段：收集所有集群的备份信息
    logger.info(_("开始收集 {} 个集群的备份信息").format(len(clusters)))
    cluster_backup_info = []

    # 主库加载已演练 backup_id；report 库查询后在 Python 侧过滤（避免跨库 Subquery）
    exercised_backup_ids = _load_exercised_backup_ids_for_task_gen()
    logger.info(_("已加载已演练备份ID {} 个（任务生成阶段）").format(len(exercised_backup_ids)))

    # 获取当前时间往前5天的时间范围
    start_time, end_time = get_recent_5days_range()
    logger.info(_("查询备份记录时间范围: {} 至 {}").format(start_time, end_time))

    for cluster in clusters:
        # 注意：忽略检查已在 get_exercise_clusters 中完成，这里不需要重复检查
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

        # 只查 report 库；已演练过滤放在 Python，避免跨库 / 巨大 NOT IN
        backup_result = None
        backup_candidates = (
            MysqlBackupResult.objects.filter(conditions)
            .annotate(json_valid=Func(F("extra_fields"), function="JSON_VALID"))
            .filter(json_valid=1)
            .order_by("-backup_consistent_time")
            .iterator(chunk_size=20)
        )
        for candidate in backup_candidates:
            if candidate.backup_id not in exercised_backup_ids:
                backup_result = candidate
                break

        if not backup_result:
            logger.debug(_("集群 {} 没有可用的备份记录").format(cluster.immute_domain))
            continue

        logger.debug(
            _("集群 {} 找到备份记录: backup_id={}, backup_time={}").format(
                cluster.immute_domain, backup_result.backup_id, backup_result.backup_consistent_time
            )
        )

        # 将集群、备份记录和备份大小存入列表
        cluster_backup_info.append((cluster, backup_result, backup_result.total_filesize))

    logger.info(_("已收集 {} 个集群的备份信息，开始生成任务").format(len(cluster_backup_info)))

    # 第三阶段：生成回档任务
    for cluster, backup_result, backup_size in cluster_backup_info:
        backup_file_size_gb = bytes_to_gb(backup_size)
        logger.debug(_("开始处理集群 {} 的备份，备份大小: {:.2f} GB").format(cluster.immute_domain, backup_file_size_gb))

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
            logger.error(_("解析JSON字段失败: {}, 备份记录: {}").format(e, backup_record))
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
        backup_type = backup_record.get("backup_type", "")

        # 打印备份信息
        logger.debug(_("演练备份记录: {}").format(backup_record))
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
            backup_type=backup_type,
            backup_tool=backup_tool,
            time_zone=time_zone,
            task_id=root_id,
            task_status=TaskStatus.GENERATED,
            phase=TaskPhase.RUNNING,
            creator="system",
            updater="system",
        )
        # 构建资源申请的 storage_spec(自动适配 master 节点的多盘布局)
        storage_spec_list = build_recovery_storage_spec(
            cluster=cluster,
            data_dir_size_mb=data_dir_size_mb,
            storage_engine=storage_engine,
            backup_type=backup_type,
            total_filesize=backup_record["total_filesize"],
        )

        # 申请资源
        mysql_version = backup_record.get("mysql_version", "")
        apply_params = build_resource_apply_params(root_id, storage_spec_list, mysql_version)
        resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
        if resp["code"] != 0:
            if resp["code"] == ResourceApplyErrCode.RESOURCE_LAKE:
                logger.error(
                    _(
                        "资源不足申请失败，请前往补货后重试。集群信息: 集群域名={}, 集群ID={}, 备份ID={}, "
                        "备份大小={:.2f}GB, storage_spec={}, MySQL版本={}, 错误信息: {}"
                    ).format(
                        cluster.immute_domain,
                        cluster.id,
                        backup_id,
                        backup_file_size_gb,
                        storage_spec_list,
                        mysql_version,
                        resp.get("message"),
                    )
                )
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
            logger.debug(f"resource_request_id: {resource_request_id}, apply_data: {apply_data}")
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
            task.phase = TaskPhase.DONE
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


def _calculate_target_ratio(
    tendbcluster_cluster_ratio: float,
    tendbcluster_recent: int,
    tendbha_recent: int,
    total_recent: int,
) -> tuple:
    """计算目标比例和演练比例"""
    if total_recent == 0:
        return tendbcluster_cluster_ratio, 0.0, 0.0

    tendbcluster_exercise_ratio = tendbcluster_recent / total_recent
    tendbha_exercise_ratio = tendbha_recent / total_recent

    # 根据演练比例调整目标比例
    balance_factor = 0.3
    exercise_diff = tendbcluster_exercise_ratio - tendbha_exercise_ratio
    adjustment = exercise_diff * balance_factor
    target_ratio = tendbcluster_cluster_ratio - adjustment

    # 确保比例在合理范围内
    min_ratio = max(0.1, tendbcluster_cluster_ratio * 0.5)
    max_ratio = min(0.9, tendbcluster_cluster_ratio * 2.0)
    target_ratio = max(min_ratio, min(max_ratio, target_ratio))

    return target_ratio, tendbcluster_exercise_ratio, tendbha_exercise_ratio


def _check_balance_need(
    tendbcluster_recent: int,
    tendbha_recent: int,
    total_recent: int,
    tendbcluster_cluster_ratio: float,
    tendbha_cluster_ratio: float,
) -> tuple:
    """判断是否需要优先平衡"""
    need_balance_tendbcluster = False
    need_balance_tendbha = False

    if total_recent > 0:
        if tendbcluster_recent == 0 and tendbha_recent > 0:
            need_balance_tendbcluster = True
        elif tendbha_recent == 0 and tendbcluster_recent > 0:
            need_balance_tendbha = True
        elif tendbcluster_recent > 0 and tendbha_recent > 0:
            if tendbcluster_recent * 5 < tendbha_recent:
                need_balance_tendbcluster = True
            elif tendbha_recent * 5 < tendbcluster_recent:
                need_balance_tendbha = True
    else:
        if tendbcluster_cluster_ratio < 0.1 and tendbha_cluster_ratio > 0.9:
            need_balance_tendbcluster = True
        elif tendbha_cluster_ratio < 0.1 and tendbcluster_cluster_ratio > 0.9:
            need_balance_tendbha = True

    return need_balance_tendbcluster, need_balance_tendbha


def _allocate_resources(
    num: int,
    target_tendbcluster_ratio: float,
    need_balance_tendbcluster: bool,
    need_balance_tendbha: bool,
) -> tuple:
    """根据资源数量和平衡需求分配资源"""
    DEFAULT_THRESHOLD = 0.5
    BALANCE_THRESHOLD_LOW = 0.2
    BALANCE_THRESHOLD_HIGH = 0.8
    MIN_BALANCE_RATIO = 0.15
    MIN_SIGNIFICANT_RATIO = 0.2

    if num == 1:
        # 计算阈值
        threshold = DEFAULT_THRESHOLD
        if need_balance_tendbcluster and target_tendbcluster_ratio >= MIN_BALANCE_RATIO:
            threshold = BALANCE_THRESHOLD_LOW
        elif need_balance_tendbha and (1 - target_tendbcluster_ratio) >= MIN_BALANCE_RATIO:
            threshold = BALANCE_THRESHOLD_HIGH

        tendbcluster_target = 1 if target_tendbcluster_ratio >= threshold else 0
        tendbha_target = 1 - tendbcluster_target

    elif num == 2:
        if need_balance_tendbcluster or need_balance_tendbha:
            tendbcluster_target = tendbha_target = 1
        else:
            tendbcluster_target = round(num * target_tendbcluster_ratio)
            tendbha_target = num - tendbcluster_target
            if 0.1 <= target_tendbcluster_ratio <= 0.9:
                tendbcluster_target = tendbha_target = 1

    else:
        tendbcluster_target = round(num * target_tendbcluster_ratio)
        tendbha_target = num - tendbcluster_target

        # 确保比例>=20%或需要平衡的类型至少分配1台
        if tendbcluster_target == 0 and (
            target_tendbcluster_ratio >= MIN_SIGNIFICANT_RATIO or need_balance_tendbcluster
        ):
            tendbcluster_target, tendbha_target = 1, num - 1
        elif tendbha_target == 0 and (target_tendbcluster_ratio <= 1 - MIN_SIGNIFICANT_RATIO or need_balance_tendbha):
            tendbha_target, tendbcluster_target = 1, num - 1

        # 修正四舍五入可能导致的总数超标
        if tendbcluster_target + tendbha_target > num:
            if target_tendbcluster_ratio >= 0.5:
                tendbcluster_target, tendbha_target = num, 0
            else:
                tendbcluster_target, tendbha_target = 0, num

    return tendbcluster_target, tendbha_target


def calculate_dynamic_cluster_type_targets(
    num: int, recent_stats: dict, tendbcluster_count: int, tendbha_count: int
) -> tuple:
    """
    根据最近24小时的演练情况和集群实际数量动态计算各集群类型的目标数量

    Args:
        num: 总需要选择的集群数量
        recent_stats: 最近24小时的演练统计信息
        tendbcluster_count: TenDBCluster类型的实际集群数量
        tendbha_count: TenDBHA类型的实际集群数量

    Returns:
        tuple: (tendbcluster_target, tendbha_target)
    """
    tendbcluster_recent = recent_stats["tendbcluster_count"]
    tendbha_recent = recent_stats["tendbha_count"]
    total_recent = recent_stats["total_count"]
    total_cluster_count = tendbcluster_count + tendbha_count

    logger.info(
        _("最近24小时演练统计: TenDBCluster {} 次, TenDBHA {} 次, 总计 {} 次").format(
            tendbcluster_recent, tendbha_recent, total_recent
        )
    )
    logger.info(
        _("集群实际数量: TenDBCluster {} 个, TenDBHA {} 个, 总计 {} 个").format(
            tendbcluster_count, tendbha_count, total_cluster_count
        )
    )

    # 边界情况处理
    if total_cluster_count == 0:
        tendbcluster_target = num // 2
        tendbha_target = num - tendbcluster_target
        logger.info(_("没有可用集群，采用平均分配策略"))
        return tendbcluster_target, tendbha_target

    if tendbcluster_count == 0:
        logger.info(_("TenDBCluster 集群数量为 0，目标数量设为 0"))
        return 0, num
    if tendbha_count == 0:
        logger.info(_("TenDBHA 集群数量为 0，目标数量设为 0"))
        return num, 0

    # 计算集群数量比例
    tendbcluster_cluster_ratio = tendbcluster_count / total_cluster_count
    tendbha_cluster_ratio = tendbha_count / total_cluster_count

    # 计算目标比例
    target_ratio, exercise_ratio_c, exercise_ratio_h = _calculate_target_ratio(
        tendbcluster_cluster_ratio, tendbcluster_recent, tendbha_recent, total_recent
    )

    # 判断是否需要平衡
    need_balance_c, need_balance_h = _check_balance_need(
        tendbcluster_recent, tendbha_recent, total_recent, tendbcluster_cluster_ratio, tendbha_cluster_ratio
    )

    # 分配资源
    tendbcluster_target, tendbha_target = _allocate_resources(num, target_ratio, need_balance_c, need_balance_h)

    # 日志输出
    logger.info(
        _("分配结果({}台): 集群比例(C:{:.1%}/H:{:.1%}), 演练比例(C:{:.1%}/H:{:.1%}), " "目标比例{:.1%}, 结果(C:{}/H:{})").format(
            num,
            tendbcluster_cluster_ratio,
            tendbha_cluster_ratio,
            exercise_ratio_c,
            exercise_ratio_h,
            target_ratio,
            tendbcluster_target,
            tendbha_target,
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

    logger.debug(
        _("演练忽略配置: 忽略业务 {} 个 {}, 忽略集群 {} 个 {}").format(
            len(ignored_biz_ids), ignored_biz_ids, len(ignored_cluster_ids), ignored_cluster_ids
        )
    )

    # 获取最近24小时的演练统计信息
    recent_stats = MySQLBackupRecoverTask.get_recent_24h_exercise_cluster_type_stats()

    # 统计TenDBCluster和TenDBHA的实际数量
    cluster_count_exclude_condition = Q()
    if ignored_biz_ids:
        cluster_count_exclude_condition |= Q(bk_biz_id__in=ignored_biz_ids)
    if ignored_cluster_ids:
        cluster_count_exclude_condition |= Q(id__in=ignored_cluster_ids)
    tendbcluster_count = (
        Cluster.objects.exclude(cluster_count_exclude_condition).filter(cluster_type=ClusterType.TenDBCluster).count()
    )
    tendbha_count = (
        Cluster.objects.exclude(cluster_count_exclude_condition).filter(cluster_type=ClusterType.TenDBHA).count()
    )

    logger.info(_("可用集群数量统计: TenDBCluster {} 个, TenDBHA {} 个").format(tendbcluster_count, tendbha_count))

    # 动态计算各集群类型的目标数量，考虑实际集群数量
    target_tendbcluster, target_tendbha = calculate_dynamic_cluster_type_targets(
        num, recent_stats, tendbcluster_count, tendbha_count
    )

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


def _get_ignore_configs():
    """
    获取需要忽略的业务ID和集群ID配置
    包括：忽略配置、最近2天失败的集群、正在运行任务的集群

    Returns:
        tuple: (ignored_biz_ids, ignored_cluster_ids)
            ignored_biz_ids: 需要忽略的业务ID列表
            ignored_cluster_ids: 需要忽略的集群ID列表（已包含失败和运行中的集群）
    """
    ignored_biz_ids = ExerciseIgnoreConfig.get_ignored_biz_ids()
    ignored_cluster_ids = ExerciseIgnoreConfig.get_ignored_cluster_ids()
    failed_cluster_ids = MySQLBackupRecoverTask.get_recent_2days_failed_cluster_ids()
    running_task_cluster_ids = MySQLBackupRecoverTask.get_running_task_cluster_ids()
    ignored_cluster_ids.extend(failed_cluster_ids)
    ignored_cluster_ids.extend(running_task_cluster_ids)
    return ignored_biz_ids, ignored_cluster_ids


def _build_exclude_condition(biz_ids=None, cluster_ids=None):
    """
    构建排除条件的Q对象

    Args:
        biz_ids: 需要排除的业务ID列表
        cluster_ids: 需要排除的集群ID列表

    Returns:
        Q: Django Q对象，用于排除指定的业务或集群
    """
    exclude_condition = Q()
    if biz_ids:
        exclude_condition |= Q(bk_biz_id__in=biz_ids)
    if cluster_ids:
        exclude_condition |= Q(id__in=cluster_ids)
    return exclude_condition


def _collect_unpracticed_clusters(
    exclude_biz_ids,
    exclude_cluster_id,
    global_priority_queue,
    ignore_configs=None,
):
    """收集从未演练过的业务的集群 - 最高优先级。"""
    count = 0
    unpracticed_biz_clusters = 0
    if ignore_configs is None:
        ignored_biz_ids, ignored_cluster_ids = _get_ignore_configs()
    else:
        ignored_biz_ids, ignored_cluster_ids = ignore_configs
    exclude_biz_ids.extend(ignored_biz_ids)
    exclude_cluster_id.extend(ignored_cluster_ids)
    # 使用 Q 对象实现 OR 逻辑：排除业务ID在列表中 OR 集群ID在列表中的集群
    exclude_condition = _build_exclude_condition(exclude_biz_ids, exclude_cluster_id)

    clusters = (
        Cluster.objects.exclude(exclude_condition)
        .filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
        .only("id", "immute_domain", "bk_biz_id", "cluster_type")
        .iterator(chunk_size=500)
    )

    # 按业务分组统计
    unpracticed_biz_ids = set()

    for cluster in clusters:
        # 从未演练过的业务的集群获得绝对最高优先级
        heapq.heappush(global_priority_queue, Task(100000, cluster))
        unpracticed_biz_ids.add(cluster.bk_biz_id)
        unpracticed_biz_clusters += 1
        count += 1

    if unpracticed_biz_ids:
        logger.info(_("发现 {} 个从未演练过的业务，包含 {} 个集群，将获得最高优先级").format(len(unpracticed_biz_ids), unpracticed_biz_clusters))
        logger.debug(_("从未演练过的业务ID列表: {}").format(sorted(list(unpracticed_biz_ids))))
    else:
        logger.info(_("未发现从未演练过的业务"))

    return count, unpracticed_biz_ids


def _collect_all_clusters(
    global_priority_queue,
    recover_success_map,
    count,
    num,
    unpracticed_biz_ids,
    ignore_configs=None,
):
    """收集所有集群 - 最低优先级兜底，排除从未演练过的业务（已以最高优先级添加）"""
    if ignore_configs is None:
        ignored_biz_ids, ignored_cluster_ids = _get_ignore_configs()
    else:
        ignored_biz_ids, ignored_cluster_ids = ignore_configs
    exclude_condition = _build_exclude_condition(ignored_biz_ids, ignored_cluster_ids)
    # 排除从未演练过的业务，因为这些集群已经在 _collect_unpracticed_clusters 中以最高优先级添加了
    if unpracticed_biz_ids:
        exclude_condition |= Q(bk_biz_id__in=unpracticed_biz_ids)
    clusters = (
        Cluster.objects.filter(cluster_type__in=[ClusterType.TenDBCluster, ClusterType.TenDBHA])
        .exclude(exclude_condition)
        .only("id", "immute_domain", "bk_biz_id", "cluster_type")
        .iterator(chunk_size=500)
    )
    fallback_clusters = 0

    for cluster in clusters:
        recover_success_cnt = recover_success_map.get(cluster.immute_domain, 0)
        # 兜底集群使用最低优先级
        priority = max(50000 - recover_success_cnt * 10, 10)  # 优先级范围 100-500
        heapq.heappush(global_priority_queue, Task(priority, cluster))
        fallback_clusters += 1
        count += 1

    if fallback_clusters > 0:
        logger.info(_("添加了 {} 个兜底集群").format(fallback_clusters))

    return count


def _is_cluster_type_quota_full(
    cluster_type,
    tendbcluster_count,
    tendbha_count,
    max_needed_tendbcluster,
    max_needed_tendbha,
):
    """判断指定集群类型的候选配额是否已满。"""
    if cluster_type == ClusterType.TenDBCluster:
        return max_needed_tendbcluster == 0 or tendbcluster_count >= max_needed_tendbcluster
    if cluster_type == ClusterType.TenDBHA:
        return max_needed_tendbha == 0 or tendbha_count >= max_needed_tendbha
    # 非目标类型直接视为已满，跳过
    return True


def _collect_valid_candidates(global_priority_queue, target_tendbcluster, target_tendbha):
    """收集有效的候选集群。

    优化点：
    1. 两种类型配额都满后，在循环顶部立即 break，避免弹空整个堆
    2. 单类型已满时静默跳过该类型，不再逐集群打 info 日志
    3. 已演练 backup_id 从主库加载一次到 set；report 库按集群点查后在 Python 过滤
       （两表分属不同库，不能跨库 Subquery）
    """
    start_time = time.time()
    all_candidates = []
    tendbcluster_count = 0
    tendbha_count = 0

    # 性能统计变量
    total_clusters_checked = 0
    backup_check_count = 0
    backup_check_time = 0
    no_backup_clusters = 0
    skipped_quota_full = 0

    # 计算需要的最大集群数量（预留一些余量以防部分集群没有有效备份）
    max_needed_tendbcluster = target_tendbcluster * 5  # 5倍余量
    max_needed_tendbha = target_tendbha * 5  # 5倍余量

    total_candidate_clusters = len(global_priority_queue)
    logger.info(_("开始检查候选集群，总计 {} 个集群待检查").format(total_candidate_clusters))
    logger.info(
        _("本轮候选收集配额: TenDBCluster 目标 {} (最多检查 {}), TenDBHA 目标 {} (最多检查 {})").format(
            target_tendbcluster, max_needed_tendbcluster, target_tendbha, max_needed_tendbha
        )
    )

    # 主库一次加载已演练 backup_id；后续点查只打 report 库，在 Python 侧过滤
    exercised_load_start = time.time()
    exercised_backup_ids = _load_exercised_backup_ids_for_candidate()
    logger.info(_("已加载已演练备份ID {} 个，耗时 {:.2f}秒").format(len(exercised_backup_ids), time.time() - exercised_load_start))

    while global_priority_queue:
        # P0: 两种类型都已满额，立即结束，避免弹空整个堆并刷日志
        if tendbcluster_count >= max_needed_tendbcluster and tendbha_count >= max_needed_tendbha:
            logger.info(_("已收集足够数量的候选集群，提前退出检查"))
            break

        task = heapq.heappop(global_priority_queue)
        cluster = task.cluster
        total_clusters_checked += 1

        # 单类型配额已满：静默跳过，不再逐条打 info（避免 CPU/日志尖峰）
        if _is_cluster_type_quota_full(
            cluster.cluster_type, tendbcluster_count, tendbha_count, max_needed_tendbcluster, max_needed_tendbha
        ):
            skipped_quota_full += 1
            continue

        logger.debug(
            _("从优先级队列取出集群: {} (ID: {}), 业务ID: {}, 优先级: {}, 集群类型: {}").format(
                cluster.immute_domain, cluster.id, cluster.bk_biz_id, task.priority, cluster.cluster_type
            )
        )

        backup_start = time.time()
        has_backup = _cluster_has_backup_record(cluster.id, cluster.immute_domain, exercised_backup_ids)
        backup_check_time += time.time() - backup_start
        backup_check_count += 1

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

        # 每处理50个“实际做了备份检查”的集群输出一次进度
        if backup_check_count % 50 == 0:
            logger.info(
                _("集群检查进度: 已检查备份 {} 个, 队列已弹出 {}/{}, 有效候选 {} 个").format(
                    backup_check_count, total_clusters_checked, total_candidate_clusters, len(all_candidates)
                )
            )

    total_time = time.time() - start_time
    avg_backup_check = backup_check_time / max(backup_check_count, 1)

    logger.info(_("集群候选筛选完成统计:"))
    logger.info(_("- 总耗时: {:.2f}秒").format(total_time))
    logger.info(_("- 队列弹出总数: {}").format(total_clusters_checked))
    logger.info(_("- 因配额已满跳过: {}").format(skipped_quota_full))
    logger.info(_("- 实际备份检查数: {}").format(backup_check_count))
    logger.info(_("- 备份检查耗时: {:.2f}秒 (平均 {:.3f}秒/集群)").format(backup_check_time, avg_backup_check))
    logger.info(_("- 无备份集群数: {}").format(no_backup_clusters))
    logger.info(
        _("- 有效候选集群: TenDBCluster {} 个, TenDBHA {} 个, 总计 {} 个").format(
            tendbcluster_count, tendbha_count, len(all_candidates)
        )
    )

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
    # ignore 配置只取一次，避免未演练/兜底两阶段重复查询
    ignore_configs = _get_ignore_configs()

    global_priority_queue = []  # 全局优先级队列
    # 先收集从未演练过的业务的集群（最高优先级）
    count, unpracticed_biz_ids = _collect_unpracticed_clusters(
        exclude_biz_ids,
        exclude_cluster_id,
        global_priority_queue,
        ignore_configs=ignore_configs,
    )
    # 收集所有集群作为兜底（最低优先级），排除从未演练过的业务，避免重复
    _collect_all_clusters(
        global_priority_queue,
        recover_success_map,
        count,
        num,
        unpracticed_biz_ids,
        ignore_configs=ignore_configs,
    )
    collect_time = time.time() - collect_start

    # 收集有效候选集群（按需点查备份，凑满配额即停）
    validation_start = time.time()
    all_candidates = _collect_valid_candidates(
        global_priority_queue,
        target_tendbcluster,
        target_tendbha,
    )
    validation_time = time.time() - validation_start

    # only() 加载的轻量对象在后续申请资源时可能访问关联字段，这里按 ID 回表完整 Cluster
    if all_candidates:
        cluster_map = {c.id: c for c in Cluster.objects.filter(id__in=[c.id for c in all_candidates])}
        all_candidates = [cluster_map[c.id] for c in all_candidates if c.id in cluster_map]

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
        logger.debug(_("选中集群 {} ({}): 历史演练成功次数 {}").format(cluster.immute_domain, cluster.cluster_type, success_count))

    return rs


def return_resource(params: Dict[str, Any]) -> None:
    """
    归还资源，支持多次重试，重试间隔先大后小
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
    # 重试配置：重试间隔先大后小（秒）
    retry_intervals = [4, 3, 2, 1]
    max_retries = len(retry_intervals) + 1  # 总共尝试 5 次（1次初始 + 4次重试）

    last_error = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # 重试时等待一段时间
                wait_time = retry_intervals[attempt - 1]
                logger.info(_("第 {} 次重试归还资源，等待 {} 秒后执行").format(attempt, wait_time))
                time.sleep(wait_time)

            resp = DBResourceApi.resource_import(params=params, raw=True)
            if resp["code"] == 0:
                logger.info(_("归还资源成功"))
                return
            else:
                error_msg = resp.get("message", "")
                logger.warning(_("归还资源失败（第 {} 次尝试）: {}").format(attempt + 1, error_msg))
                last_error = error_msg
        except Exception as e:
            logger.warning(_("归还资源时发生异常（第 {} 次尝试）: {}").format(attempt + 1, str(e)))
            last_error = str(e)

        # 如果是最后一次尝试，抛出异常
        if attempt == max_retries - 1:
            error_message = _("归还资源失败，已重试 {} 次，最后错误: {}").format(max_retries, last_error)
            logger.error(error_message)
            raise Exception(error_message)
