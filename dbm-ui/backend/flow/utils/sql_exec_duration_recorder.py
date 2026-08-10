# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

按 IP / 单据 反查作业日志，把 dbactuator 执行 SQL 文件时单条 SQL 耗时 ≥ 阈值的记录入库到
backend.db_report.models.MysqlSqlExecDuration 表。

提供两个公共入口：
    record_sql_exec_durations(ip=..., root_id=...)           —— 单 IP 细粒度
    record_sql_exec_durations_by_ticket(ticket_id=...)        —— 单据级一键消费

入库时通过 SQLSimulationApi.parse_sql_tables 解析 sql_type / table_name，
再按语句类型查 MysqlDbTableSize：
    - 普通表级 DDL/DML：按表 Sum(table_size)，多表求和
    - drop_db：填逻辑库 database_size（TenDBCluster 跨分片求和）
    - call / 过程函数触发器事件：不查 size，table_size 置 NULL
"""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db.models import Max, Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components.sql_import.client import SQLSimulationApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_report.models import MysqlDbTableSize, MysqlSqlExecDuration
from backend.flow.models import FlowBkJobInstance
from backend.flow.utils.job_log_parser import SqlExecRecord, parse_sql_logs_by_ip

logger = logging.getLogger("flow")

# 单条 SQL 执行耗时 ≥ 该阈值（秒）才入库。函数参数允许覆盖。
LONG_SQL_THRESHOLD_SEC = 30.0

# Redis Set key：sql_exec_duration_handler.py 端按 ticket_type 装饰器派发后 sadd ticket_id；
# 周期任务端原子 drain 后派发 Celery 消费。
# 该 key 仅本业务（SQL 执行耗时审计）使用，不与 dbm_aiagent.log_analysis 等其它链路共享。
# 业务白名单（哪些 ticket_type 会入队）的 source of truth 不在本文件，
# 而是 backend.flow.signal.sql_exec_duration_handler 的 @create_ticket_handler 注册声明。
SQL_EXEC_DURATION_CONSUME_KEY = "sql_exec_duration_consume"

# 容量查询：复刻 mysql_db_table_size ORM，只 import db_report.models。
_SIZE_LOOKBACK_HOURS = 48
_SIZE_ROLE_SLAVE = InstanceInnerRole.SLAVE.value
_SIZE_ROLE_ORPHAN = InstanceInnerRole.ORPHAN.value
_SIZE_ROLE_FALLBACKS = (_SIZE_ROLE_SLAVE, _SIZE_ROLE_ORPHAN, InstanceInnerRole.MASTER.value)

# 解析结果中忽略的旁路命令（取 sql_type 时跳过）
_SKIP_SQL_TYPE_CMDS = frozenset({"change_db", "set_option"})
# 不查表/库大小的语句类型（call / 过程 / 函数 / 触发器 / 事件）
_SKIP_SIZE_SQL_TYPES = frozenset(
    {
        "call",
        "create_procedure",
        "drop_procedure",
        "alter_procedure",
        "create_function",
        "drop_function",
        "alter_function",
        "create_spfunction",
        "create_trigger",
        "drop_trigger",
        "create_event",
        "drop_event",
        "alter_event",
    }
)
_DROP_DB_SQL_TYPE = "drop_db"


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
    @param threshold_sec: 入库阈值，默认 30s
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
    @param threshold_sec: 入库阈值，默认 30s
    @return:
        {
            "total_inserted": int,                           # 累计新增条数
            "scanned": int,                                  # 扫描的 (instance, ip) 组合数
            "instance_count": int,                           # 该单据下 FlowBkJobInstance 条数
            "failures": [                                    # 失败明细，单 IP 失败不中断整体
                {"job_instance_id": int, "ip": str, "error": str},
                ...
            ],
        }
    """
    if not ticket_id:
        raise ValueError(_("ticket_id 不能为空"))

    instances = list(FlowBkJobInstance.objects.filter(ticket_id=ticket_id))
    instance_count = len(instances)
    if instance_count == 0:
        logger.info(_("消费 SQL 执行耗时：ticket={} 无 FlowBkJobInstance，跳过解析").format(ticket_id))
        return {"total_inserted": 0, "scanned": 0, "instance_count": 0, "failures": []}

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

    return {
        "total_inserted": total_inserted,
        "scanned": scanned,
        "instance_count": instance_count,
        "failures": failures,
    }


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


def _resolve_sim_cluster_type(cluster_id: Optional[int]) -> str:
    """解析 API 的 cluster_type：TenDBCluster 用 spider，其余用 mysql。"""
    if not cluster_id:
        return "mysql"
    ctype = Cluster.objects.filter(id=cluster_id).values_list("cluster_type", flat=True).first()
    if ctype == ClusterType.TenDBCluster.value:
        return "spider"
    return "mysql"


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


def _lookback_window():
    base_time = timezone.now()
    return base_time - timedelta(hours=_SIZE_LOOKBACK_HOURS), base_time


def _query_table_size_bytes(
    *,
    cluster_domain: str,
    db_name: str,
    table_names: List[str],
) -> Optional[int]:
    """
    按 (cluster_domain, database_name, table_name) 取最近上报小时内 Sum(table_size)。
    TenDBCluster 同小时多行（分片）自动加总；多表再求和。默认 instance_role=slave，失败回退 orphan/master。
    """
    if not cluster_domain or not db_name or not table_names:
        return None
    start_time, base_time = _lookback_window()
    for role in _SIZE_ROLE_FALLBACKS:
        try:
            total = _sum_table_sizes_for_role(
                cluster_domain=cluster_domain,
                db_name=db_name,
                table_names=table_names,
                instance_role=role,
                start_time=start_time,
                base_time=base_time,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                _("查询表容量失败 cluster_domain={} db={} tables={} role={}: {}").format(
                    cluster_domain, db_name, table_names, role, e
                )
            )
            return None
        if total is not None:
            return total
    return None


def _sum_table_sizes_for_role(
    *,
    cluster_domain: str,
    db_name: str,
    table_names: List[str],
    instance_role: str,
    start_time,
    base_time,
) -> Optional[int]:
    qs = (
        MysqlDbTableSize.objects.filter(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
            dteventtimehour__gte=start_time,
            dteventtimehour__lte=base_time,
            database_name=db_name,
            table_name__in=table_names,
        )
        .values("database_name", "table_name", "dteventtimehour")
        .annotate(table_size=Sum("table_size"))
        .order_by("database_name", "table_name", "-dteventtimehour")
    )
    seen = set()
    total = 0
    found = False
    for item in qs:
        key = (item["database_name"], item["table_name"])
        if key in seen:
            continue
        seen.add(key)
        if item.get("table_size") is None:
            continue
        total += int(item["table_size"])
        found = True
    return total if found else None


def _query_database_size_bytes(*, cluster_domain: str, db_name: str) -> Optional[int]:
    """
    drop_db 专用：取最近上报小时内该逻辑库的 database_size。
    TenDBCluster：按 original_database_name 取 Max(database_size) 再对各分片求和。
    """
    if not cluster_domain or not db_name:
        return None
    start_time, base_time = _lookback_window()
    for role in _SIZE_ROLE_FALLBACKS:
        try:
            total = _sum_db_sizes_for_role(
                cluster_domain=cluster_domain,
                db_name=db_name,
                instance_role=role,
                start_time=start_time,
                base_time=base_time,
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(
                _("查询库容量失败 cluster_domain={} db_name={} role={}: {}").format(cluster_domain, db_name, role, e)
            )
            return None
        if total is not None:
            return total
    return None


def _sum_db_sizes_for_role(
    *,
    cluster_domain: str,
    db_name: str,
    instance_role: str,
    start_time,
    base_time,
) -> Optional[int]:
    qs = (
        MysqlDbTableSize.objects.filter(
            cluster_domain=cluster_domain,
            instance_role=instance_role,
            dteventtimehour__gte=start_time,
            dteventtimehour__lte=base_time,
            database_name=db_name,
        )
        .values("original_database_name", "dteventtimehour")
        .annotate(db_size=Max("database_size"))
        .order_by("-dteventtimehour")
    )
    latest_hour = None
    total = 0
    found = False
    for item in qs:
        hour = item["dteventtimehour"]
        if latest_hour is None:
            latest_hour = hour
        if hour != latest_hour:
            break
        if item.get("db_size") is None:
            continue
        total += int(item["db_size"])
        found = True
    return total if found else None


def _parse_sql_queries(sql: str, sim_cluster_type: str) -> List[Dict[str, Any]]:
    """调用 parse_sql_tables；失败返回空列表，不阻断入库。"""
    if not sql:
        return []
    try:
        result = SQLSimulationApi.parse_sql_tables(
            params={"cluster_type": sim_cluster_type, "sql": sql},
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("解析 SQL 表名失败: {} —— sql_type/table_name 留空").format(e))
        return []
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # 兼容偶发整包响应
        data = result.get("data")
        return data if isinstance(data, list) else []
    return []


def _first_sql_type(queries: List[Dict[str, Any]]) -> str:
    """首条非 change_db/set_option 的 command；都没有则取任意非空 command。"""
    fallback = ""
    for q in queries:
        if not isinstance(q, dict):
            continue
        cmd = str(q.get("command") or "")
        if not cmd:
            continue
        if not fallback:
            fallback = cmd
        if cmd not in _SKIP_SQL_TYPE_CMDS:
            return cmd
    return fallback


def _collect_tables_and_db(queries: List[Dict[str, Any]]) -> Tuple[List[str], str, str]:
    """收集去重表名、带表行的 db_name、最近 change_db 的 db_name。"""
    table_names: List[str] = []
    size_db = ""
    last_use_db = ""
    for q in queries:
        if not isinstance(q, dict):
            continue
        cmd = str(q.get("command") or "")
        db_name = str(q.get("db_name") or "")
        table_name = str(q.get("table_name") or "")
        if cmd == "change_db" and db_name:
            last_use_db = db_name
        if not table_name or table_name in table_names:
            continue
        table_names.append(table_name)
        if db_name and not size_db:
            size_db = db_name
    return table_names, size_db, last_use_db


def _extract_sql_meta(queries: List[Dict[str, Any]], fallback_db: str) -> Dict[str, Any]:
    """从 ParseIncludeTableBase 列表提取 sql_type / table_name / size 用 db_name。"""
    table_names, size_db, last_use_db = _collect_tables_and_db(queries)
    if not size_db:
        size_db = last_use_db or fallback_db or ""
    return {
        "sql_type": _first_sql_type(queries),
        "table_name": ",".join(table_names),
        "table_names": table_names,
        "size_db": size_db,
    }


def _resolve_table_size(
    *,
    sql_type: str,
    cluster_domain: str,
    size_db: str,
    table_names: List[str],
) -> Optional[int]:
    """按 sql_type 决定查表 size / 库 size / 跳过。"""
    if not sql_type or sql_type in _SKIP_SIZE_SQL_TYPES:
        return None
    if sql_type == _DROP_DB_SQL_TYPE:
        return _query_database_size_bytes(cluster_domain=cluster_domain, db_name=size_db)
    if not table_names:
        return None
    return _query_table_size_bytes(
        cluster_domain=cluster_domain,
        db_name=size_db,
        table_names=table_names,
    )


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
        2. 同批次内去重：按 (job_instance_id, ip, sql_checksum)
        3. 入库前过滤 DB 已存在 checksum
        4. 调 parse_sql_tables 填 sql_type/table_name，再按类型查 table_size
        5. bulk_create(ignore_conflicts=True)
    """
    if not sql_records:
        return 0

    items: List[Tuple[SqlExecRecord, str]] = [(r, hashlib.md5(r.sql.encode("utf-8")).hexdigest()) for r in sql_records]

    seen: set = set()
    unique_items: List[Tuple[SqlExecRecord, str]] = []
    for r, cs in items:
        key = (r.job_instance_id, r.ip, cs)
        if key in seen:
            continue
        seen.add(key)
        unique_items.append((r, cs))

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

    sim_cluster_type = _resolve_sim_cluster_type(cluster_id)
    parse_cache: Dict[str, Dict[str, Any]] = {}
    size_cache: Dict[Tuple[str, str, str], Optional[int]] = {}

    objs = []
    for r, cs in fresh_items:
        if cs not in parse_cache:
            queries = _parse_sql_queries(r.sql, sim_cluster_type)
            parse_cache[cs] = _extract_sql_meta(queries, fallback_db=r.db or "")
        meta = parse_cache[cs]
        sql_type = meta["sql_type"]
        table_name = meta["table_name"]
        size_db = meta["size_db"]
        table_names = meta["table_names"]

        size_key = (sql_type, size_db, table_name)
        if size_key not in size_cache:
            size_cache[size_key] = _resolve_table_size(
                sql_type=sql_type,
                cluster_domain=cluster_domain,
                size_db=size_db,
                table_names=table_names,
            )
        objs.append(
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
                table_name=table_name,
                sql_text=r.sql,
                sql_type=sql_type,
                sql_checksum=cs,
                table_size=size_cache[size_key],
                duration_sec=r.duration_sec,
            )
        )
    MysqlSqlExecDuration.objects.bulk_create(objs, ignore_conflicts=True)
    return len(objs)
