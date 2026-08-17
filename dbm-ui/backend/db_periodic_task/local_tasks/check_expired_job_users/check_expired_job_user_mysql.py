# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 临时（Job）账号巡检 —— 业务实现 + Celery worker 薄壳 + 定制分发器实例。

设计要点 / 怎么做：
  - 三段职责，同文件，边界清晰：
    1) `CheckExpiredJobUserForMysql`：单批业务巡检器（不感知锁 / Celery）；
    2) `check_expired_job_users_for_mysql_batch`：Celery @app.task 薄壳；
    3) 模块级 `mysql_dispatcher`：ExpiredJobUserDispatcher 实例，供 task.py 调用。
  - 通用调度骨架（分片/错峰/双层锁/投递）复用 dispatcher.ExpiredJobUserDispatcher，本文件不重复实现。
  - 与 SQLServer 版本共享同一份分发器，仅通过 worker_task / cluster_types 参数化差异。
"""
import logging
from typing import Iterable, List, Optional

from blueapps.core.celery.celery import app

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.check_expired_job_users.dispatcher import (
    ExpiredJobUserDispatcher,
    run_batch_with_lock,
)
from backend.db_periodic_task.utils import TimeUnit
from backend.flow.consts import DBM_MYSQL_JOB_TMP_USER_PREFIX, StateType
from backend.flow.models import FlowTree

logger = logging.getLogger("root")

# ------------------------------ 常量 / 配置 ------------------------------

# MySQL 巡检允许的集群类型白名单；其它类型直接拒绝，避免误清理其它 DB 的账号
_ALLOWED_MYSQL_CLUSTER_TYPES: frozenset = frozenset(
    {ClusterType.TenDBHA, ClusterType.TenDBCluster, ClusterType.TenDBSingle}
)

# MySQL 巡检默认覆盖的集群类型（dispatcher 默认值）
_DEFAULT_MYSQL_CLUSTER_TYPES: List[ClusterType] = [
    ClusterType.TenDBSingle,
    ClusterType.TenDBHA,
    ClusterType.TenDBCluster,
]

# 判定为"已过期"的 Flow 状态集合：终止 / 已完成
_EXPIRED_FLOW_STATUSES: List[str] = [StateType.REVOKED, StateType.FINISHED]

# host 白名单：仅这两类才认定为 dbm 产生的临时账号；其它 host 一律不清理
_LOCAL_HOSTS: frozenset = frozenset({"localhost"})

# Celery worker 任务名，仅用于日志展示
_MYSQL_BATCH_TASK_NAME: str = "check_expired_job_users_for_mysql"


# ------------------------------ 业务巡检器 ------------------------------


class CheckExpiredJobUserForMysql(object):
    """MySQL 集群 Job 临时账号过期巡检器（单批工作单元）。

    职责：
      - 对传入的一批集群，抓取其上以 DBM_MYSQL_JOB_TMP_USER_PREFIX 开头的账号；
      - 反查账号名后缀对应的 flow_root_id，若 Flow 已 TERMINATED / REVOKED / SUCCEEDED，则 drop 该账号；
      - 严格限制：仅 host in [localhost, 实例本机 IP] 才认定为 dbm 产生的临时账号。

    使用方式：
      CheckExpiredJobUserForMysql(cluster_ids=[1, 2, 3]).do_check()

    边界：
      - cluster_ids 为空 -> do_check 直接返回，不发起任何 RPC；
      - 集群下无实例 -> 跳过；
      - DRS RPC 失败 -> 记录 error 日志，不抛异常，等下一周期重试；
      - drop user RPC 失败 -> 不捕捉，等待下一周期处理（保持原语义）。
    """

    # host 白名单策略常量：
    #   strict   —— 仅 {localhost, 本机IP}；定时任务默认，与创建时的 host 集合完全对齐，最安全；
    #   topology —— strict 基础上 + 集群拓扑内所有节点 IP；用于人工清理主从同步漂移账号；
    #   loose    —— 不校验 host；应急兜底，谨慎使用。
    HOST_MODE_STRICT: str = "strict"
    HOST_MODE_TOPOLOGY: str = "topology"
    HOST_MODE_LOOSE: str = "loose"

    def __init__(
        self,
        cluster_ids: Optional[Iterable[int]] = None,
        mysql_cluster_types: Optional[List[ClusterType]] = None,
        host_mode: str = HOST_MODE_STRICT,
    ) -> None:
        """初始化巡检器。

        入参二选一：
          - 优先使用 cluster_ids（分片后的一批集群 id）；
          - 若未传 cluster_ids，则退化为按 mysql_cluster_types 全量拉取（兼容旧调用）。

        :param cluster_ids: 待巡检的集群 id 列表；由上游 dispatcher 分片后传入
        :param mysql_cluster_types: 集群类型白名单；仅在 cluster_ids 未传时生效
        :param host_mode: host 白名单策略；取值见 HOST_MODE_STRICT/TOPOLOGY/LOOSE，
                          默认 strict（等价于历史行为，定时任务无需传此参数）

        边界：
          - 传入的 cluster_type 不在 MySQL 白名单 -> 抛 Exception，避免误操作其它 DB
          - cluster_ids 与 mysql_cluster_types 均未传 -> 视为空批
          - host_mode 传入未知值 -> 抛 ValueError，防止误用为宽策略
        """
        if host_mode not in (self.HOST_MODE_STRICT, self.HOST_MODE_TOPOLOGY, self.HOST_MODE_LOOSE):
            raise ValueError(f"invalid host_mode: {host_mode}")
        self.host_mode: str = host_mode

        base_qs = Cluster.objects.filter(cluster_type__in=_ALLOWED_MYSQL_CLUSTER_TYPES)

        if cluster_ids is not None:
            self.clusters = base_qs.filter(id__in=list(cluster_ids)).prefetch_related(
                "storageinstance_set",
                "proxyinstance_set__tendbclusterspiderext",
            )
            return

        if mysql_cluster_types:
            for mysql_cluster_type in mysql_cluster_types:
                if mysql_cluster_type not in _ALLOWED_MYSQL_CLUSTER_TYPES:
                    raise Exception(f"Invalid cluster_type: expected one of [{mysql_cluster_type}] for MySQL.")
            self.clusters = (
                Cluster.objects.filter(cluster_type__in=mysql_cluster_types)
                .prefetch_related("storageinstance_set")
                .prefetch_related("proxyinstance_set__tendbclusterspiderext")
            )
            return

        # 空批：既没给 ids 也没给 types
        self.clusters = base_qs.none()

    @staticmethod
    def _get_storage_instance_for_cluster(cluster: Cluster) -> List[str]:
        """获取集群下需要巡检的 MySQL 实例列表。

        :param cluster: 集群对象（需已 prefetch storageinstance_set / proxyinstance_set）
        :return: ["ip:port", ...]，对 TenDBCluster 额外包含 spider 与 spider_master 的中控端口
        边界：无 storage/proxy 实例时返回 []
        """
        proxy_instances: List[str] = []
        if cluster.cluster_type == ClusterType.TenDBCluster:
            # 如果是 TenDB Cluster 集群，spider 和中控节点需要检查
            proxy_instances = [p.ip_port for p in list(cluster.proxyinstance_set.all())]
            proxy_instances += [
                f"{p.machine.ip}{IP_PORT_DIVIDER}{p.admin_port}"
                for p in list(
                    cluster.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                    )
                )
            ]

        storage_instances = [p.ip_port for p in list(cluster.storageinstance_set.all())]

        return storage_instances + proxy_instances

    def _get_job_users_for_cluster(self, cluster: Cluster) -> list:
        """查询单个集群下所有实例上以 DBM_MYSQL_JOB_TMP_USER_PREFIX 开头的 job 账号。

        设计要点 / 怎么做：
          - 单集群单次 DRS RPC；同一集群实例必属同一 bk_cloud_id，可聚合到一个请求；
          - 相较"整批集群按 bk_cloud_id 汇聚"：牺牲少量 RPC 次数，换取
              · 更小的单次 RPC 体量（不易触发 DRS 超时 / 大响应）；
              · 更小的失败爆炸半径（单集群卡住不牵连本批其它集群）；
              · 天然拿到 cluster 对象，日志定位不再需要反查 instances_map。
          - 这里不区分它到底是中控节点还是mysql节点， 传入force=true的情况，为了如果实例及时不支持tc_admin参数，不让它报错，也能输出实例信息
        :param cluster: 目标集群对象（需已 prefetch storageinstance_set / proxyinstance_set）
        :return: DRS raw resp list（每个元素形如 {"address", "error_msg", "cmd_results", ...}）
        边界：
          - 集群下无实例 -> 直接返回 []，不发起 RPC；
          - 某个实例 error_msg 非空 -> 记录 error 日志，继续处理其它实例。
        """
        instances = self._get_storage_instance_for_cluster(cluster=cluster)
        if not instances:
            logger.info("no instance to check: cluster=[%s] id=%s", cluster.name, cluster.id)
            return []

        get_job_users_sql = f"select user,host from mysql.user where user like '{DBM_MYSQL_JOB_TMP_USER_PREFIX}%' "

        resp = DRSApi.rpc(
            {
                "addresses": instances,
                "cmds": ["set tc_admin = 0;", get_job_users_sql],
                "force": True,
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

    def _build_allowed_hosts(self, cluster: Cluster, instance_address: str) -> Optional[set]:
        """按 host_mode 构造实例上的 host 白名单。

        :param cluster: 当前处理的集群（需已 prefetch storageinstance_set / proxyinstance_set）
        :param instance_address: 形如 "ip:port"；从中取出实例本机 IP
        :return: host 白名单集合；HOST_MODE_LOOSE 时返回 None，代表"不校验 host"
        边界：
          - strict   -> {localhost, 本机IP}（与创建时的 host 集合完全对齐，默认路径，最安全）；
          - topology -> 上面 + 集群拓扑内所有 storage / proxy 节点 IP；
          - loose    -> None，调用方需自行判断"不校验"。
        """
        instance_ip: str = instance_address.split(IP_PORT_DIVIDER)[0]
        if self.host_mode == self.HOST_MODE_LOOSE:
            return None
        if self.host_mode == self.HOST_MODE_TOPOLOGY:
            topology_ips = {inst.machine.ip for inst in cluster.storageinstance_set.all()} | {
                inst.machine.ip for inst in cluster.proxyinstance_set.all()
            }
            return _LOCAL_HOSTS | {instance_ip} | topology_ips
        # HOST_MODE_STRICT
        return _LOCAL_HOSTS | {instance_ip}

    @staticmethod
    def _drop_expired_job_user_for_instance(cloud_id: int, user_info: dict, address: str) -> None:
        """
        在指定实例上 drop 已过期的临时账号。
        这里不区分它到底是中控节点还是mysql节点， 传入force=true的情况，为了如果实例及时不支持tc_admin参数，不让它报错，
        也是达到drop user 效果。

        :param cloud_id: bk_cloud_id
        :param user_info: {"user": ..., "host": ...}
        :param address: "ip:port"
        :return: None
        边界：drop 失败不捕捉异常，交由上层重试；不写 binlog（仅当前实例生效）
        """
        DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": [
                    "set session sql_log_bin = 0;",
                    "set tc_admin = 0;",
                    f"drop user `{user_info['user']}`@`{user_info['host']}`;",
                    "set session sql_log_bin = 1;",
                ],
                "force": True,
                "bk_cloud_id": cloud_id,
            }
        )
        logger.info(f"drop user [{user_info['user']}@{user_info['host']} in instance : [{address}]")

        return

    def check_job_user_is_expired(self, clusters: List[Cluster]) -> None:
        """遍历本批集群，逐集群查询 job 账号并判定是否过期，过期则 drop。

        设计要点 / 怎么做：
          - 外层按 cluster 迭代：单集群一次 RPC → 立即处理 → 释放；
          - 单集群失败不牵连本批其它集群（异常在 _drop / RPC 层面各自局部化）。

        :param clusters: 本批集群列表
        :return: None
        边界：
          - cmd_results 为 None / table_data 为空 -> 跳过
          - host 不属于 [localhost, 实例本机 IP] -> 视为非 dbm 临时账号，跳过
          - Flow 状态非 TERMINATED / REVOKED / SUCCEEDED -> 视为运行中，跳过
        """
        for cluster in clusters:
            resp = self._get_job_users_for_cluster(cluster=cluster)
            # 单集群统计：扫描到的 job 账号数、判定过期并 drop 的账号数
            scanned_users: int = 0
            dropped_users: int = 0
            for info in resp:
                if info["cmd_results"] is None:
                    continue

                for cmd_result in info["cmd_results"]:
                    if not cmd_result.get("table_data", None):
                        # 空列表 -> 该实例无 job_user，跳过
                        continue
                    for user_info in cmd_result.get("table_data"):
                        scanned_users += 1
                        flow_root_id = user_info["user"].replace(DBM_MYSQL_JOB_TMP_USER_PREFIX, "")
                        # host 白名单按 host_mode 构造：strict/topology 返回集合；loose 返回 None（不校验）
                        allowed_hosts = self._build_allowed_hosts(cluster, info["address"])
                        host_ok = allowed_hosts is None or user_info["host"] in allowed_hosts
                        if (
                            host_ok
                            and FlowTree.objects.filter(
                                root_id=flow_root_id,
                                status__in=_EXPIRED_FLOW_STATUSES,
                            ).exists()
                        ):
                            # host 命中白名单（或 loose 不校验），且 Flow 已终结；可安全 drop
                            self._drop_expired_job_user_for_instance(
                                cloud_id=cluster.bk_cloud_id, user_info=user_info, address=info["address"]
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
        """入口：对构造时传入的一批集群执行完整的过期账号巡检流程。

        :return: None
        边界：clusters 为空 QuerySet 时直接返回
        """
        clusters = list(self.clusters)
        if not clusters:
            logger.info("check skip, empty cluster batch")
            return
        self.check_job_user_is_expired(clusters=clusters)


# ------------------------------ Celery 薄壳 worker ------------------------------


@app.task
def check_expired_job_users_for_mysql_batch(cluster_ids: List[int], lock_key: str) -> None:
    """MySQL 临时账号巡检 —— 单批 Celery worker 任务（薄壳）。

    功能说明：
      - 由 dispatcher 按 Cluster.id 分片投递；
      - 委托 CheckExpiredJobUserForMysql(cluster_ids=...) 执行完整巡检；
      - 通过 run_batch_with_lock 统一处理"日志 + 异常上抛 + 释放 batch 锁"。

    :param cluster_ids: 本批要巡检的集群 id 列表
    :param lock_key: 本批对应的 Redis 锁 key，任务结束时释放
    :return: None
    边界：详见 dispatcher.run_batch_with_lock 的 docstring
    """
    with run_batch_with_lock(_MYSQL_BATCH_TASK_NAME, lock_key, len(cluster_ids)):
        CheckExpiredJobUserForMysql(cluster_ids=cluster_ids).do_check()


# ------------------------------ 模块级 dispatcher 实例 ------------------------------

# MySQL 巡检 dispatcher（供 task.py 直接调用 dispatch()）
#
# 参数选型说明（针对 ~6000 套 MySQL 集群规模）：
#   - batch_size=30：单批 30 集群串行处理，正常 2.5~5min 内结束；
#     6000/30 = 200 batch，相比默认 batch_size=5 时的 1200 batch 显著降低总消息数。
#   - dispatch_window_seconds=2h：错峰投递到 2 小时内平摊，避免瞬时冲击 DRS；
#     每 60s 桶约 1.7 batch = 50 集群，相比默认 5min 窗口时的 240 batch/60s 尖峰
#     改善约 144x；相比 1h 窗口再降 50%，DRS 侧压力进一步平滑。
#     注：hash_cnt=200 与 window=2h 组合下 unit=max(36,60)=60s 仍踩 60s 下限，
#     若要彻底避开下限需将 batch_size 上调至 60（hash_cnt=100，桶宽 72s）。
#   - batch_lock_timeout=5h：与 2h 错峰窗口匹配的最坏链路兜底 TTL，
#     覆盖 (countdown 2h + broker 排队 ~30min + 硬超时 30min + 余量 ~2h)，
#     比默认 12h 缩短 worker 崩溃后的恢复时间；5h < 24h 保证次日 beat 一定可抢到锁。
#   - 其他 timeout（batch soft/hard、dispatch_lock）沿用默认值，30 集群单批耗时
#     远低于 20min soft 上限，无需调整。
#   - 与 07:00 触发的 SQLServer 巡检有 07:00~08:05 约 1h 的执行重叠期，
#     两者 DRS 后端隔离互不影响，仅需监控 worker 池 slot 占用（预计 <15 slot）。
#   - 若集群数变化：>10000 需上调至 batch_size=60 且窗口 3h 以维持均匀分布；
#     <1000 可回退为默认值。
mysql_dispatcher: ExpiredJobUserDispatcher = ExpiredJobUserDispatcher(
    name="mysql",
    cluster_types=_DEFAULT_MYSQL_CLUSTER_TYPES,
    worker_task=check_expired_job_users_for_mysql_batch,
    batch_size=30,
    dispatch_window_seconds=2 * TimeUnit.HOUR,
    batch_lock_timeout=5 * TimeUnit.HOUR,
)
