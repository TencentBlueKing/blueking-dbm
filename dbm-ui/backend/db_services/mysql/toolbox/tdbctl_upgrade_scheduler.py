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
import logging
import time
import uuid
from typing import Dict, List, Optional

from celery import shared_task
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_report.enums import TdbctlUpgradeStatus
from backend.db_report.models import TdbctlUpgradeRecord
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.spider.upgrade.upgrade_tdbctl import UpgradeTdbctlFlow
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

# ----------------------------- Redis 锁相关常量 ----------------------------------------
# 全局锁键名（当 bk_biz_ids 为空时，表示升级所有业务）
TDBCTL_UPGRADE_GLOBAL_LOCK_KEY = "tdbctl_upgrade:global"
# 业务粒度锁键名前缀
TDBCTL_UPGRADE_BIZ_LOCK_KEY_PREFIX = "tdbctl_upgrade:biz:"
# 锁过期时间，默认 1 小时
TDBCTL_UPGRADE_LOCK_TIMEOUT = 3600


# ----------------------------- Redis 锁辅助函数 ----------------------------------------


def _is_global_lock_held() -> bool:
    """
    检查全局锁是否被持有

    @return: True 表示全局锁被持有，False 表示未被持有
    """
    return RedisConn.exists(TDBCTL_UPGRADE_GLOBAL_LOCK_KEY)


def _check_any_biz_lock_exists() -> List[int]:
    """
    检查是否存在任何业务粒度锁

    @return: 被锁定的业务ID列表
    """
    locked_biz_ids = []
    # 使用 SCAN 命令扫描所有业务锁
    pattern = f"{TDBCTL_UPGRADE_BIZ_LOCK_KEY_PREFIX}*"
    cursor = 0
    while True:
        cursor, keys = RedisConn.scan(cursor=cursor, match=pattern, count=100)
        for key in keys:
            # 从 key 中提取业务ID
            try:
                biz_id = int(key.replace(TDBCTL_UPGRADE_BIZ_LOCK_KEY_PREFIX, ""))
                locked_biz_ids.append(biz_id)
            except (ValueError, TypeError):
                continue
        if cursor == 0:
            break
    return locked_biz_ids


def _acquire_global_lock(operator: str, timeout: int = TDBCTL_UPGRADE_LOCK_TIMEOUT) -> bool:
    """
    获取全局锁

    @param operator: 操作人
    @param timeout: 锁过期时间（秒）
    @return: True 表示获取成功，False 表示获取失败
    """
    # 先检查是否存在业务粒度锁
    locked_biz_ids = _check_any_biz_lock_exists()
    if locked_biz_ids:
        logger.warning(_("获取全局锁失败: 存在业务粒度锁, 被锁定的业务ID={}").format(locked_biz_ids))
        return False

    # 尝试获取全局锁
    lock_value = f"{operator}:{time.time()}"
    acquired = RedisConn.set(TDBCTL_UPGRADE_GLOBAL_LOCK_KEY, lock_value, nx=True, ex=timeout)
    if acquired:
        logger.info(_("获取全局锁成功: operator={}, timeout={}s").format(operator, timeout))
        return True
    else:
        logger.warning(_("获取全局锁失败: 锁已被其他任务持有"))
        return False


def _release_global_lock():
    """
    释放全局锁
    """
    RedisConn.delete(TDBCTL_UPGRADE_GLOBAL_LOCK_KEY)
    logger.info(_("释放全局锁成功"))


def _acquire_biz_locks(bk_biz_ids: List[int], operator: str, timeout: int = TDBCTL_UPGRADE_LOCK_TIMEOUT) -> List[int]:
    """
    获取业务粒度锁

    @param bk_biz_ids: 业务ID列表
    @param operator: 操作人
    @param timeout: 锁过期时间（秒）
    @return: 成功获取锁的业务ID列表
    """
    # 先检查全局锁是否存在
    if _is_global_lock_held():
        logger.warning(_("获取业务锁失败: 全局锁被持有，无法获取业务粒度锁"))
        return []

    acquired_biz_ids = []
    for bk_biz_id in bk_biz_ids:
        lock_key = f"{TDBCTL_UPGRADE_BIZ_LOCK_KEY_PREFIX}{bk_biz_id}"
        lock_value = f"{operator}:{time.time()}"
        acquired = RedisConn.set(lock_key, lock_value, nx=True, ex=timeout)
        if acquired:
            acquired_biz_ids.append(bk_biz_id)
            logger.info(_("获取业务锁成功: bk_biz_id={}, timeout={}s").format(bk_biz_id, timeout))
        else:
            logger.warning(_("获取业务锁失败: bk_biz_id={}, 锁已被其他任务持有").format(bk_biz_id))

    return acquired_biz_ids


def _release_biz_locks(bk_biz_ids: List[int]):
    """
    释放业务粒度锁

    @param bk_biz_ids: 业务ID列表
    """
    for bk_biz_id in bk_biz_ids:
        lock_key = f"{TDBCTL_UPGRADE_BIZ_LOCK_KEY_PREFIX}{bk_biz_id}"
        RedisConn.delete(lock_key)
        logger.info(_("释放业务锁成功: bk_biz_id={}").format(bk_biz_id))


class TdbctlUpgradeScheduler:
    """
    TdbCtl 全局升级调度器

    用于调度平台所有 TenDBCluster 集群的 tdbctl 中控升级。
    支持分批次执行，每批处理固定数量的集群，避免一次性升级所有集群带来的风险。

    使用方式：
        scheduler = TdbctlUpgradeScheduler(
            bk_biz_ids=[1, 2],  # 指定业务，为空则升级全部
            batch_size=20,      # 每批集群数
            pkg_id=123,         # tdbctl 升级包ID
        )
        result = scheduler.schedule_batch()
    """

    def __init__(
        self,
        pkg_id: int,
        bk_biz_ids: Optional[List[int]] = None,
        batch_size: int = 20,
        operator: str = "system",
    ):
        """
        初始化调度器

        @param pkg_id: tdbctl 升级包ID（必填）
        @param bk_biz_ids: 业务ID列表，为空则升级全部业务
        @param batch_size: 每批集群数量，默认20
        @param operator: 操作人
        """
        self.pkg_id = pkg_id
        self.bk_biz_ids = bk_biz_ids
        self.batch_size = batch_size
        self.operator = operator
        self.batch_id = str(uuid.uuid4())[:8]  # 生成批次ID

        # 验证升级包
        self._validate_package()

    def _validate_package(self):
        """验证升级包是否存在"""
        try:
            self.pkg = Package.objects.get(id=self.pkg_id, pkg_type=MediumEnum.tdbCtl)
            self.target_version = self.pkg.name
            logger.info(_("目标升级版本: {}").format(self.target_version))
        except Package.DoesNotExist:
            raise ValueError(_("升级包 {} 不存在").format(self.pkg_id))

    def get_all_tendbcluster_clusters(self) -> List[Cluster]:
        """获取所有 TenDBCluster 集群"""
        queryset = Cluster.objects.filter(cluster_type=ClusterType.TenDBCluster)

        if self.bk_biz_ids:
            queryset = queryset.filter(bk_biz_id__in=self.bk_biz_ids)

        return list(queryset)

    def get_pending_clusters(self) -> List[Cluster]:
        """
        获取待升级的集群列表

        过滤规则：
        1. 排除状态为 SUCCESS 且 target_version 等于当前目标版本的集群
        2. 排除状态为 RUNNING 的集群
        3. 排除状态为 SKIPPED 且 target_version 等于当前目标版本的集群

        @return: 待升级的集群列表
        """
        all_clusters = self.get_all_tendbcluster_clusters()
        if not all_clusters:
            logger.info(_("没有找到 TenDBCluster 集群"))
            return []

        cluster_ids = [c.id for c in all_clusters]

        # 查询已经成功升级到目标版本的集群ID
        success_cluster_ids = set(
            TdbctlUpgradeRecord.objects.filter(
                cluster_id__in=cluster_ids,
                target_version=self.target_version,
                status=TdbctlUpgradeStatus.SUCCESS.value,
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

        # 查询正在升级中的集群ID
        running_cluster_ids = set(
            TdbctlUpgradeRecord.objects.filter(
                cluster_id__in=cluster_ids,
                status=TdbctlUpgradeStatus.RUNNING.value,
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

        # 查询已跳过（版本已最新）且目标版本匹配的集群ID
        skipped_cluster_ids = set(
            TdbctlUpgradeRecord.objects.filter(
                cluster_id__in=cluster_ids,
                target_version=self.target_version,
                status=TdbctlUpgradeStatus.SKIPPED.value,
            )
            .values_list("cluster_id", flat=True)
            .distinct()
        )

        # 排除已成功、正在升级和已跳过的集群
        exclude_ids = success_cluster_ids | running_cluster_ids | skipped_cluster_ids

        pending_clusters = [c for c in all_clusters if c.id not in exclude_ids]

        logger.info(
            _("集群统计: 总数={}, 已成功={}, 升级中={}, 已跳过={}, 待升级={}").format(
                len(all_clusters),
                len(success_cluster_ids),
                len(running_cluster_ids),
                len(skipped_cluster_ids),
                len(pending_clusters),
            )
        )

        return pending_clusters

    def schedule_batch(self, schedule_interval_seconds: int = 180) -> Dict:
        """
        调度一批集群升级，按业务串行执行 flow

        @param schedule_interval_seconds: 每个业务之间的调度间隔（秒），默认 180 秒（3 分钟）
        @return: 调度结果，包含成功和失败的集群信息
        """
        pending_clusters = self.get_pending_clusters()

        if not pending_clusters:
            return {
                "result": True,
                "message": _("没有待升级的集群"),
                "batch_id": self.batch_id,
                "scheduled_count": 0,
                "pending_count": 0,
                "flows": [],
            }

        # 取前 batch_size 个集群
        batch_clusters = pending_clusters[: self.batch_size]

        logger.info(
            _("开始调度升级，批次ID: {}, 待升级集群数: {}, 本批次集群数: {}").format(
                self.batch_id, len(pending_clusters), len(batch_clusters)
            )
        )

        # 按业务分组执行 flow
        flows = []
        errors = []

        # 按业务分组
        biz_clusters: Dict[int, List[Cluster]] = {}
        for cluster in batch_clusters:
            if cluster.bk_biz_id not in biz_clusters:
                biz_clusters[cluster.bk_biz_id] = []
            biz_clusters[cluster.bk_biz_id].append(cluster)

        # 按业务串行执行升级流程
        biz_list = list(biz_clusters.items())
        for idx, (bk_biz_id, clusters) in enumerate(biz_list):
            try:
                root_id = self._execute_upgrade_flow(bk_biz_id, clusters)
                flows.append(
                    {
                        "root_id": root_id,
                        "bk_biz_id": bk_biz_id,
                        "cluster_count": len(clusters),
                        "cluster_ids": [c.id for c in clusters],
                    }
                )
                logger.info(_("执行升级流程成功: 业务={}, root_id={}, 集群数={}").format(bk_biz_id, root_id, len(clusters)))
            except Exception as e:
                error_msg = _("执行升级流程失败: 业务={}, 错误={}").format(bk_biz_id, str(e))
                logger.error(error_msg)
                errors.append(
                    {
                        "bk_biz_id": bk_biz_id,
                        "cluster_ids": [c.id for c in clusters],
                        "error": str(e),
                    }
                )

            # 如果不是最后一个业务，等待指定时间后再执行下一个
            if idx < len(biz_list) - 1:
                logger.info(_("等待 {} 秒后执行下一个业务的升级流程").format(schedule_interval_seconds))
                time.sleep(schedule_interval_seconds)

        return {
            "result": len(errors) == 0,
            "message": _("调度完成") if not errors else _("部分调度失败"),
            "batch_id": self.batch_id,
            "target_version": self.target_version,
            "scheduled_count": len(batch_clusters),
            "pending_count": len(pending_clusters) - len(batch_clusters),
            "flows": flows,
            "errors": errors,
        }

    def _execute_upgrade_flow(self, bk_biz_id: int, clusters: List[Cluster]) -> str:
        """
        直接执行 tdbctl 升级 flow

        @param bk_biz_id: 业务ID
        @param clusters: 集群列表
        @return: flow 的 root_id
        """
        # 生成 root_id
        root_id = generate_root_id()
        # 构建 flow 数据
        infos = []
        for cluster in clusters:
            infos.append(
                {
                    "cluster_id": cluster.id,
                    "pkg_id": self.pkg_id,
                }
            )

        flow_data = {
            "bk_biz_id": bk_biz_id,
            "bk_cloud_id": clusters[0].bk_cloud_id if clusters else 0,
            "uid": "",
            "created_by": self.operator,
            "ticket_type": TicketType.TENDBCLUSTER_TDBCTL_UPGRADE.value,
            "infos": infos,
            "batch_id": self.batch_id,
        }

        # 直接执行 flow
        flow = UpgradeTdbctlFlow(root_id=root_id, data=flow_data)
        flow.run()

        logger.info(_("tdbctl 升级流程已启动: root_id={}, 集群数={}").format(root_id, len(clusters)))

        return root_id

    def get_upgrade_progress(self) -> Dict:
        """
        获取升级进度统计

        @return: 进度统计信息
        """
        all_clusters = self.get_all_tendbcluster_clusters()
        cluster_ids = [c.id for c in all_clusters]

        if not cluster_ids:
            return {
                "total_clusters": 0,
                "pending": 0,
                "running": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "target_version": self.target_version,
            }

        # 按状态统计
        status_counts = {}
        for status in TdbctlUpgradeStatus.get_values():
            queryset = TdbctlUpgradeRecord.objects.filter(
                cluster_id__in=cluster_ids,
                status=status,
            )
            # 如果是成功或跳过状态，需要匹配目标版本
            if status in [TdbctlUpgradeStatus.SUCCESS.value, TdbctlUpgradeStatus.SKIPPED.value]:
                queryset = queryset.filter(target_version=self.target_version)
            status_counts[status] = queryset.values("cluster_id").distinct().count()

        # 计算待升级数（没有记录或者失败的）
        recorded_cluster_ids = set(
            TdbctlUpgradeRecord.objects.filter(cluster_id__in=cluster_ids)
            .values_list("cluster_id", flat=True)
            .distinct()
        )
        no_record_count = len(set(cluster_ids) - recorded_cluster_ids)

        return {
            "total_clusters": len(cluster_ids),
            "pending": no_record_count + status_counts.get(TdbctlUpgradeStatus.PENDING.value, 0),
            "running": status_counts.get(TdbctlUpgradeStatus.RUNNING.value, 0),
            "success": status_counts.get(TdbctlUpgradeStatus.SUCCESS.value, 0),
            "failed": status_counts.get(TdbctlUpgradeStatus.FAILED.value, 0),
            "skipped": status_counts.get(TdbctlUpgradeStatus.SKIPPED.value, 0),
            "target_version": self.target_version,
            "bk_biz_ids": self.bk_biz_ids,
        }

    def get_upgrade_records(
        self,
        status: Optional[str] = None,
        cluster_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """
        获取升级记录列表

        @param status: 状态过滤
        @param cluster_id: 集群ID过滤
        @param limit: 返回记录数
        @param offset: 偏移量
        @return: 记录列表和分页信息
        """
        queryset = TdbctlUpgradeRecord.objects.all()

        if self.bk_biz_ids:
            queryset = queryset.filter(bk_biz_id__in=self.bk_biz_ids)

        if status:
            queryset = queryset.filter(status=status)

        if cluster_id:
            queryset = queryset.filter(cluster_id=cluster_id)

        total = queryset.count()
        records = queryset.order_by("-update_at")[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": [
                {
                    "id": r.id,
                    "bk_biz_id": r.bk_biz_id,
                    "cluster_id": r.cluster_id,
                    "cluster_domain": r.cluster_domain,
                    "ip": r.ip,
                    "port": r.port,
                    "instance_role": r.instance_role,
                    "current_version": r.current_version,
                    "target_version": r.target_version,
                    "upgraded_version": r.upgraded_version,
                    "status": r.status,
                    "task_id": r.task_id,
                    "batch_id": r.batch_id,
                    "error_msg": r.error_msg,
                    "upgrade_count": r.upgrade_count,
                    "upgrade_history": r.upgrade_history,
                    "create_at": r.create_at.isoformat() if r.create_at else None,
                    "update_at": r.update_at.isoformat() if r.update_at else None,
                }
                for r in records
            ],
        }


# ----------------------------- 异步任务 ----------------------------------------


@shared_task
def tdbctl_upgrade_task(
    pkg_id: int,
    bk_biz_ids: Optional[List[int]],
    batch_size: int,
    operator: str,
    schedule_interval_seconds: int = 180,
    lock_timeout: int = TDBCTL_UPGRADE_LOCK_TIMEOUT,
) -> Dict:
    """
    异步执行 tdbctl 升级调度任务（按业务串行调度）

    使用 Redis 分布式锁避免重复调度：
    - 如果 bk_biz_ids 为空（升级所有业务），使用全局锁
    - 如果 bk_biz_ids 不为空，使用业务粒度锁

    @param pkg_id: tdbctl 升级包ID
    @param bk_biz_ids: 业务ID列表，为空则升级全部业务
    @param batch_size: 每批集群数量
    @param operator: 操作人
    @param schedule_interval_seconds: 每个业务之间的调度间隔（秒），默认 180 秒
    @param lock_timeout: 锁过期时间（秒），默认 3600 秒（1 小时）
    @return: 调度结果
    """
    logger.info(
        _("异步任务开始: tdbctl 升级调度, pkg_id={}, bk_biz_ids={}, batch_size={}, operator={}, interval={}s").format(
            pkg_id, bk_biz_ids, batch_size, operator, schedule_interval_seconds
        )
    )

    # 判断是否为全局调度（升级所有业务）
    is_global_schedule = not bk_biz_ids

    # 用于记录获取的锁，以便在 finally 中释放
    acquired_global_lock = False
    acquired_biz_ids: List[int] = []

    try:
        if is_global_schedule:
            # 全局调度：需要获取全局锁
            acquired_global_lock = _acquire_global_lock(operator, lock_timeout)
            if not acquired_global_lock:
                # 锁检查已在 views 层前置，这里只记录日志作为兜底
                logger.warning(_("异步任务获取全局锁失败，可能存在其他调度任务正在执行"))
                return {"result": False, "message": "lock_acquire_failed", "lock_type": "global"}
        else:
            # 业务粒度调度：检查全局锁并获取业务锁
            if _is_global_lock_held():
                # 锁检查已在 views 层前置，这里只记录日志作为兜底
                logger.warning(_("异步任务检测到全局锁被持有，无法执行业务粒度调度"))
                return {"result": False, "message": "global_lock_held", "lock_type": "biz"}

            # 尝试获取业务锁
            acquired_biz_ids = _acquire_biz_locks(bk_biz_ids, operator, lock_timeout)
            if not acquired_biz_ids:
                # 锁检查已在 views 层前置，这里只记录日志作为兜底
                logger.warning(_("异步任务获取业务锁失败，所有指定业务都已被其他任务锁定: {}").format(bk_biz_ids))
                return {"result": False, "message": "biz_lock_acquire_failed", "lock_type": "biz"}

            # 如果只获取到部分业务锁，记录日志
            if len(acquired_biz_ids) < len(bk_biz_ids):
                skipped_biz_ids = [biz_id for biz_id in bk_biz_ids if biz_id not in acquired_biz_ids]
                logger.warning(_("部分业务锁获取失败，跳过这些业务: {}").format(skipped_biz_ids))

            # 只调度获取到锁的业务
            bk_biz_ids = acquired_biz_ids

        # 执行调度
        scheduler = TdbctlUpgradeScheduler(
            pkg_id=pkg_id,
            bk_biz_ids=bk_biz_ids,
            batch_size=batch_size,
            operator=operator,
        )
        result = scheduler.schedule_batch(schedule_interval_seconds=schedule_interval_seconds)
        logger.info(_("异步任务完成: tdbctl 升级调度, batch_id={}, 结果={}").format(scheduler.batch_id, result.get("result")))

        # 添加锁信息到结果中
        if is_global_schedule:
            result["lock_type"] = "global"
        else:
            result["lock_type"] = "biz"
            result["locked_biz_ids"] = acquired_biz_ids

        return result

    except Exception as e:
        logger.exception(_("异步任务异常: tdbctl 升级调度, 错误={}").format(str(e)))
        return {
            "result": False,
            "message": _("调度异常: {}").format(str(e)),
        }
    finally:
        # 释放锁
        logger.info(_("开始释放锁, 全局锁={}, 业务锁={}").format(acquired_global_lock, acquired_biz_ids))
        if acquired_global_lock:
            _release_global_lock()
            logger.info(_("全局锁释放完成"))
        if acquired_biz_ids:
            _release_biz_locks(acquired_biz_ids)
            logger.info(_("业务锁释放完成, 业务ID列表={}").format(acquired_biz_ids))
