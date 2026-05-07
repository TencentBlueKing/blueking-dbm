# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

按 IP 反查作业平台日志、解析 dbactuator 在 stdout 上抛出的 SQL 执行明细。

日志中的 db 边界由 dbactuator 的 marker 协议提供（详见 dbm-services/mysql/db-tools/
dbactuator/pkg/util/marker/marker.go），形如：

    __DBACTUATOR_EVENT__ {"ts":"...","event":"exec_db_begin","db":"mydb"}
    --------------
    create database `dbm3xas`
    --------------
    Query OK, 1 row affected (0.00 sec)
    __DBACTUATOR_EVENT__ {"ts":"...","event":"exec_db_end","db":"mydb"}

per-SQL 时长来自 mysql -vvv 自身打印的 "(X.XX sec)" token。

注意：DBACTUATOR_PREFIX / EVENT_* 常量是与 Go 侧 marker 包硬编码同步的契约，
两侧改前缀或事件名时必须一起改。当前阶段不抽象到公共层。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from typing import Any, Iterator, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend import env
from backend.components import JobApi
from backend.flow.models import FlowBkJobInstance

logger = logging.getLogger("flow")

# 与 Go 侧 dbm-services/mysql/db-tools/dbactuator/pkg/util/marker/marker.go 同步的协议常量
DBACTUATOR_PREFIX = "__DBACTUATOR_EVENT__"
EVENT_EXEC_DB_BEGIN = "exec_db_begin"
EVENT_EXEC_DB_END = "exec_db_end"

# mysql -vvv 用 14 个 '-' 包夹一条 SQL 的输入回显
_SQL_DELIM_RE = re.compile(r"^-{14,}$")
# 匹配 SQL 文件里的 "USE <db>;" 语句（大小写不敏感、可选反引号、可选分号、可选前后空白）。
# mysql 客户端执行 USE 后当前连接的默认 db 切换到 <db>，后续 SQL 也归属新 db。
_USE_DB_RE = re.compile(
    r"\Ause\s+`?(?P<db>[^\s`;]+)`?\s*;?\s*\Z",
    re.IGNORECASE,
)
# 兼容 mysql 客户端 nice_time() 的耗时输出（业务场景下单 SQL 不会跑超过 1 天，故不解析 day 档位）：
#   "(0.00 sec)"
#   "(1 min 40.00 sec)"
#   "(1 hour 1 min 40.00 sec)"  /  "(2 hours 0 min 1.00 sec)"
# 注意 mysql 源码 nice_time() 单复数规则：
#   - hour / hours  依据数量大小选单复数（1 hour, 2 hours）
#   - min           始终是 "min"（无复数）
#   - sec           始终是 "sec"（无复数）
# 各组件按从大到小依次出现，前面的 hour/min 都是可选的，sec 一定有。
_DURATION_RE = re.compile(
    r"\(\s*" r"(?:(?P<hours>\d+)\s*hours?\s+)?" r"(?:(?P<mins>\d+)\s*min\s+)?" r"(?P<secs>[\d.]+)\s*sec" r"\s*\)"
)


@dataclass
class SqlExecRecord:
    """一条 SQL 在指定 IP 上的执行明细。"""

    job_instance_id: int
    step_instance_id: Optional[int]
    ip: str
    bk_cloud_id: int
    db: str
    sql: str
    duration_sec: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


def parse_sql_logs_by_ip(
    *,
    ip: str,
    root_id: Optional[str] = None,
    ticket_id: Optional[int] = None,
    job_instance_id: Optional[int] = None,
    bk_cloud_id: int = 0,
) -> List[SqlExecRecord]:
    """
    根据 IP 反查 FlowBkJobInstance，把作业平台对应的日志拉下来解析成 SQL 明细。

    @param ip: 目标执行 IP
    @param root_id: 可选，限定到某次流程
    @param ticket_id: 可选，限定到某个单据
    @param job_instance_id: 可选，限定到某个作业实例
    @param bk_cloud_id: 拉日志/匹配 IP 用的云区域，默认 0
    @return: SqlExecRecord 列表，按 (job_instance_id, 解析顺序) 排列

    至少要传 root_id / ticket_id / job_instance_id 之一以缩小查询范围，
    否则会拒绝执行（避免对 FlowBkJobInstance 全表扫描）。
    """
    if not ip:
        raise ValueError(_("ip 不能为空"))
    if not (root_id or ticket_id or job_instance_id):
        raise ValueError(_("必须至少指定 root_id / ticket_id / job_instance_id 之一"))

    candidates = _query_candidate_instances(
        root_id=root_id,
        ticket_id=ticket_id,
        job_instance_id=job_instance_id,
    )
    matched = [inst for inst in candidates if _exec_ips_matches(inst.exec_ips, ip)]
    if not matched:
        logger.info(
            _("按 IP {} 反查未命中 FlowBkJobInstance（root_id={} ticket_id={} job_instance_id={}）").format(
                ip, root_id, ticket_id, job_instance_id
            )
        )
        return []

    records: List[SqlExecRecord] = []
    for inst in matched:
        if not inst.step_instance_id:
            logger.warning(
                _("跳过 job_instance_id={} 节点 {}：无 step_instance_id，无法拉取日志").format(inst.job_instance_id, inst.node_id)
            )
            continue
        log_content = _fetch_log_content(
            job_instance_id=inst.job_instance_id,
            step_instance_id=inst.step_instance_id,
            ip=ip,
            bk_cloud_id=bk_cloud_id,
        )
        if not log_content:
            continue
        for db, sql, duration in _iter_sql_records(log_content):
            records.append(
                SqlExecRecord(
                    job_instance_id=inst.job_instance_id,
                    step_instance_id=inst.step_instance_id,
                    ip=ip,
                    bk_cloud_id=bk_cloud_id,
                    db=db,
                    sql=sql,
                    duration_sec=duration,
                )
            )
    return records


def _query_candidate_instances(
    *,
    root_id: Optional[str],
    ticket_id: Optional[int],
    job_instance_id: Optional[int],
):
    qs = FlowBkJobInstance.objects.all()
    if job_instance_id:
        qs = qs.filter(job_instance_id=job_instance_id)
    if root_id:
        qs = qs.filter(root_id=root_id)
    if ticket_id:
        qs = qs.filter(ticket_id=ticket_id)
    return qs.order_by("id")


def _exec_ips_matches(exec_ips: Any, ip: str) -> bool:
    """
    exec_ips 既可能是 ["1.2.3.4", ...]，也可能是 [{"ip": "1.2.3.4", "bk_cloud_id": 0}, ...]，
    统一在 Python 侧做匹配。空值视为不匹配。
    """
    if not exec_ips or not isinstance(exec_ips, list):
        return False
    for item in exec_ips:
        if isinstance(item, str) and item == ip:
            return True
        if isinstance(item, dict) and str(item.get("ip", "")) == ip:
            return True
    return False


def _fetch_log_content(
    *,
    job_instance_id: int,
    step_instance_id: int,
    ip: str,
    bk_cloud_id: int,
) -> str:
    payload = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "job_instance_id": job_instance_id,
        "step_instance_id": step_instance_id,
        "ip": ip,
        "bk_cloud_id": bk_cloud_id,
    }
    try:
        resp = JobApi.get_job_instance_ip_log(payload, raw=True)
    except Exception as e:
        logger.error(
            _("拉取作业日志失败 job_instance_id={} step_instance_id={} ip={}: {}").format(
                job_instance_id, step_instance_id, ip, e
            )
        )
        return ""
    if not (isinstance(resp, dict) and resp.get("result")):
        logger.warning(
            _("作业日志接口返回异常 job_instance_id={} step_instance_id={} ip={}: {}").format(
                job_instance_id, step_instance_id, ip, resp
            )
        )
        return ""
    return (resp.get("data") or {}).get("log_content") or ""


def _iter_sql_records(log_content: str) -> Iterator[Tuple[str, str, Optional[float]]]:
    """
    单个 IP 的日志正文 -> 流式产出 (db, sql, duration_sec)。

    状态机：
        outside           初始/SQL 与结果都已结算
        reading_sql       已遇到首个 '----' 分隔符，正在收集 SQL 文本
        awaiting_result   第二个 '----' 之后，等待 (X.XX sec) 出现
    任何 marker 行会强制结算当前未完成的 SQL（避免 SQL 跨 marker 边界）。

    db 归属优先级（从高到低）：
        1. SQL 文件里显式的 USE <db>;  ——  最高优先，永久生效直到下一条 USE 覆盖
        2. dbactuator marker exec_db_begin 的 db  ——  仅在还没出现过 USE 时作为初始 db
    """
    marker_db = ""
    use_db = ""
    state = "outside"
    sql_lines: List[str] = []
    pending_sql = ""

    for raw_line in log_content.splitlines():
        line = raw_line.rstrip("\r")
        stripped = line.strip()

        if stripped.startswith(DBACTUATOR_PREFIX):
            if pending_sql:
                record, use_db = _emit_with_use_priority(marker_db, use_db, pending_sql, None)
                yield record
                pending_sql = ""
            state = "outside"
            sql_lines = []
            new_marker_db = _parse_marker_db(stripped)
            if new_marker_db is not None:
                marker_db = new_marker_db
            continue

        if _SQL_DELIM_RE.match(stripped):
            if state == "outside":
                state = "reading_sql"
                sql_lines = []
            elif state == "reading_sql":
                pending_sql = "\n".join(sql_lines).strip()
                sql_lines = []
                state = "awaiting_result" if pending_sql else "outside"
            else:
                # awaiting_result 期间又见分隔符：上一条 SQL 没拿到 sec（如 USE/Database changed），落盘后开新块
                if pending_sql:
                    record, use_db = _emit_with_use_priority(marker_db, use_db, pending_sql, None)
                    yield record
                    pending_sql = ""
                state = "reading_sql"
                sql_lines = []
            continue

        if state == "reading_sql":
            sql_lines.append(line)
            continue

        if state == "awaiting_result" and pending_sql:
            duration = _extract_duration_sec(line)
            if duration is not None:
                record, use_db = _emit_with_use_priority(marker_db, use_db, pending_sql, duration)
                yield record
                pending_sql = ""
                state = "outside"

    if pending_sql:
        record, use_db = _emit_with_use_priority(marker_db, use_db, pending_sql, None)
        yield record


def _emit_with_use_priority(
    marker_db: str, use_db: str, sql: str, duration: Optional[float]
) -> Tuple[Tuple[str, str, Optional[float]], str]:
    """
    按 "USE 优先" 规则构造一条记录，并返回 (record, new_use_db)。

    - 若 sql 是 "USE <db>;"，本条记录的 db = <db>，且 new_use_db = <db>，
      永久覆盖后续记录的 db 归属（直到再出现一条 USE）。
    - 否则若曾经出现过 USE，本条 db = 上一次 USE 的 <db>，与最新 marker 无关。
    - 否则（从未 USE 过）回退到当前 marker_db。
    """
    new_use = _extract_use_db(sql)
    if new_use:
        return (new_use, sql, duration), new_use
    return (use_db or marker_db, sql, duration), use_db


def _extract_use_db(sql: str) -> Optional[str]:
    """如果 sql 是 USE <db>; 形式（大小写不敏感、可选反引号 / 分号），返回 <db>，否则 None。"""
    if not sql:
        return None
    m = _USE_DB_RE.match(sql.strip())
    if not m:
        return None
    return m.group("db")


def _extract_duration_sec(line: str) -> Optional[float]:
    """
    从 mysql 结果行里提取耗时，统一规约成秒（float）。匹配不到返回 None。

    示例：
        "(0.00 sec)"                          -> 0.0
        "(1 min 40.00 sec)"                   -> 100.0
        "(1 hour 1 min 40.00 sec)"            -> 3700.0
        "(2 hours 0 min 1.00 sec)"            -> 7201.0
    """
    m = _DURATION_RE.search(line)
    if not m:
        return None
    try:
        hours = int(m.group("hours") or 0)
        mins = int(m.group("mins") or 0)
        secs = float(m.group("secs"))
    except (TypeError, ValueError):
        return None
    return hours * 3600 + mins * 60 + secs


def _parse_marker_db(line: str) -> Optional[str]:
    """
    解析 marker 行，返回事件需要切换到的 db；end 事件返回 ""，
    解析失败或非关心事件返回 None（调用方据此决定是否覆盖 current_db）。
    """
    payload = line[len(DBACTUATOR_PREFIX) :].strip()
    if not payload:
        return None
    try:
        ev = json.loads(payload)
    except json.JSONDecodeError:
        return None
    event = ev.get("event")
    if event == EVENT_EXEC_DB_BEGIN:
        return str(ev.get("db") or "")
    if event == EVENT_EXEC_DB_END:
        return ""
    return None
