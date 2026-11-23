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
import json
import logging
import os
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from django.core.cache import cache
from django.db.models import Count, F, Func, Q
from django.forms.models import model_to_dict
from django.utils import timezone as django_timezone
from django.utils.translation import gettext as _

from backend.components.dbconfig.client import DBConfigApi
from backend.components.dbconfig.constants import ConfFile, ConfType, FormatType, LevelName
from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterPhase, ClusterStatus, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.mysql_backup_rollback.gen_task import (
    EXERCISED_BACKUP_ID_LOOKBACK_DAYS,
    backup_info_format,
    build_recovery_storage_spec,
    bytes_to_gb,
    return_resource,
)
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

# 备份查询时间窗：统一为当前时间前 7 天至前 1 天（UTC）
BACKUP_LOOKBACK_START_DAYS = 7
BACKUP_LOOKBACK_END_DAYS = 1

# 规格不匹配需求缓存配置（方案 A：缓存集群所需规格，新进大机可装下时自动放行）
SPEC_CACHE_KEY_PREFIX = "mysql_backup_rollback:v2:spec_req:"
SPEC_CACHE_TTL_SECONDS = 2 * 60 * 60

# 无可用备份短 TTL 负缓存（防止大量长期无备份的未演练集群耗尽单轮扫描预算）
NO_BACKUP_CACHE_KEY_PREFIX = "mysql_backup_rollback:v2:no_backup:"
NO_BACKUP_CACHE_TTL_SECONDS = 30 * 60

# 非直连云区域(bk_cloud_id != 0) COS 备份上传能力缓存（按 (bk_biz_id, bk_cloud_id) 缓存 24 小时）
CLOUD_COS_CACHE_KEY_PREFIX = "mysql_backup_rollback:v2:cloud_cos:"
CLOUD_COS_CACHE_TTL_SECONDS = 24 * 60 * 60
CLOUD_COS_VALID_STORAGE_TYPES = ("cos", "s3", "bkrepo")

# 单轮扫描保护参数
CANDIDATE_POOL_MULTIPLIER = 4
HEAVY_PROBE_MULTIPLIER = 2
EXTRA_HEAVY_PROBE_LIMIT = 60
MAX_SCAN_CLUSTERS_PER_RUN = 500
SPEC_CACHE_BATCH_SIZE = 100
DEFAULT_MAX_CLUSTERS_PER_UNPRACTICED_BIZ = 1
# 判定为大备份/大规格主机的磁盘容量阈值（GB）：即使池里只剩一台大机也能优先给大备份
LARGE_DISK_THRESHOLD_GB = 500

# MySQL 8.0+ 不允许使用的操作系统名称
MYSQL8_EXCLUDED_OS_NAMES = ("tlinux-1.2", "")

# 备份角色排除集合（仅存权限/中控，不含业务数据全备）
EXCLUDED_BACKUP_ROLES = ("spider_master", "spider_mnt", "TDBCTL")

# 目标演练集群类型
EXERCISE_CLUSTER_TYPES = (ClusterType.TenDBCluster.value, ClusterType.TenDBHA.value)

# 视为已占用/已演练的任务状态（包含运行中，防止同一备份重复调度）
EXERCISED_TASK_STATUSES = (
    TaskStatus.GENERATED,
    TaskStatus.RESOURCE_APPLIED,
    TaskStatus.COMMIT_SUCCESS,
    TaskStatus.DEPLOY_SUCCESS,
    TaskStatus.RECOVER_SUCCESS,
    TaskStatus.RESOURCE_RETURN_SUCCESS,
)


@dataclass
class FreeHost:
    """
    资源池空闲主机画像。

    示例数据：
        FreeHost(
            bk_host_id=1001,
            ip="127.0.0.2",
            bk_cloud_id=0,
            bk_biz_id=2005000002,
            os_type="Linux",
            os_name="tlinux-2.6",
            mount_sizes={"/data": 200, "/data1": 1000},
            labels=["1"],
        )
    """

    bk_host_id: int
    ip: str
    bk_cloud_id: int
    bk_biz_id: int
    os_type: str
    os_name: str
    mount_sizes: Dict[str, int] = field(default_factory=dict)
    labels: List[Any] = field(default_factory=list)
    mount_disk_types: Dict[str, str] = field(default_factory=dict)

    @property
    def supports_mysql8(self) -> bool:
        return (self.os_name or "").strip().lower() not in MYSQL8_EXCLUDED_OS_NAMES

    @property
    def disk_count(self) -> int:
        return len(self.mount_sizes)

    @property
    def total_data_disk_gb(self) -> int:
        return sum(self.mount_sizes.values())

    @property
    def max_disk_gb(self) -> int:
        return max(self.mount_sizes.values(), default=0)

    def best_fit_sort_key(self, need_mysql8: bool) -> Tuple[int, int, int, int, int]:
        """最小够用（Best-Fit）排序键：优先把大盘/双盘/8.0兼容机留给高需求集群。"""
        waste_mysql8_flag = 1 if (not need_mysql8 and self.supports_mysql8) else 0
        return (
            waste_mysql8_flag,
            self.disk_count,
            self.total_data_disk_gb,
            self.max_disk_gb,
            self.bk_host_id,
        )


@dataclass
class ExerciseCandidate:
    """经过备份验证与规格计算的待匹配演练候选。"""

    cluster: Cluster
    tier: int
    recover_success_cnt: int
    backup_record: Dict[str, Any]
    parsed_extra_fields: Dict[str, Any]
    storage_spec: List[Dict[str, Any]]
    mysql_version: str
    need_mysql8: bool
    required_disk_gb: int
    backup_id: str
    backup_file_size_gb: float


def _safe_int_size(raw_size: Any) -> int:
    """安全解析磁盘容量（GB），非数字或负数统一返回 0。"""
    if raw_size is None or raw_size == "":
        return 0
    try:
        size_gb = int(float(raw_size))
    except (TypeError, ValueError):
        return 0
    return size_gb if size_gb > 0 else 0


def _parse_storage_device_details(raw_storage_device: Any) -> Tuple[Dict[str, int], Dict[str, str]]:
    """解析资源池返回的主机 storage_device 为 ({规范挂载点: 容量GB}, {规范挂载点: 磁盘类型})。"""
    if not raw_storage_device:
        return {}, {}
    data = raw_storage_device
    if isinstance(raw_storage_device, str):
        try:
            data = json.loads(raw_storage_device)
        except json.JSONDecodeError:
            return {}, {}
    if not isinstance(data, dict):
        return {}, {}

    mount_sizes: Dict[str, int] = {}
    mount_disk_types: Dict[str, str] = {}
    for mount_point, disk_info in data.items():
        if not mount_point or not isinstance(disk_info, dict):
            continue
        norm_mp = os.path.normpath(str(mount_point))
        size_gb = _safe_int_size(disk_info.get("size"))
        if size_gb > 0:
            mount_sizes[norm_mp] = size_gb
            mount_disk_types[norm_mp] = str(disk_info.get("disk_type") or "").strip()
    return mount_sizes, mount_disk_types


def _parse_storage_device(raw_storage_device: Any) -> Dict[str, int]:
    """解析资源池返回的主机 storage_device 为 {规范挂载点: 容量GB}。"""
    mount_sizes, unused_types = _parse_storage_device_details(raw_storage_device)
    return mount_sizes


def _is_mysql8_or_above(mysql_version: str) -> bool:
    """判断 MySQL 版本是否大于等于 8.0。"""
    if not mysql_version:
        return False
    try:
        return mysql_version_parse(mysql_version) >= 8000000
    except Exception:
        return False


def fetch_free_hosts() -> List[FreeHost]:
    """拉取演练专用空闲 Linux 主机完整明细，构建本地主机画像列表。"""
    params = {
        "status": ["Unused"],
        "resource_type": "mysql",
        "for_bizs": [MYSQL_BACKUPRECOVER_BIZ_ID],
        "labels": [MYSQL_BACKUPRECOVER_MCH_LABELS_ID],
        "os_type": "Linux",
        "gse_agent_alive": "true",
    }
    resp = DBResourceApi.resource_list(params=params, raw=True)
    if not isinstance(resp, dict) or resp.get("code") != 0:
        logger.error(_("获取演练空闲主机列表失败: {}").format(resp.get("message", "") if isinstance(resp, dict) else resp))
        return []

    data = resp.get("data")
    if not isinstance(data, dict):
        logger.info(_("没有可用的演练主机资源"))
        return []

    details = data.get("details") or []
    free_hosts: List[FreeHost] = []
    for item in details:
        if not isinstance(item, dict) or not item.get("bk_host_id") or not item.get("ip"):
            continue
        status = str(item.get("status") or "")
        if status and status != "Unused":
            continue
        os_type = str(item.get("os_type") or "")
        if os_type and os_type.lower() != "linux":
            continue
        mount_sizes, mount_disk_types = _parse_storage_device_details(item.get("storage_device"))
        free_hosts.append(
            FreeHost(
                bk_host_id=int(item["bk_host_id"]),
                ip=str(item["ip"]),
                bk_cloud_id=int(item.get("bk_cloud_id", 0) or 0),
                bk_biz_id=int(item.get("bk_biz_id", 0) or 0),
                os_type=os_type or "Linux",
                os_name=str(item.get("os_name") or ""),
                mount_sizes=mount_sizes,
                labels=list(item.get("labels") or []),
                mount_disk_types=mount_disk_types,
            )
        )

    logger.info(_("获取到 {} 台可用演练空闲主机").format(len(free_hosts)))
    return free_hosts


def _disk_matches_spec(disk_size: int, disk_type: str, spec: Dict[str, Any]) -> bool:
    """对齐 db-resource diskDetailMatch：校验磁盘容量区间与可选 disk_type。"""
    req_disk_type = str(spec.get("disk_type") or "").strip()
    if req_disk_type and disk_type.strip() != req_disk_type:
        return False
    min_size = int(spec.get("min", 0) or 0)
    max_size = int(spec.get("max", 0) or 0)
    if disk_size < min_size:
        return False
    if max_size > 0 and disk_size > max_size:
        return False
    return True


def host_can_fit(host: FreeHost, storage_spec: List[Dict[str, Any]], mysql_version: str) -> bool:
    """
    判断单台空闲主机是否满足演练的 OS 与磁盘规格需求。

    语义与 db-resource 的 MatchStorage / filterEmptyMountPointStorage / os_names 对齐。
    """
    if _is_mysql8_or_above(mysql_version) and not host.supports_mysql8:
        return False

    if not storage_spec:
        return True

    mounted_specs = [spec for spec in storage_spec if spec.get("mount_point")]
    unmounted_specs = [spec for spec in storage_spec if not spec.get("mount_point")]

    used_mounts: Set[str] = set()
    for spec in mounted_specs:
        mp = os.path.normpath(str(spec["mount_point"]))
        if mp not in host.mount_sizes:
            return False
        disk_type = host.mount_disk_types.get(mp, "")
        if not _disk_matches_spec(host.mount_sizes[mp], disk_type, spec):
            return False
        used_mounts.add(mp)

    if unmounted_specs:
        # 按需求容量从大到小分配剩余未占用盘，确保每个无挂载点需求对应独立磁盘
        remaining_disks = sorted(
            [
                (size, host.mount_disk_types.get(mp, ""))
                for mp, size in host.mount_sizes.items()
                if mp not in used_mounts
            ],
            key=lambda item: item[0],
            reverse=True,
        )
        sorted_specs = sorted(unmounted_specs, key=lambda s: int(s.get("min", 0) or 0), reverse=True)
        for spec in sorted_specs:
            matched_idx = None
            for idx, (disk_size, disk_type) in enumerate(remaining_disks):
                if _disk_matches_spec(disk_size, disk_type, spec):
                    matched_idx = idx
                    break
            if matched_idx is None:
                return False
            remaining_disks.pop(matched_idx)

    return True


def any_host_can_fit(hosts: List[FreeHost], storage_spec: List[Dict[str, Any]], mysql_version: str) -> bool:
    return any(host_can_fit(host, storage_spec, mysql_version) for host in hosts)


def _spec_cache_key(cluster_id: int) -> str:
    return f"{SPEC_CACHE_KEY_PREFIX}{cluster_id}"


def _no_backup_cache_key(cluster_id: int) -> str:
    return f"{NO_BACKUP_CACHE_KEY_PREFIX}{cluster_id}"


def _batch_get_spec_cache(cluster_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """批量从 Redis 读取集群历史规格需求缓存，异常时安全降级为空字典。"""
    if not cluster_ids:
        return {}
    key_to_cid = {_spec_cache_key(cid): cid for cid in cluster_ids}
    try:
        raw_map = cache.get_many(list(key_to_cid.keys()))
    except Exception as e:
        logger.warning(_("批量读取演练规格需求缓存失败，降级为无缓存: {}").format(str(e)))
        return {}
    return {key_to_cid[key]: value for key, value in raw_map.items() if isinstance(value, dict)}


def _batch_get_no_backup_cache(cluster_ids: List[int]) -> Set[int]:
    """批量从 Redis 读取近期无可用备份的集群集合，异常时安全降级为空集合。"""
    if not cluster_ids:
        return set()
    key_to_cid = {_no_backup_cache_key(cid): cid for cid in cluster_ids}
    try:
        raw_map = cache.get_many(list(key_to_cid.keys()))
    except Exception as e:
        logger.warning(_("批量读取演练无备份缓存失败，降级为无缓存: {}").format(str(e)))
        return set()
    return {key_to_cid[key] for key, value in raw_map.items() if value}


def _set_spec_cache(cluster_id: int, storage_spec: List[Dict[str, Any]], mysql_version: str) -> None:
    """记录当前空闲池装不下的集群规格需求，池里新进大机时自动放行。"""
    payload = {"storage_spec": storage_spec, "mysql_version": mysql_version}
    try:
        cache.set(_spec_cache_key(cluster_id), payload, timeout=SPEC_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(_("写入演练规格需求缓存失败(cluster_id={}): {}").format(cluster_id, str(e)))


def _set_no_backup_cache(cluster_id: int) -> None:
    """记录短时间内无可用备份的集群，避免重复查库耗尽扫描预算。"""
    try:
        cache.set(_no_backup_cache_key(cluster_id), 1, timeout=NO_BACKUP_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(_("写入演练无备份缓存失败(cluster_id={}): {}").format(cluster_id, str(e)))


def _delete_spec_cache(cluster_id: int) -> None:
    try:
        cache.delete(_spec_cache_key(cluster_id))
    except Exception:
        pass


def get_backup_query_range() -> Tuple[datetime, datetime]:
    """统一备份查询时间窗：当前时间前 7 天至前 1 天（UTC）。"""
    now = datetime.now(django_timezone.utc)
    return now - timedelta(days=BACKUP_LOOKBACK_START_DAYS), now - timedelta(days=BACKUP_LOOKBACK_END_DAYS)


def load_exercised_backup_ids() -> Set[str]:
    """加载近 90 天已演练或正在演练的 backup_id 集合（不吞 DB 异常）。"""
    since = django_timezone.now() - timedelta(days=EXERCISED_BACKUP_ID_LOOKBACK_DAYS)
    return set(
        MySQLBackupRecoverTask.objects.filter(
            task_status__in=EXERCISED_TASK_STATUSES,
            create_at__gte=since,
        ).values_list("backup_id", flat=True)
    )


def calculate_cluster_type_targets(
    total_hosts: int,
    recent_stats: Dict[str, int],
    tendbcluster_count: int,
    tendbha_count: int,
) -> Dict[str, int]:
    """
    基于存量占比与近 24h 演练占比的负反馈，计算各集群类型的软目标配额。

    修正旧版把 50%/50% 当平衡基准的问题：负反馈改为对照实际存量占比。
    """
    if total_hosts <= 0:
        return {ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: 0}

    total_clusters = tendbcluster_count + tendbha_count
    if total_clusters == 0:
        c_target = total_hosts // 2
        return {ClusterType.TenDBCluster.value: c_target, ClusterType.TenDBHA.value: total_hosts - c_target}
    if tendbcluster_count == 0:
        return {ClusterType.TenDBCluster.value: 0, ClusterType.TenDBHA.value: total_hosts}
    if tendbha_count == 0:
        return {ClusterType.TenDBCluster.value: total_hosts, ClusterType.TenDBHA.value: 0}

    cluster_ratio_c = tendbcluster_count / total_clusters
    total_recent = recent_stats.get("total_count", 0)
    recent_c = recent_stats.get("tendbcluster_count", 0)
    recent_h = recent_stats.get("tendbha_count", 0)

    if total_recent > 0:
        exercise_ratio_c = recent_c / total_recent
        # 对照实际存量占比进行负反馈纠偏
        exercise_diff = exercise_ratio_c - cluster_ratio_c
        target_ratio_c = cluster_ratio_c - exercise_diff * 0.5
        min_ratio = max(0.05, cluster_ratio_c * 0.5)
        max_ratio = min(0.95, max(cluster_ratio_c * 2.0, cluster_ratio_c + 0.15))
        target_ratio_c = max(min_ratio, min(max_ratio, target_ratio_c))
    else:
        target_ratio_c = cluster_ratio_c

    if total_hosts == 1:
        # 单台空闲机时：若某类近 24h 为 0 且另一类已演练，优先补 0 次的类型；否则按目标比例倾斜
        if recent_c == 0 and recent_h > 0:
            c_target = 1
        elif recent_h == 0 and recent_c > 0:
            c_target = 0
        else:
            c_target = 1 if target_ratio_c >= 0.5 else 0
    else:
        c_target = round(total_hosts * target_ratio_c)
        c_target = max(0, min(total_hosts, c_target))
        if c_target == 0 and recent_c == 0 and recent_h > 0:
            c_target = 1
        elif c_target == total_hosts and recent_h == 0 and recent_c > 0:
            c_target = total_hosts - 1

    h_target = total_hosts - c_target
    logger.info(
        _("类型配额计算({}台): 存量(C:{}/H:{}), 近24h(C:{}/H:{}), " "目标比例C:{:.1%}, 软配额(C:{}/H:{})").format(
            total_hosts,
            tendbcluster_count,
            tendbha_count,
            recent_c,
            recent_h,
            target_ratio_c,
            c_target,
            h_target,
        )
    )
    return {ClusterType.TenDBCluster.value: c_target, ClusterType.TenDBHA.value: h_target}


def _base_online_clusters_queryset():
    """仅保留在线且非临时/演练内置标签的目标类型集群。"""
    return (
        Cluster.objects.exclude_builtin_cluster_tags()
        .filter(
            cluster_type__in=EXERCISE_CLUSTER_TYPES,
            phase=ClusterPhase.ONLINE.value,
        )
        .exclude(status=ClusterStatus.TEMPORARY.value)
    )


def _build_exclude_q(biz_ids: Set[int], cluster_ids: Set[int]) -> Q:
    cond = Q()
    if biz_ids:
        cond |= Q(bk_biz_id__in=biz_ids)
    if cluster_ids:
        cond |= Q(id__in=cluster_ids)
    return cond


def _load_recover_success_map() -> Dict[int, int]:
    """按 cluster_id 聚合历史成功演练次数，命中 idx_cluster_task_status 索引。"""
    rows = (
        MySQLBackupRecoverTask.objects.filter(
            task_status__in=[TaskStatus.RESOURCE_RETURN_SUCCESS, TaskStatus.RECOVER_SUCCESS],
        )
        .values("cluster_id")
        .annotate(total=Count("*"))
    )
    return {row["cluster_id"]: row["total"] for row in rows}


def _round_robin_by_biz(clusters: List[Cluster]) -> List[Cluster]:
    """按业务分组后随机打散业务顺序与业务内集群顺序，再 Round-Robin 交错展开。"""
    biz_groups: Dict[int, List[Cluster]] = defaultdict(list)
    for cluster in clusters:
        biz_groups[cluster.bk_biz_id].append(cluster)

    biz_ids = list(biz_groups.keys())
    random.shuffle(biz_ids)
    for biz_id in biz_ids:
        random.shuffle(biz_groups[biz_id])

    ordered: List[Cluster] = []
    round_idx = 0
    while True:
        added_in_round = False
        for biz_id in biz_ids:
            group = biz_groups[biz_id]
            if round_idx < len(group):
                ordered.append(group[round_idx])
                added_in_round = True
        if not added_in_round:
            break
        round_idx += 1
    return ordered


def _bucket_shuffle_by_success_count(clusters: List[Cluster], recover_success_map: Dict[int, int]) -> List[Cluster]:
    """按历史演练成功次数升序分桶，同桶内随机打散，避免固定主键顺序。"""
    buckets: Dict[int, List[Cluster]] = defaultdict(list)
    for cluster in clusters:
        cnt = recover_success_map.get(cluster.id, 0)
        buckets[cnt].append(cluster)

    ordered: List[Cluster] = []
    for cnt in sorted(buckets.keys()):
        bucket = buckets[cnt]
        random.shuffle(bucket)
        ordered.extend(bucket)
    return ordered


def _cloud_cos_cache_key(bk_biz_id: int, bk_cloud_id: int) -> str:
    return f"{CLOUD_COS_CACHE_KEY_PREFIX}{bk_biz_id}:{bk_cloud_id}"


def _has_valid_cos_config(content: Any) -> bool:
    """
    判断 DBConfig cosinfo.toml 内容是否配置了有效的远程对象存储上传能力。

    判定逻辑与 BackupClientInstaller.install_one_cloud 对齐：
    storage_type 属于 cos/s3/bkrepo 且 bucket_name 非空且不含模板占位符 "{{"。
    """
    if not isinstance(content, dict):
        return False
    cos_auth = content.get("cos_auth")
    if not isinstance(cos_auth, dict):
        return False
    storage_type = str(cos_auth.get("storage_type") or "").strip().lower()
    bucket_name = str(cos_auth.get("bucket_name") or "").strip()
    return storage_type in CLOUD_COS_VALID_STORAGE_TYPES and bool(bucket_name) and "{{" not in bucket_name


def _query_cloud_cos_capability(bk_biz_id: int, bk_cloud_id: int) -> Optional[bool]:
    """查询指定 (bk_biz_id, bk_cloud_id) 是否配置了有效的 COS 备份上传能力；接口异常返回 None。"""
    if bk_biz_id <= 0:
        return False
    try:
        resp = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLOUD.value,
                "level_value": str(bk_cloud_id),
                "conf_file": ConfFile.COSINFO.value,
                "conf_type": ConfType.BACKUP_CLIENT.value,
                "namespace": "common",
                "format": FormatType.MAP_LEVEL.value,
            }
        )
    except Exception as e:
        logger.warning(
            _("查询云区域 COS 备份配置失败(bk_biz_id={}, bk_cloud_id={})，本轮保守跳过且不写缓存: {}").format(bk_biz_id, bk_cloud_id, str(e))
        )
        return None

    content = resp.get("content") if isinstance(resp, dict) else None
    return _has_valid_cos_config(content)


def _batch_check_cloud_cos_capability(biz_cloud_pairs: Set[Tuple[int, int]]) -> Dict[Tuple[int, int], bool]:
    """
    批量检查非直连云区域(bk_cloud_id != 0)是否配置有效 COS，结果缓存 24 小时。

    - 缓存命中直接返回，避免每次调度重复请求 DBConfig；
    - DBConfig 接口异常时不写缓存，本轮保守返回 False，待下轮重试。
    """
    target_pairs = [(biz_id, cloud_id) for biz_id, cloud_id in biz_cloud_pairs if cloud_id != 0]
    if not target_pairs:
        return {}

    key_to_pair = {_cloud_cos_cache_key(biz_id, cloud_id): (biz_id, cloud_id) for biz_id, cloud_id in target_pairs}
    cached_raw: Dict[str, Any] = {}
    try:
        cached_raw = cache.get_many(list(key_to_pair.keys()))
    except Exception as e:
        logger.warning(_("批量读取云区域 COS 缓存失败，降级为直接查询: {}").format(str(e)))

    result: Dict[Tuple[int, int], bool] = {}
    for key, pair in key_to_pair.items():
        if key in cached_raw and cached_raw[key] in (0, 1, True, False):
            result[pair] = bool(cached_raw[key])

    missing_pairs = [pair for pair in target_pairs if pair not in result]
    for biz_id, cloud_id in missing_pairs:
        has_cos = _query_cloud_cos_capability(biz_id, cloud_id)
        if has_cos is None:
            result[(biz_id, cloud_id)] = False
            continue
        result[(biz_id, cloud_id)] = has_cos
        try:
            cache.set(_cloud_cos_cache_key(biz_id, cloud_id), int(has_cos), timeout=CLOUD_COS_CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(_("写入云区域 COS 缓存失败(bk_biz_id={}, bk_cloud_id={}): {}").format(biz_id, cloud_id, str(e)))

    return result


def _build_no_cos_exclude_q(no_cos_pairs: Set[Tuple[int, int]]) -> Q:
    cond = Q()
    for biz_id, cloud_id in no_cos_pairs:
        cond |= Q(bk_biz_id=biz_id, bk_cloud_id=cloud_id)
    return cond


def _get_no_cos_biz_cloud_pairs(cluster_qs) -> Set[Tuple[int, int]]:
    """找出候选在线集群中 bk_cloud_id != 0 且未配置有效 COS 的 (bk_biz_id, bk_cloud_id) 集合。"""
    non_direct_pairs = set(cluster_qs.exclude(bk_cloud_id=0).values_list("bk_biz_id", "bk_cloud_id").distinct())
    if not non_direct_pairs:
        return set()
    cos_capability = _batch_check_cloud_cos_capability(non_direct_pairs)
    return {pair for pair in non_direct_pairs if not cos_capability.get(pair, False)}


def prepare_tiered_cluster_streams(
    total_hosts: int,
) -> Tuple[List[Cluster], List[Cluster], Dict[str, int], Dict[int, int]]:
    """
    准备两档集群候选流、类型软配额及历史成功次数映射。

    - 默认忽略规则：除配置表忽略外，bk_cloud_id != 0 且未配置有效 COS 的集群默认忽略
    - Tier 1：从未成功演练过的业务下的在线集群（按业务 Round-Robin 打散）
    - Tier 2：其余在线集群（按历史成功次数升序分桶，桶内打散）
    """
    ignored_biz_ids = set(ExerciseIgnoreConfig.get_ignored_biz_ids())
    ignored_cluster_ids = set(ExerciseIgnoreConfig.get_ignored_cluster_ids())
    failed_cluster_ids = set(MySQLBackupRecoverTask.get_recent_2days_failed_cluster_ids())
    running_cluster_ids = set(MySQLBackupRecoverTask.get_running_task_cluster_ids())
    today_cluster_ids = set(MySQLBackupRecoverTask.get_today_task_cluster_ids())

    base_exclude_cluster_ids = ignored_cluster_ids | failed_cluster_ids | running_cluster_ids | today_cluster_ids
    practiced_biz_ids = set(MySQLBackupRecoverTask.get_all_practiced_biz_ids())
    practiced_cluster_ids = set(MySQLBackupRecoverTask.get_all_practiced_cluster_ids())

    online_qs = _base_online_clusters_queryset()
    count_qs = online_qs.exclude(_build_exclude_q(ignored_biz_ids, ignored_cluster_ids))
    no_cos_pairs = _get_no_cos_biz_cloud_pairs(count_qs)
    if no_cos_pairs:
        no_cos_q = _build_no_cos_exclude_q(no_cos_pairs)
        count_qs = count_qs.exclude(no_cos_q)
    else:
        no_cos_q = Q()

    logger.info(
        _("调度排除统计: 忽略业务 {}, 忽略集群 {}, 无COS非直连云区域组合 {}, " "运行中集群 {}, 近2天失败集群 {}, 今日已建任务集群 {}").format(
            len(ignored_biz_ids),
            len(ignored_cluster_ids),
            len(no_cos_pairs),
            len(running_cluster_ids),
            len(failed_cluster_ids),
            len(today_cluster_ids),
        )
    )

    tendbcluster_count = count_qs.filter(cluster_type=ClusterType.TenDBCluster.value).count()
    tendbha_count = count_qs.filter(cluster_type=ClusterType.TenDBHA.value).count()
    recent_stats = MySQLBackupRecoverTask.get_recent_24h_exercise_cluster_type_stats()
    type_targets = calculate_cluster_type_targets(total_hosts, recent_stats, tendbcluster_count, tendbha_count)

    recover_success_map = _load_recover_success_map()

    # 拉取所有当前有资格参与调度的在线集群轻量字段
    eligible_qs = online_qs.exclude(_build_exclude_q(ignored_biz_ids, base_exclude_cluster_ids))
    if no_cos_pairs:
        eligible_qs = eligible_qs.exclude(no_cos_q)
    eligible_clusters = list(eligible_qs.only("id", "immute_domain", "bk_biz_id", "cluster_type", "bk_cloud_id"))

    tier1_raw: List[Cluster] = []
    tier2_raw: List[Cluster] = []
    for cluster in eligible_clusters:
        if cluster.bk_biz_id not in practiced_biz_ids and cluster.id not in practiced_cluster_ids:
            tier1_raw.append(cluster)
        else:
            tier2_raw.append(cluster)

    tier1_stream = _round_robin_by_biz(tier1_raw)
    tier2_stream = _bucket_shuffle_by_success_count(tier2_raw, recover_success_map)

    logger.info(_("候选集群流就绪: Tier1(未演练业务) {} 个集群, Tier2(兜底) {} 个集群").format(len(tier1_stream), len(tier2_stream)))
    return tier1_stream, tier2_stream, type_targets, recover_success_map


def _find_latest_usable_backup(
    cluster: Cluster,
    start_time: datetime,
    end_time: datetime,
    exercised_backup_ids: Set[str],
) -> Optional[MysqlBackupResult]:
    """查询集群在统一时间窗内最新一条未演练的有效全备记录。"""
    conditions = Q(
        cluster_id=cluster.id,
        cluster_address=cluster.immute_domain,
        backup_consistent_time__range=(start_time, end_time),
        is_full_backup=1,
    ) & ~Q(mysql_role__in=EXCLUDED_BACKUP_ROLES)

    backup_candidates = (
        MysqlBackupResult.objects.filter(conditions)
        .annotate(json_valid=Func(F("extra_fields"), function="JSON_VALID"))
        .filter(json_valid=1)
        .order_by("-backup_consistent_time")
        .iterator(chunk_size=20)
    )
    for record in backup_candidates:
        if record.backup_id not in exercised_backup_ids:
            return record
    return None


def _build_candidate_from_backup(
    cluster: Cluster,
    backup_result: MysqlBackupResult,
    tier: int,
    recover_success_cnt: int,
) -> Optional[ExerciseCandidate]:
    """解析备份记录并计算该集群演练所需的 storage_spec。"""
    backup_record = model_to_dict(backup_result)
    backup_record["backup_consistent_time"] = backup_result.backup_consistent_time.isoformat()
    backup_record["backup_begin_time"] = backup_result.backup_begin_time.isoformat()
    backup_record["backup_end_time"] = backup_result.backup_end_time.isoformat()
    backup_record["backup_source"] = MySQLBackupSource.REMOTE.value

    try:
        json.loads(backup_record["binlog_info"])
        json.loads(backup_record["file_list"])
        extra_fields = json.loads(backup_record["extra_fields"])
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(_("解析备份 JSON 字段失败(cluster={}): {}").format(cluster.immute_domain, str(e)))
        return None

    data_dir_size_mb = extra_fields.get("data_dir_size_mb", 0)
    storage_engine = extra_fields.get("storage_engine", "innodb")
    backup_type = backup_record.get("backup_type", "")
    total_filesize = backup_record.get("total_filesize", 0) or 0
    mysql_version = backup_record.get("mysql_version", "") or ""

    storage_spec = build_recovery_storage_spec(
        cluster=cluster,
        data_dir_size_mb=data_dir_size_mb,
        storage_engine=storage_engine,
        backup_type=backup_type,
        total_filesize=total_filesize,
    )
    required_disk_gb = sum(int(spec.get("min", 0) or 0) for spec in storage_spec)
    return ExerciseCandidate(
        cluster=cluster,
        tier=tier,
        recover_success_cnt=recover_success_cnt,
        backup_record=backup_record,
        parsed_extra_fields=extra_fields,
        storage_spec=storage_spec,
        mysql_version=mysql_version,
        need_mysql8=_is_mysql8_or_above(mysql_version),
        required_disk_gb=required_disk_gb,
        backup_id=backup_record["backup_id"],
        backup_file_size_gb=bytes_to_gb(total_filesize),
    )


def _hosts_need_heavy_probe(all_hosts: List[FreeHost], remaining_hosts: List[FreeHost]) -> bool:
    """判断当前剩余空闲机是否包含稀缺/大规格主机，需要额外探测大备份避免饥饿。"""
    if len(all_hosts) > 1:
        signatures = {(h.disk_count, h.total_data_disk_gb, h.max_disk_gb, h.supports_mysql8) for h in all_hosts}
        if len(signatures) > 1:
            return True
    return any(h.disk_count >= 2 or h.max_disk_gb >= LARGE_DISK_THRESHOLD_GB for h in remaining_hosts)


def _is_heavy_candidate(
    candidate: ExerciseCandidate,
    all_hosts: List[FreeHost],
    remaining_hosts: List[FreeHost],
) -> bool:
    """
    判断候选是否属于需要优先匹配大规格/稀缺主机的“高需求候选”：
    1. 在全池或剩余池中存在装不下它的机器（说明它挑机器）；或
    2. 本身属于多盘或大盘备份需求（即使池里只剩一台大机也能优先配给它）。
    """
    fit_in_rem = sum(1 for h in remaining_hosts if host_can_fit(h, candidate.storage_spec, candidate.mysql_version))
    if fit_in_rem == 0:
        return False
    if fit_in_rem < len(remaining_hosts):
        return True
    if all_hosts:
        fit_in_all = sum(1 for h in all_hosts if host_can_fit(h, candidate.storage_spec, candidate.mysql_version))
        if fit_in_all < len(all_hosts):
            return True
    return len(candidate.storage_spec) >= 2 or candidate.required_disk_gb >= LARGE_DISK_THRESHOLD_GB


def _should_stop_collecting(
    candidate_count: int,
    target_pool_size: int,
    heterogeneous: bool,
    heavy_found: int,
    desired_heavy_count: int,
    extra_probe_used: int,
    extra_probe_limit: int,
) -> bool:
    """判断当前批次候选收集是否已足够。"""
    if candidate_count < target_pool_size:
        return False
    if not heterogeneous:
        return True
    return heavy_found >= desired_heavy_count or extra_probe_used >= extra_probe_limit


def _should_skip_by_cache(
    cluster_id: int,
    no_backup_ids: Set[int],
    cached_spec_map: Dict[int, Dict[str, Any]],
    all_hosts: List[FreeHost],
    remaining_hosts: List[FreeHost],
    stats: Dict[str, int],
) -> bool:
    """检查集群是否命中无备份负缓存或规格不匹配缓存；若全池已有可匹配机则自动清除旧规格缓存。"""
    if cluster_id in no_backup_ids:
        stats["skipped_by_no_backup_cache"] += 1
        return True

    cached_req = cached_spec_map.get(cluster_id)
    if not cached_req:
        return False

    cached_spec = cached_req.get("storage_spec") or []
    cached_ver = cached_req.get("mysql_version") or ""
    if not any_host_can_fit(remaining_hosts, cached_spec, cached_ver):
        stats["skipped_by_spec_cache"] += 1
        return True

    # 当前空闲池已有可匹配的机器，清除旧缓存并放行
    if any_host_can_fit(all_hosts, cached_spec, cached_ver):
        _delete_spec_cache(cluster_id)
    return False


def _collect_fittable_candidates(
    cluster_stream: List[Cluster],
    start_index: int,
    tier: int,
    all_hosts: List[FreeHost],
    remaining_hosts: List[FreeHost],
    start_time: datetime,
    end_time: datetime,
    exercised_backup_ids: Set[str],
    recover_success_map: Dict[int, int],
    scan_budget: int,
    stats: Dict[str, int],
) -> Tuple[List[ExerciseCandidate], int, int]:
    """
    从指定 Tier 的集群流中收集一批能被当前空闲主机池装下的有效候选。

    - 先批量查 Redis 无备份负缓存与规格需求缓存：命中则 0 次 DB 查询直接跳过；
      若当前池新进大机已能装下则自动清规格缓存并放行。
    - 若当前池包含稀缺/大规格主机，在凑够基础候选池后再额外探测
      有限数量集群以吸纳 heavy 候选，兼顾防大备份饥饿与 DB 查询开销。
    """
    if not remaining_hosts or start_index >= len(cluster_stream) or scan_budget <= 0:
        return [], start_index, 0

    target_pool_size = len(remaining_hosts) * CANDIDATE_POOL_MULTIPLIER
    need_heavy_probe = _hosts_need_heavy_probe(all_hosts, remaining_hosts)
    desired_heavy_count = len(remaining_hosts) * HEAVY_PROBE_MULTIPLIER if need_heavy_probe else 0
    extra_probe_limit = min(len(remaining_hosts) * 10, EXTRA_HEAVY_PROBE_LIMIT) if need_heavy_probe else 0

    candidates: List[ExerciseCandidate] = []
    heavy_found = 0
    scanned_db_count = 0
    extra_probe_used = 0
    cursor = start_index

    while cursor < len(cluster_stream) and scanned_db_count < scan_budget:
        if _should_stop_collecting(
            len(candidates),
            target_pool_size,
            need_heavy_probe,
            heavy_found,
            desired_heavy_count,
            extra_probe_used,
            extra_probe_limit,
        ):
            break

        batch = cluster_stream[cursor : cursor + SPEC_CACHE_BATCH_SIZE]
        batch_ids = [c.id for c in batch]
        no_backup_ids = _batch_get_no_backup_cache(batch_ids)
        cached_map = _batch_get_spec_cache(batch_ids)

        for cluster in batch:
            if scanned_db_count >= scan_budget or _should_stop_collecting(
                len(candidates),
                target_pool_size,
                need_heavy_probe,
                heavy_found,
                desired_heavy_count,
                extra_probe_used,
                extra_probe_limit,
            ):
                break
            cursor += 1

            if _should_skip_by_cache(cluster.id, no_backup_ids, cached_map, all_hosts, remaining_hosts, stats):
                continue

            scanned_db_count += 1
            stats["backup_db_checked"] += 1
            if len(candidates) >= target_pool_size:
                extra_probe_used += 1

            backup_result = _find_latest_usable_backup(cluster, start_time, end_time, exercised_backup_ids)
            if not backup_result:
                stats["no_backup"] += 1
                _set_no_backup_cache(cluster.id)
                continue

            candidate = _build_candidate_from_backup(
                cluster=cluster,
                backup_result=backup_result,
                tier=tier,
                recover_success_cnt=recover_success_map.get(cluster.id, 0),
            )
            if not candidate:
                continue

            if not any_host_can_fit(all_hosts, candidate.storage_spec, candidate.mysql_version):
                stats["skipped_spec_mismatch"] += 1
                _set_spec_cache(cluster.id, candidate.storage_spec, candidate.mysql_version)
                logger.debug(
                    _("集群 {} 当前全量空闲池无匹配规格主机，跳过并缓存需求: storage_spec={}, version={}").format(
                        cluster.immute_domain, candidate.storage_spec, candidate.mysql_version
                    )
                )
                continue

            if not any_host_can_fit(remaining_hosts, candidate.storage_spec, candidate.mysql_version):
                stats["skipped_no_remaining_fit"] += 1
                continue

            candidates.append(candidate)
            if _is_heavy_candidate(candidate, all_hosts, remaining_hosts):
                heavy_found += 1

    return candidates, cursor, scanned_db_count


def _pick_best_fit_host(candidate: ExerciseCandidate, remaining_hosts: List[FreeHost]) -> Optional[FreeHost]:
    """在当前剩余空闲主机中，为候选挑选最小够用（Best-Fit）的主机。"""
    fittable = [h for h in remaining_hosts if host_can_fit(h, candidate.storage_spec, candidate.mysql_version)]
    if not fittable:
        return None
    return min(fittable, key=lambda h: h.best_fit_sort_key(candidate.need_mysql8))


def _match_phase(
    pool: List[ExerciseCandidate],
    all_hosts: List[FreeHost],
    remaining_hosts: List[FreeHost],
    type_quota: Dict[str, int],
    biz_used: Dict[int, int],
    max_per_biz: Optional[int],
    enforce_type_quota: bool,
    heavy_only: bool,
) -> List[Tuple[ExerciseCandidate, FreeHost]]:
    """
    单阶段匹配执行器。

    - heavy_only=True：仅处理“挑机器/高磁盘需求”的候选，
      按可行机数升序 → 历史成功次数升序 → 所需磁盘降序 → 流内原始序优先分配，
      既避免大备份饥饿，又避免 Tier 2 单个超大集群持续霸占大机。
    - 每次落位采用 Best-Fit（最小够用），保护大机不被小备份吃掉。
    """
    matched: List[Tuple[ExerciseCandidate, FreeHost]] = []
    if not pool or not remaining_hosts:
        return matched

    ordered_candidates: List[ExerciseCandidate] = []
    if heavy_only:
        scored: List[Tuple[Tuple[int, int, int, int], ExerciseCandidate]] = []
        for idx, candidate in enumerate(pool):
            fit_count = sum(
                1 for h in remaining_hosts if host_can_fit(h, candidate.storage_spec, candidate.mysql_version)
            )
            if fit_count == 0:
                continue
            if not _is_heavy_candidate(candidate, all_hosts, remaining_hosts):
                continue
            if enforce_type_quota and type_quota.get(candidate.cluster.cluster_type, 0) <= 0:
                continue
            if max_per_biz is not None and biz_used[candidate.cluster.bk_biz_id] >= max_per_biz:
                continue
            sort_key = (fit_count, candidate.recover_success_cnt, -candidate.required_disk_gb, idx)
            scored.append((sort_key, candidate))
        scored.sort(key=lambda item: item[0])
        ordered_candidates = [candidate for unused_key, candidate in scored]
    else:
        for candidate in pool:
            if enforce_type_quota and type_quota.get(candidate.cluster.cluster_type, 0) <= 0:
                continue
            if max_per_biz is not None and biz_used[candidate.cluster.bk_biz_id] >= max_per_biz:
                continue
            if not any_host_can_fit(remaining_hosts, candidate.storage_spec, candidate.mysql_version):
                continue
            ordered_candidates.append(candidate)

    selected_ids: Set[int] = set()
    for candidate in ordered_candidates:
        if not remaining_hosts:
            break
        if enforce_type_quota and type_quota.get(candidate.cluster.cluster_type, 0) <= 0:
            continue
        if max_per_biz is not None and biz_used[candidate.cluster.bk_biz_id] >= max_per_biz:
            continue

        host = _pick_best_fit_host(candidate, remaining_hosts)
        if host is None:
            continue

        remaining_hosts.remove(host)
        selected_ids.add(candidate.cluster.id)
        if type_quota.get(candidate.cluster.cluster_type, 0) > 0:
            type_quota[candidate.cluster.cluster_type] -= 1
        biz_used[candidate.cluster.bk_biz_id] += 1
        matched.append((candidate, host))

    # 原地移除已分配候选
    pool[:] = [c for c in pool if c.cluster.id not in selected_ids]
    return matched


def match_candidates_to_hosts(
    candidates: List[ExerciseCandidate],
    remaining_hosts: List[FreeHost],
    type_quota: Dict[str, int],
    biz_used: Dict[int, int],
    tier: int,
    all_hosts: Optional[List[FreeHost]] = None,
    strict_only: bool = False,
    relax_only: bool = False,
) -> List[Tuple[ExerciseCandidate, FreeHost]]:
    """
    同 Tier 内的分阶段匹配（支持严格阶段与兜底放宽阶段分离执行）：
    1. 严格阶段：遵守类型软配额与单业务限额，先 heavy 后常规，均采用 Best-Fit 最小够用；
    2. 放宽阶段：放开类型软配额 → 放开单业务限额（依然 heavy 优先 + Best-Fit）兜底填满。
    """
    pool = list(candidates)
    hosts_context = all_hosts if all_hosts is not None else list(remaining_hosts)
    max_per_biz = DEFAULT_MAX_CLUSTERS_PER_UNPRACTICED_BIZ if tier == 1 else None
    matched: List[Tuple[ExerciseCandidate, FreeHost]] = []

    strict_phases = [
        (True, True, max_per_biz),
        (False, True, max_per_biz),
    ]
    relax_phases = [
        (True, False, max_per_biz),
        (False, False, max_per_biz),
    ]
    if max_per_biz is not None:
        relax_phases.extend([(True, False, None), (False, False, None)])

    if strict_only:
        phases = strict_phases
    elif relax_only:
        phases = relax_phases
    else:
        phases = strict_phases + relax_phases

    for heavy_only, enforce_type, biz_limit in phases:
        if not remaining_hosts or not pool:
            break
        matched.extend(
            _match_phase(
                pool=pool,
                all_hosts=hosts_context,
                remaining_hosts=remaining_hosts,
                type_quota=type_quota,
                biz_used=biz_used,
                max_per_biz=biz_limit,
                enforce_type_quota=enforce_type,
                heavy_only=heavy_only,
            )
        )
    return matched


def plan_exercise_assignments(
    free_hosts: List[FreeHost],
    tier1_stream: List[Cluster],
    tier2_stream: List[Cluster],
    type_targets: Dict[str, int],
    start_time: datetime,
    end_time: datetime,
    exercised_backup_ids: Set[str],
    recover_success_map: Dict[int, int],
) -> Tuple[List[Tuple[ExerciseCandidate, FreeHost]], List[FreeHost], Dict[str, int]]:
    """
    按 Tier 1（未演练业务严格优先）→ Tier 2（已演练兜底）流式生成 (候选, 匹配主机) 分配计划。

    - 流式扫描期间严格遵守类型软配额与单业务限额，未入选的有效候选暂存到 deferred_pool；
    - 当本 Tier 流扫完或达到扫描预算且仍有剩余主机时，再对 deferred_pool 放宽配额/限额兜底填满；
    - 只要还有剩余空闲主机且未触达扫描预算，就持续向后补位，避免高优不匹配集群导致空调度。
    """
    remaining_hosts = list(free_hosts)
    type_quota = dict(type_targets)
    biz_used: Dict[int, int] = defaultdict(int)
    assignments: List[Tuple[ExerciseCandidate, FreeHost]] = []
    scan_budget = MAX_SCAN_CLUSTERS_PER_RUN
    stats = {
        "skipped_by_no_backup_cache": 0,
        "skipped_by_spec_cache": 0,
        "backup_db_checked": 0,
        "no_backup": 0,
        "skipped_spec_mismatch": 0,
        "skipped_no_remaining_fit": 0,
    }

    for tier, stream in ((1, tier1_stream), (2, tier2_stream)):
        cursor = 0
        deferred_pool: List[ExerciseCandidate] = []
        deferred_backup_ids: Set[str] = set()

        while remaining_hosts and cursor < len(stream) and scan_budget > 0:
            batch_candidates, cursor, scanned = _collect_fittable_candidates(
                cluster_stream=stream,
                start_index=cursor,
                tier=tier,
                all_hosts=free_hosts,
                remaining_hosts=remaining_hosts,
                start_time=start_time,
                end_time=end_time,
                exercised_backup_ids=exercised_backup_ids,
                recover_success_map=recover_success_map,
                scan_budget=scan_budget,
                stats=stats,
            )
            scan_budget -= scanned
            if not batch_candidates:
                continue

            # 同批去重同一 backup_id，防止极端情况下被重复安排
            deduped: List[ExerciseCandidate] = []
            for cand in batch_candidates:
                if cand.backup_id not in exercised_backup_ids and cand.backup_id not in deferred_backup_ids:
                    deduped.append(cand)
                    deferred_backup_ids.add(cand.backup_id)

            tier_matched = match_candidates_to_hosts(
                candidates=deduped,
                remaining_hosts=remaining_hosts,
                type_quota=type_quota,
                biz_used=biz_used,
                tier=tier,
                all_hosts=free_hosts,
                strict_only=True,
            )
            matched_cluster_ids = {cand.cluster.id for cand, unused_host in tier_matched}
            for cand, host in tier_matched:
                exercised_backup_ids.add(cand.backup_id)
                assignments.append((cand, host))

            for cand in deduped:
                if cand.cluster.id not in matched_cluster_ids:
                    deferred_pool.append(cand)

        # 本 Tier 扫描结束（或达到预算）后仍有空闲机，使用已收集的未入选候选放宽配额/单业务限额补位
        if remaining_hosts and deferred_pool:
            relaxed_candidates = [c for c in deferred_pool if c.backup_id not in exercised_backup_ids]
            relaxed_matched = match_candidates_to_hosts(
                candidates=relaxed_candidates,
                remaining_hosts=remaining_hosts,
                type_quota=type_quota,
                biz_used=biz_used,
                tier=tier,
                all_hosts=free_hosts,
                relax_only=True,
            )
            for cand, host in relaxed_matched:
                exercised_backup_ids.add(cand.backup_id)
                assignments.append((cand, host))

    return assignments, remaining_hosts, stats


def build_targeted_resource_apply_params(
    task_id: str,
    host: FreeHost,
    storage_spec: List[Dict[str, Any]],
    mysql_version: str,
) -> Dict[str, Any]:
    """构造定向主机申请参数，将批内 Best-Fit 匹配结果精准下发给资源池。"""
    details: Dict[str, Any] = {
        "count": 1,
        "group_mark": "backup_recovery_exercise_0",
        "bk_cloud_id": host.bk_cloud_id,
        "hosts": [{"bk_host_id": host.bk_host_id, "ip": host.ip}],
        "labels": [MYSQL_BACKUPRECOVER_MCH_LABELS_ID],
        "os_type": "Linux",
        "storage_spec": storage_spec,
    }
    if _is_mysql8_or_above(mysql_version):
        details["os_names"] = list(MYSQL8_EXCLUDED_OS_NAMES)
        details["exclude_os_name"] = True

    return {
        "for_biz_id": MYSQL_BACKUPRECOVER_BIZ_ID,
        "resource_type": "mysql",
        "task_id": task_id,
        "operator": "system",
        "details": [details],
    }


def _apply_host_with_fallback(
    root_id: str,
    candidate: ExerciseCandidate,
    primary_host: FreeHost,
    backup_hosts: List[FreeHost],
) -> Optional[Dict[str, Any]]:
    """
    定向申请匹配主机；若遇并发抢占返回 RESOURCE_LAKE，从剩余未分配空闲主机中重试一次 Best-Fit。
    """
    hosts_to_try: List[FreeHost] = [primary_host]
    for attempt_idx in range(2):
        target_host = hosts_to_try[attempt_idx]
        apply_params = build_targeted_resource_apply_params(
            task_id=root_id,
            host=target_host,
            storage_spec=candidate.storage_spec,
            mysql_version=candidate.mysql_version,
        )
        try:
            resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
        except Exception as e:
            logger.exception(
                _("调用资源池申请接口异常: 集群={}, 主机={}({}), 错误={}").format(
                    candidate.cluster.immute_domain, target_host.ip, target_host.bk_host_id, str(e)
                )
            )
            return None

        if not isinstance(resp, dict):
            logger.error(_("资源池申请返回格式异常: {}").format(resp))
            return None

        code = resp.get("code")
        if code == 0:
            return resp

        if code == ResourceApplyErrCode.RESOURCE_LAKE:
            logger.warning(
                _("定向申请资源失败(可能被并发占用): 集群={}, 主机={}({}), 备份ID={}, " "storage_spec={}, 错误={}").format(
                    candidate.cluster.immute_domain,
                    target_host.ip,
                    target_host.bk_host_id,
                    candidate.backup_id,
                    candidate.storage_spec,
                    resp.get("message"),
                )
            )
            if attempt_idx == 0:
                fallback_host = _pick_best_fit_host(candidate, backup_hosts)
                if fallback_host is not None:
                    backup_hosts.remove(fallback_host)
                    hosts_to_try.append(fallback_host)
                    continue
            return None

        if code in ResourceApplyErrCode.get_values():
            logger.error(
                _("资源池服务出现系统错误，请联系管理员或稍后重试。错误信息: [{}]{}").format(
                    ResourceApplyErrCode.get_choice_label(code), resp.get("message")
                )
            )
            return None

        logger.error(_("资源池相关服务出现未知异常，请联系管理员处理。错误信息: [{}]{}").format(code, resp.get("message")))
        return None
    return None


def _submit_exercise_task(
    candidate: ExerciseCandidate,
    matched_host: FreeHost,
    backup_hosts: List[FreeHost],
) -> bool:
    """申请资源、落库 MySQLBackupRecoverTask 并启动演练 Flow；任一步异常均尝试归还已申请主机。"""
    cluster = candidate.cluster
    backup_record = candidate.backup_record
    extra_fields = candidate.parsed_extra_fields
    root_id = generate_root_id()

    resp = _apply_host_with_fallback(root_id, candidate, matched_host, backup_hosts)
    if not resp:
        return False

    mch_info: Optional[Dict[str, Any]] = None
    task: Optional[MySQLBackupRecoverTask] = None
    try:
        resource_request_id, apply_data = resp["request_id"], resp["data"]
        logger.debug(_("演练资源申请结果: request_id={}, apply_data={}").format(resource_request_id, apply_data))
        mch_info = apply_data[0]["data"][0]

        task = MySQLBackupRecoverTask(
            bk_biz_id=backup_record["bk_biz_id"],
            cluster_id=cluster.id,
            cluster_domain=backup_record.get("cluster_address", ""),
            cluster_type=cluster.cluster_type,
            charset=extra_fields.get("backup_charset", ""),
            mysql_version=candidate.mysql_version,
            sql_mode=extra_fields.get("sql_mode", ""),
            backup_id=candidate.backup_id,
            backup_begin_time=backup_record["backup_begin_time"],
            backup_end_time=backup_record["backup_end_time"],
            backup_total_size=int(candidate.backup_file_size_gb),
            backup_host=backup_record.get("backup_host", ""),
            backup_host_role=backup_record.get("mysql_role", ""),
            backup_type=backup_record.get("backup_type", ""),
            backup_tool=extra_fields.get("backup_tool", ""),
            time_zone=extra_fields.get("time_zone", ""),
            task_id=root_id,
            task_status=TaskStatus.RESOURCE_APPLIED,
            phase=TaskPhase.RUNNING,
            creator="system",
            updater="system",
        )
        task.save()

        rollback_host = {
            "ip": mch_info["ip"],
            "bk_host_id": mch_info["bk_host_id"],
            "bk_cloud_id": mch_info["bk_cloud_id"],
            "bk_biz_id": mch_info["bk_biz_id"],
        }
        flow_context = {
            "uid": root_id,
            "ticket_type": TicketType.MYSQL_ROLLBACK_EXERCISE,
            "exercise_cluster_id": cluster.id,
            "backup_id": candidate.backup_id,
            "rollback_host": rollback_host,
            "bk_biz_id": MYSQL_BACKUPRECOVER_BIZ_ID,
            "backup_record": backup_info_format(dict(backup_record)),
            "created_by": "system",
            "labels": mch_info["labels"],
            "rollback_type": RollbackType.REMOTE_AND_BACKUPID,
        }
        task.exercise_host_ip = mch_info["ip"]
        task.task_status = TaskStatus.COMMIT_SUCCESS
        task.save()
        flow = MySQLRollbackExerciseFlow(root_id=root_id, data=flow_context)
        flow.run()
        return True
    except Exception as e:
        logger.exception(_("回档演练流程运行失败: {}").format(e))
        resource_return_info = _try_return_applied_host(mch_info)
        if task is not None and task.pk:
            try:
                task.task_status = TaskStatus.COMMIT_FAILED
                task.task_info = _("演练流程失败: {}; {}").format(str(e), resource_return_info)
                task.phase = TaskPhase.DONE
                task.save()
            except Exception as save_e:
                logger.error(_("更新失败演练任务状态异常(task_id={}): {}").format(root_id, str(save_e)))
        return False


def _try_return_applied_host(mch_info: Optional[Dict[str, Any]]) -> str:
    """Flow 启动异常时尝试归还已申请的演练机器。"""
    if not mch_info:
        return _("未解析到已申请主机信息，跳过自动归还")
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
        logger.info(_("演练失败，已成功归还资源: {}").format(mch_info["ip"]))
        return _("资源归还成功: IP {}").format(mch_info["ip"])
    except Exception as return_e:
        logger.error(_("归还资源失败: {}").format(str(return_e)))
        return _("资源归还失败: {}").format(str(return_e))


def gen_rollback_task_v2() -> None:
    """
    新版 MySQL 备份恢复演练调度入口（基于空闲主机规格匹配）。

    核心策略：
    1. 拉取空闲 Linux 主机完整画像，按空闲资源驱动调度，避免空调度；
    2. 统一 now-7d ~ now-1d 备份时间窗与近 90 天已演练集合，单阶段查备份；
    3. 未演练业务（Tier 1）严格优先于已演练业务（Tier 2）；
    4. 同 Tier 内大规格/挑剔备份优先配大机，同时使用 Best-Fit 最小够用防小备份吃掉大机；
    5. 装不下的集群跳过并写入 2 小时轻量需求缓存（新进大机自动放行），继续向后补位。
    """
    total_start = time.time()
    free_hosts = fetch_free_hosts()
    if not free_hosts:
        logger.info(_("没有可用的演练主机资源，跳过回档任务生成"))
        return

    exercised_backup_ids = load_exercised_backup_ids()
    start_time, end_time = get_backup_query_range()
    logger.info(
        _("演练调度v2开始: 空闲主机 {} 台, 已演练备份ID {} 个, 备份窗口 {} 至 {}").format(
            len(free_hosts), len(exercised_backup_ids), start_time, end_time
        )
    )

    tier1_stream, tier2_stream, type_targets, recover_success_map = prepare_tiered_cluster_streams(len(free_hosts))
    assignments, unassigned_hosts, stats = plan_exercise_assignments(
        free_hosts=free_hosts,
        tier1_stream=tier1_stream,
        tier2_stream=tier2_stream,
        type_targets=type_targets,
        start_time=start_time,
        end_time=end_time,
        exercised_backup_ids=exercised_backup_ids,
        recover_success_map=recover_success_map,
    )

    logger.info(
        _("演练匹配计划完成: 配对 {}/{} 台, 无备份缓存跳过 {}, 规格缓存跳过 {}, " "查库 {}, 无备份 {}, 全池规格不匹配跳过 {}, 剩余池规格不足跳过 {}").format(
            len(assignments),
            len(free_hosts),
            stats["skipped_by_no_backup_cache"],
            stats["skipped_by_spec_cache"],
            stats["backup_db_checked"],
            stats["no_backup"],
            stats["skipped_spec_mismatch"],
            stats["skipped_no_remaining_fit"],
        )
    )

    submitted_count = 0
    for candidate, matched_host in assignments:
        logger.info(
            _("提交演练任务: 集群={} (Tier={}, 类型={}, 需求磁盘={}GB) -> 主机={} (总数据盘={}GB, 盘数={})").format(
                candidate.cluster.immute_domain,
                candidate.tier,
                candidate.cluster.cluster_type,
                candidate.required_disk_gb,
                matched_host.ip,
                matched_host.total_data_disk_gb,
                matched_host.disk_count,
            )
        )
        try:
            if _submit_exercise_task(candidate, matched_host, unassigned_hosts):
                submitted_count += 1
        except Exception as e:
            logger.exception(
                _("提交演练任务发生未预期异常(cluster={}, host={}): {}").format(
                    candidate.cluster.immute_domain, matched_host.ip, str(e)
                )
            )

    logger.info(
        _("演练调度v2完成: 成功提交 {}/{} 个任务, 耗时 {:.2f}秒").format(submitted_count, len(assignments), time.time() - total_start)
    )
