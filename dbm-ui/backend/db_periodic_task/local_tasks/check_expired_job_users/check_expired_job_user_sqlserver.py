# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 临时（Job）账号巡检 —— 业务实现 + Celery worker 薄壳 + 定制分发器实例。

设计要点 / 怎么做：
  - 核心业务逻辑保持不变（逐 cluster 一次 sqlserver_rpc，判断 loginname 前缀 + Flow 状态）；
  - 通用调度骨架（分片 / 错峰 / 双层锁 / 投递）复用 dispatcher.ExpiredJobUserDispatcher；
  - 单节点与 HA 集群共用同一个 dispatcher，通过 cluster_types 一次覆盖，减少 beat 触发点。
"""
import logging
from typing import Iterable, List, Optional

from blueapps.core.celery.celery import app

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.check_expired_job_users.dispatcher import (
    ExpiredJobUserDispatcher,
    run_batch_with_lock,
)
from backend.db_periodic_task.utils import TimeUnit
from backend.flow.consts import DBM_JOB_TMP_USER_REGULAR, DBM_MYSQL_JOB_TMP_USER_PREFIX, StateType
from backend.flow.models import FlowTree

logger = logging.getLogger("root")

# ------------------------------ 常量 / 配置 ------------------------------

# SQLServer 巡检允许的集群类型白名单
_ALLOWED_SQLSERVER_CLUSTER_TYPES: frozenset = frozenset({ClusterType.SqlserverHA, ClusterType.SqlserverSingle})

# SQLServer 巡检默认覆盖的集群类型（dispatcher 默认值）
_DEFAULT_SQLSERVER_CLUSTER_TYPES: List[ClusterType] = [
    ClusterType.SqlserverSingle,
    ClusterType.SqlserverHA,
]

# 判定为"已过期"的 Flow 状态集合：终止 / 已完成
_EXPIRED_FLOW_STATUSES: List[str] = [StateType.REVOKED, StateType.FINISHED]

# Celery worker 任务名，仅用于日志展示
_SQLSERVER_BATCH_TASK_NAME: str = "check_expired_job_users_for_sqlserver"


# ------------------------------ 业务巡检器 ------------------------------


class CheckExpiredJobUserForSqlserver(object):
    """SQLServer 集群 Job 临时账号过期巡检器（单批工作单元）。

    职责：
      - 对传入的一批集群，抓取其上以 DBM job 前缀命名的 login；
      - 反查 loginname 后缀对应的 flow_root_id，若 Flow 已 TERMINATED / REVOKED / SUCCEEDED，则 drop login。

    使用方式：
      CheckExpiredJobUserForSqlserver(cluster_ids=[1, 2]).do_check()
      # 兼容旧调用
      CheckExpiredJobUserForSqlserver(sqlserver_cluster_type=ClusterType.SqlserverHA).do_check()

    边界：
      - cluster_ids 为空 -> do_check 直接返回；
      - DRS RPC 失败    -> 记录 error 日志，不抛异常，等下一周期重试；
      - drop login 失败 -> 不捕捉，等待下一周期处理（保持原语义）。
    """

    def __init__(
        self,
        cluster_ids: Optional[Iterable[int]] = None,
        sqlserver_cluster_type: Optional[ClusterType] = None,
    ) -> None:
        """初始化巡检器。

        入参二选一：
          - 优先使用 cluster_ids（分片后的一批集群 id）；
          - 若未传 cluster_ids，则退化为按 sqlserver_cluster_type 全量拉取（兼容旧调用）。

        :param cluster_ids: 待巡检的集群 id 列表；由上游 dispatcher 分片后传入
        :param sqlserver_cluster_type: 集群类型；仅在 cluster_ids 未传时生效

        边界：
          - sqlserver_cluster_type 不在 SQLServer 白名单 -> 抛 Exception；
          - 两者均未传 -> 视为空批。
        """
        base_qs = Cluster.objects.filter(cluster_type__in=_ALLOWED_SQLSERVER_CLUSTER_TYPES)

        if cluster_ids is not None:
            self.clusters = base_qs.filter(id__in=list(cluster_ids))
            return

        if sqlserver_cluster_type is not None:
            if sqlserver_cluster_type not in _ALLOWED_SQLSERVER_CLUSTER_TYPES:
                raise Exception(
                    f"the cluster_type does not belong to the sqlserver cluster type range: "
                    f"cluster_type:[{sqlserver_cluster_type}]"
                )
            self.clusters = Cluster.objects.filter(cluster_type=sqlserver_cluster_type)
            return

        # 空批
        self.clusters = base_qs.none()

    @staticmethod
    def _get_storage_instance_for_cluster(cluster: Cluster) -> List[str]:
        """获取集群 sqlserver 实例列表。

        :param cluster: 集群对象
        :return: ["ip:port", ...]
        边界：无 storage 实例时返回 []
        """
        return [p.ip_port for p in list(cluster.storageinstance_set.all())]

    def _get_job_users_for_cluster(self, cluster: Cluster) -> list:
        """获取单个集群实例上以 DBM job 前缀命名的 login 列表。

        :param cluster: 集群对象
        :return: DRS raw resp list
        边界：
          - 集群下无实例 -> 直接返回 []，不发起 RPC；
          - 某个实例 error_msg 非空 -> 记录 error 日志（带 instance 定位），继续处理其它实例。
        """
        instances = self._get_storage_instance_for_cluster(cluster=cluster)
        if not instances:
            logger.info("no instance to check: cluster=[%s] id=%s", cluster.name, cluster.id)
            return []

        get_job_users_sql = (
            f"select loginname from master.sys.syslogins where loginname like '{DBM_JOB_TMP_USER_REGULAR}' "
        )

        resp = DRSApi.sqlserver_rpc(
            {
                "addresses": instances,
                "cmds": [get_job_users_sql],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )

        # 统计本集群 RPC 结果，便于观察"正常但无事可做"的静默路径
        failed_cnt: int = 0
        ok_cnt: int = 0
        for info in resp:
            if info["error_msg"]:
                failed_cnt += 1
                logger.error(
                    "get job_users failed in cluster [%s] instance [%s] : [%s]",
                    cluster.name,
                    info.get("address"),
                    info["error_msg"],
                )
            else:
                ok_cnt += 1
        logger.info(
            "cluster scanned: name=[%s] id=%s instances=%d ok=%d failed=%d",
            cluster.name,
            cluster.id,
            len(instances),
            ok_cnt,
            failed_cnt,
        )

        return resp

    @staticmethod
    def _drop_expired_job_user_for_instance(cluster: Cluster, user_info: dict, address: str) -> None:
        """在指定实例上 drop 已过期的临时 login。

        :param cluster: 集群对象（用于取 bk_cloud_id）
        :param user_info: {"loginname": ...}
        :param address: "ip:port"
        :return: None
        边界：drop 失败不捕捉异常，交由上层重试
        """
        DRSApi.sqlserver_rpc(
            {
                "addresses": [address],
                "cmds": [f"drop login [{user_info['loginname']}]"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        logger.info(f"drop login [{user_info['loginname']}] in instance : [{address}]")

        return

    def check_job_user_is_expired(self, cluster: Cluster) -> None:
        """遍历单个集群实例上的 job login，判定过期则 drop。

        :param cluster: 集群对象
        :return: None
        边界：cmd_results 为 None / table_data 为空 -> 跳过；Flow 状态非 TERMINATED/REVOKED/SUCCEEDED -> 跳过
        """
        resp = self._get_job_users_for_cluster(cluster=cluster)
        # 单集群统计：扫描到的 job login 数、判定过期并 drop 的 login 数
        scanned_users: int = 0
        dropped_users: int = 0
        for info in resp:
            if info["cmd_results"] is None:
                continue

            for cmd_result in info["cmd_results"]:
                if not cmd_result.get("table_data", None):
                    # 如果是空列表，则表示实例上没有job_user, 正常跳过处理。
                    continue
                # 如果不是空，则逐个判断随机账号情况,判断已过期，则删除
                for user_info in cmd_result.get("table_data"):
                    scanned_users += 1
                    flow_root_id = user_info["loginname"].replace(DBM_MYSQL_JOB_TMP_USER_PREFIX, "")
                    if FlowTree.objects.filter(
                        root_id=flow_root_id,
                        status__in=_EXPIRED_FLOW_STATUSES,
                    ).exists():
                        # 对应的 job_id 存在且已终止/撤销，视为可安全 drop
                        self._drop_expired_job_user_for_instance(
                            cluster=cluster, user_info=user_info, address=info["address"]
                        )
                        dropped_users += 1
                    else:
                        # 匹配不到，则认为 running 状态，不作处理
                        pass
        logger.info(
            "cluster checked: name=[%s] id=%s scanned_users=%d dropped_users=%d",
            cluster.name,
            cluster.id,
            scanned_users,
            dropped_users,
        )

    def do_check(self) -> None:
        """入口：遍历本批集群，逐个执行过期账号巡检。

        :return: None
        边界：clusters 为空 QuerySet 时直接返回
        """
        clusters = list(self.clusters)
        if not clusters:
            logger.info("check skip, empty cluster batch")
            return
        for cluster in clusters:
            self.check_job_user_is_expired(cluster=cluster)


# ------------------------------ Celery 薄壳 worker ------------------------------


@app.task
def check_expired_job_users_for_sqlserver_batch(cluster_ids: List[int], lock_key: str) -> None:
    """SQLServer 临时账号巡检 —— 单批 Celery worker 任务（薄壳）。

    功能说明：
      - 由 dispatcher 按 Cluster.id 分片投递；
      - 委托 CheckExpiredJobUserForSqlserver(cluster_ids=...) 执行完整巡检；
      - 通过 run_batch_with_lock 统一处理"日志 + 异常上抛 + 释放 batch 锁"。

    :param cluster_ids: 本批要巡检的集群 id 列表
    :param lock_key: 本批对应的 Redis 锁 key，任务结束时释放
    :return: None
    边界：详见 dispatcher.run_batch_with_lock 的 docstring
    """
    with run_batch_with_lock(_SQLSERVER_BATCH_TASK_NAME, lock_key, len(cluster_ids)):
        CheckExpiredJobUserForSqlserver(cluster_ids=cluster_ids).do_check()


# ------------------------------ 模块级 dispatcher 实例 ------------------------------

# SQLServer 巡检 dispatcher（Single 与 HA 合并覆盖，供 task.py 直接调用 dispatch()）
#
# 参数选型说明（针对 ~753 套 SQLServer 集群规模）：
#   - batch_size=15：单批 15 集群串行处理，正常 1.25~2min 内结束，最坏含慢集群 <3min；
#     753/15 = 51 batch，相比默认 batch_size=5 时的 151 batch 显著降低总消息数。
#   - dispatch_window_seconds=1h：错峰投递到 1 小时内平摊，避免瞬时冲击 SQLServer 后端 DRS；
#     hash_cnt=51 与 window=1h 组合下 unit=max(70,60)=70s ≥ 60s，
#     calculate_countdown__mod 每桶恰好 1 batch，达到彻底均匀分布（不踩 60s 硬下限）；
#     相比默认 5min 窗口时的 30 batch/60s 尖峰改善约 30x。
#   - batch_lock_timeout=3h：与 1h 错峰窗口匹配的最坏链路兜底 TTL，
#     覆盖 (countdown 1h + broker 排队 ~30min + 硬超时 30min + 余量 1h)，
#     比默认 12h 缩短 worker 崩溃后的恢复时间；3h < 24h 保证次日 beat 一定可抢到锁。
#   - 其他 timeout（batch soft/hard、dispatch_lock）沿用默认值，15 集群单批耗时
#     远低于 20min soft 上限，无需调整。
#   - 触发时机 07:00 与 MySQL 尾巴（06:00~08:00 窗口 + ~5min 尾巴）在 07:00~08:05
#     有约 1h 执行重叠期，两者 DRS 后端隔离互不干扰，worker 池叠加占用预计 <10 slot。
#   - 若集群数变化：>2000 需上调至 batch_size=30 且窗口 2h 以维持均匀分布；
#     <200 可回退为默认值。
sqlserver_dispatcher: ExpiredJobUserDispatcher = ExpiredJobUserDispatcher(
    name="sqlserver",
    cluster_types=_DEFAULT_SQLSERVER_CLUSTER_TYPES,
    worker_task=check_expired_job_users_for_sqlserver_batch,
    batch_size=15,
    dispatch_window_seconds=1 * TimeUnit.HOUR,
    batch_lock_timeout=3 * TimeUnit.HOUR,
)
