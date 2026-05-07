# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

按 IP / 单据 反查作业日志，把 dbactuator 执行 SQL 文件时单条 SQL 耗时 ≥ 60s 的记录入库到
backend.db_report.models.MysqlSqlExecDuration 表。

提供两个公共入口：
    record_sql_exec_durations(ip=..., root_id=...)           —— 单 IP 细粒度
    record_sql_exec_durations_by_ticket(ticket_id=...)        —— 单据级一键消费

待 enrich 的字段（sql_type / table_name / table_size）本轮入库时一律留空。
等 SQL 解析 API 接入后由 enrich 路径回填：

    SQL 解析 API 同时返回 sql_type 与 table_names →
        sql_type、table_name 直接 update；
        再用本表已存的 cluster_domain 调
        backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_db_table_size.query_table_size()
        拿 table_size 一并 update。
    无需再回查 db_meta.Cluster。
"""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_report.models import MysqlDbTableSize, MysqlSqlExecDuration
from backend.flow.models import FlowBkJobInstance
from backend.flow.utils.job_log_parser import SqlExecRecord, parse_sql_logs_by_ip

logger = logging.getLogger("flow")

# 单条 SQL 执行耗时 ≥ 该阈值（秒）才入库。函数参数允许覆盖。
LONG_SQL_THRESHOLD_SEC = 0

# Redis Set key：sql_exec_duration_handler.py 端按 ticket_type 装饰器派发后 sadd ticket_id；
# 周期任务端原子 drain 后派发 Celery 消费。
# 该 key 仅本业务（SQL 执行耗时审计）使用，不与 dbm_aiagent.log_analysis 等其它链路共享。
# 业务白名单（哪些 ticket_type 会入队）的 source of truth 不在本文件，
# 而是 backend.flow.signal.sql_exec_duration_handler 的 @create_ticket_handler 注册声明。
SQL_EXEC_DURATION_CONSUME_KEY = "sql_exec_duration_consume"

# table_size 占位查询配置：复刻
# backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_db_table_size 的 ORM 写法，
# 但只 import db_report.models，不跨 mcp_tools layer。
_SIZE_LOOKBACK_HOURS = 48
_SIZE_DEFAULT_INSTANCE_ROLE = InstanceRole.BACKEND_MASTER.value


def record_sql_exec_durations(
    *,
    ip: str,
    root_id: str,
    ticket_id: Optional[int] = None,
    job_instance_id: Optional[int] = None,
    cluster_id: Optional[int] = None,
    bk_cloud_id: int = 0,
    threshold_sec: float = LONG_SQL_THRESHOLD_SEC,
) -> int:
    """
    解析单 IP 的作业日志，把 duration_sec >= threshold_sec 的 SQL 执行明细入库。

    @param ip: 执行 IP
    @param root_id: DBM 流程任务 ID（必填，参数不能为空）
    @param ticket_id: 单据 ID，可选；用于反查 cluster_id 和入库
    @param job_instance_id: 蓝鲸作业实例 ID，可选；用于反查 cluster_id 和精确定位 job
    @param cluster_id: 集群 ID，未传时会按 (root_id [+ ticket_id [+ job_instance_id]]) 反查 FlowBkJobInstance
    @param bk_cloud_id: 拉日志 / 入库用的云区域 ID
    @param threshold_sec: 入库阈值，默认 60s
    @return: 实际新增入库的条数（已存在的会先 dedupe，不重复入库）
    """
    if not ip:
        raise ValueError(_("ip 不能为空"))
    if not root_id:
        raise ValueError(_("root_id 不能为空"))

    sql_records = parse_sql_logs_by_ip(
        ip=ip,
        root_id=root_id,
        ticket_id=ticket_id,
        job_instance_id=job_instance_id,
        bk_cloud_id=bk_cloud_id,
    )
    long_records = _filter_by_threshold(sql_records, threshold_sec)
    if not long_records:
        return 0

    if cluster_id is None:
        cluster_id = _resolve_cluster_id(root_id=root_id, ticket_id=ticket_id, job_instance_id=job_instance_id)
    cluster_domain = _resolve_cluster_domain(cluster_id) if cluster_id else ""

    return _persist(
        sql_records=long_records,
        root_id=root_id,
        cluster_id=cluster_id,
        cluster_domain=cluster_domain,
        ticket_id=ticket_id,
    )


def record_sql_exec_durations_by_ticket(
    *,
    ticket_id: int,
    threshold_sec: float = LONG_SQL_THRESHOLD_SEC,
) -> Dict[str, Any]:
    """
    扫该单据下所有 FlowBkJobInstance，逐 (job_instance_id, ip) 解析作业日志并入库。

    @param ticket_id: 单据 ID（必填）
    @param threshold_sec: 入库阈值，默认 60s
    @return:
        {
            "total_inserted": int,                           # 累计新增条数
            "scanned": int,                                  # 扫描的 (instance, ip) 组合数
            "failures": [                                    # 失败明细，单 IP 失败不中断整体
                {"job_instance_id": int, "ip": str, "error": str},
                ...
            ],
        }
    """
    if not ticket_id:
        raise ValueError(_("ticket_id 不能为空"))

    instances = list(FlowBkJobInstance.objects.filter(ticket_id=ticket_id))
    cluster_domain_cache = _build_cluster_domain_cache(
        cluster_ids=[inst.cluster_id for inst in instances if inst.cluster_id]
    )

    total_inserted = 0
    scanned = 0
    failures: List[Dict[str, Any]] = []

    for inst in instances:
        if not inst.step_instance_id:
            logger.info(
                _("跳过 ticket={} job_instance_id={}：无 step_instance_id，无法拉取日志").format(ticket_id, inst.job_instance_id)
            )
            continue
        cluster_domain = cluster_domain_cache.get(inst.cluster_id, "") if inst.cluster_id else ""
        for ip, bk_cloud_id in _normalize_ips(inst.exec_ips):
            scanned += 1
            try:
                inserted = _record_single_ip_with_known_cluster(
                    ip=ip,
                    root_id=inst.root_id,
                    ticket_id=ticket_id,
                    job_instance_id=inst.job_instance_id,
                    cluster_id=inst.cluster_id,
                    cluster_domain=cluster_domain,
                    bk_cloud_id=bk_cloud_id,
                    threshold_sec=threshold_sec,
                )
                total_inserted += inserted
            except Exception as e:
                logger.exception(
                    _("入库 SQL 执行耗时记录失败 ticket={} job_instance_id={} ip={}: {}").format(
                        ticket_id, inst.job_instance_id, ip, e
                    )
                )
                failures.append(
                    {
                        "job_instance_id": inst.job_instance_id,
                        "ip": ip,
                        "error": str(e),
                    }
                )

    return {"total_inserted": total_inserted, "scanned": scanned, "failures": failures}


def _record_single_ip_with_known_cluster(
    *,
    ip: str,
    root_id: str,
    ticket_id: int,
    job_instance_id: int,
    cluster_id: Optional[int],
    cluster_domain: str,
    bk_cloud_id: int,
    threshold_sec: float,
) -> int:
    """单据级入口的内部实现：cluster_id / cluster_domain 已就绪，跳过反查直接拉日志 + 入库。"""
    sql_records = parse_sql_logs_by_ip(
        ip=ip,
        root_id=root_id,
        ticket_id=ticket_id,
        job_instance_id=job_instance_id,
        bk_cloud_id=bk_cloud_id,
    )
    long_records = _filter_by_threshold(sql_records, threshold_sec)
    if not long_records:
        return 0
    return _persist(
        sql_records=long_records,
        root_id=root_id,
        cluster_id=cluster_id,
        cluster_domain=cluster_domain,
        ticket_id=ticket_id,
    )


def _filter_by_threshold(sql_records: List[SqlExecRecord], threshold_sec: float) -> List[SqlExecRecord]:
    return [r for r in sql_records if r.duration_sec is not None and r.duration_sec >= threshold_sec]


def _resolve_cluster_id(*, root_id: str, ticket_id: Optional[int], job_instance_id: Optional[int]) -> Optional[int]:
    """按 (root_id [+ ticket_id [+ job_instance_id]]) 反查 FlowBkJobInstance 取首条非空 cluster_id。"""
    qs = FlowBkJobInstance.objects.filter(root_id=root_id, cluster_id__isnull=False)
    if job_instance_id:
        qs = qs.filter(job_instance_id=job_instance_id)
    if ticket_id:
        qs = qs.filter(ticket_id=ticket_id)
    return qs.values_list("cluster_id", flat=True).first()


def _resolve_cluster_domain(cluster_id: int) -> str:
    return Cluster.objects.filter(id=cluster_id).values_list("immute_domain", flat=True).first() or ""


def _build_cluster_domain_cache(cluster_ids: Iterable[int]) -> Dict[int, str]:
    """一次性查 db_meta.Cluster，构造 {cluster_id: immute_domain} 缓存，避免每条 SQL 都查表。"""
    unique_ids = {cid for cid in cluster_ids if cid}
    if not unique_ids:
        return {}
    return dict(Cluster.objects.filter(id__in=unique_ids).values_list("id", "immute_domain"))


def _normalize_ips(exec_ips: Any) -> List[Tuple[str, int]]:
    """
    把 FlowBkJobInstance.exec_ips 规约成 [(ip, bk_cloud_id), ...]：
        - ["1.2.3.4", "5.6.7.8"]                                     -> bk_cloud_id 缺省 0
        - [{"ip": "1.2.3.4", "bk_cloud_id": 0}, ...]                 -> 用各自 bk_cloud_id
        - 其他 / None / 空列表                                         -> []
    """
    if not exec_ips or not isinstance(exec_ips, list):
        return []
    result: List[Tuple[str, int]] = []
    for item in exec_ips:
        if isinstance(item, str) and item:
            result.append((item, 0))
        elif isinstance(item, dict):
            ip = str(item.get("ip", "") or "")
            if not ip:
                continue
            try:
                cloud_id = int(item.get("bk_cloud_id", 0) or 0)
            except (TypeError, ValueError):
                cloud_id = 0
            result.append((ip, cloud_id))
    return result


def _query_db_size_bytes(
    *,
    cluster_domain: str,
    db_name: str,
    instance_role: str = _SIZE_DEFAULT_INSTANCE_ROLE,
) -> Optional[int]:
    """
    按 (cluster_domain, instance_role, db_name) 在最近 _SIZE_LOOKBACK_HOURS 小时窗口内，
    取 dteventtimehour 最新一小时的 SUM(table_size) 作为该库整体大小（字节）。

    实现参考 backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_db_table_size.query_table_size
    的 ORM 写法（按小时分组 + Sum + 取最新一小时），但本函数仅 import db_report.models 同包模型，
    不跨 mcp_tools layer。

    table_size 字段当前作为"该 SQL 涉及 db 总大小"的占位值；待 SQL 解析 API 给出 table_name 后，
    enrich 路径可用 (cluster_domain, db_name, table_name) 拉精确单表 size 覆盖该字段。

    容错：MysqlDbTableSize 走 stats_db 路由（容量统计库，外部生成）。该数据源在
    部分环境（如个人/测试环境）可能未配置 STATS_DB_HOST 等环境变量，连接会
    Connection refused。考虑到 table_size 只是占位字段，查询失败必须吞异常返回 None，
    保护核心 SQL 执行耗时入库不被辅助查询拖垮。

    @return: 字节数；查不到 / 入参不全 / 数据源连接失败时一律返回 None
    """
    if not cluster_domain or not db_name:
        return None

    base_time = timezone.now()
    start_time = base_time - timedelta(hours=_SIZE_LOOKBACK_HOURS)

    try:
        qs = (
            MysqlDbTableSize.objects.filter(
                cluster_domain=cluster_domain,
                instance_role=instance_role,
                dteventtimehour__gte=start_time,
                dteventtimehour__lte=base_time,
                database_name=db_name,
            )
            .values("dteventtimehour")
            .annotate(db_size=Sum("table_size"))
            .order_by("-dteventtimehour")
        )
        row = qs.first()
    except Exception as e:  # pylint: disable=broad-except
        # stats_db 不可用 / 表结构异常 / 任意其它 DB 错误，table_size 退化为 None。
        # 不打 exception 栈以避免日志噪声，warning 一条足够定位环境问题。
        logger.warning(
            _("查询 db 容量失败 cluster_domain={} db_name={}: {} —— table_size 退化为 NULL").format(cluster_domain, db_name, e)
        )
        return None

    if not row or row.get("db_size") is None:
        return None
    return int(row["db_size"])


def _persist(
    *,
    sql_records: List[SqlExecRecord],
    root_id: str,
    cluster_id: Optional[int],
    cluster_domain: str,
    ticket_id: Optional[int],
) -> int:
    """
    构造 MysqlSqlExecDuration 实例并入库，返回真实新增条数。

    实现：
        1. 算 sql_checksum（md5(sql_text) 32 位 hex）
        2. 同批次内去重：按 (job_instance_id, ip, sql_checksum) 去掉一批 SQL 内重复的条目
        3. 入库前查 DB 里已存在的 sql_checksum 集合，过滤掉，避免触发 unique 冲突
        4. table_size 字段：用 (cluster_domain, db_name) 调 _query_db_size_bytes 查到的 db 总大小
           作为占位值；同一批次内同 db 走缓存只查一次。table_name 暂留空。
        5. bulk_create(ignore_conflicts=True) 兜底竞态（其他进程同时入库）
    """
    if not sql_records:
        return 0

    # 1) (record, checksum) 元组列表
    items: List[Tuple[SqlExecRecord, str]] = [(r, hashlib.md5(r.sql.encode("utf-8")).hexdigest()) for r in sql_records]

    # 2) 同批次内 (job_instance_id, ip, sql_checksum) 去重
    seen: set = set()
    unique_items: List[Tuple[SqlExecRecord, str]] = []
    for r, cs in items:
        key = (r.job_instance_id, r.ip, cs)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append((r, cs))

    # 3) 查 DB 里 (root_id, job_instance_id, ip) 范围内已存在的 sql_checksum 集合（按 IP 维度查一次）
    #    本批次 sql_records 都来自单一 IP 的日志解析，取首条即可定位
    first = sql_records[0]
    existing_checksums = set(
        MysqlSqlExecDuration.objects.filter(
            root_id=root_id,
            job_instance_id=first.job_instance_id,
            ip=first.ip,
        ).values_list("sql_checksum", flat=True)
    )
    fresh_items = [(r, cs) for (r, cs) in unique_items if cs not in existing_checksums]
    if not fresh_items:
        return 0

    # 4) table_size 占位值缓存：同一批 record 同一 db 只查一次
    db_size_cache: Dict[str, Optional[int]] = {}

    def _size_for(db: str) -> Optional[int]:
        if not db or not cluster_domain:
            return None
        if db not in db_size_cache:
            db_size_cache[db] = _query_db_size_bytes(cluster_domain=cluster_domain, db_name=db)
        return db_size_cache[db]

    # 5) 入库
    objs = [
        MysqlSqlExecDuration(
            cluster_id=cluster_id,
            cluster_domain=cluster_domain,
            ticket_id=ticket_id,
            root_id=root_id,
            job_instance_id=r.job_instance_id,
            step_instance_id=r.step_instance_id,
            ip=r.ip,
            bk_cloud_id=r.bk_cloud_id,
            db_name=r.db,
            table_name="",
            sql_text=r.sql,
            sql_type="",
            sql_checksum=cs,
            table_size=_size_for(r.db),
            duration_sec=r.duration_sec,
        )
        for r, cs in fresh_items
    ]
    MysqlSqlExecDuration.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)
