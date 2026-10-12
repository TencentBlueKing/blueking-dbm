# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

通过 DRS（db-remote-service）的 /v2/oracle/rpc 接口执行 Oracle 只读查询。

- DRS 使用纯 Go 驱动 go-ora 直连实例，不依赖 Oracle Instant Client，兼容 11G；
- 连接账号由 DRS 侧配置（ORACLE_SYS_READ_USER / ORACLE_SYS_READ_PASSWORD）
- DRS 只放行 SELECT / WITH 语句。
"""
import logging
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.components import DRSApi
from backend.db_meta.models import StorageInstance
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpInstanceNotFoundException,
    DBMMcpOracleConnectionException,
    DBMMcpOracleQueryException,
    DBMMcpUnsafeIdentifierException,
)
from backend.dbm_aiagent.mcp_tools.oracle.constants import (
    ORACLE_CONNECT_TIMEOUT,
    ORACLE_QUERY_TIMEOUT,
    ORACLE_SERVICE_NAME,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.assert_clustertype import ORACLE_ALLOW_CLUSTER_TYPES

logger = logging.getLogger("root")

# 一条查询：(sql, binds)；binds 中的 :name 占位符会在 Python 侧渲染为 SQL 字面量
Query = Tuple[str, Optional[Dict[str, Any]]]

# DRS HTTP 调用在查询超时之外额外等待的时间（秒）
_DRS_EXTRA_TIMEOUT = 15

_BIND_RE = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")


def resolve_instance(addr: str) -> StorageInstance:
    """按 addr（ip:port）解析 Oracle 存储实例；未命中或命中多个实例（跨云区域同地址）时报错。"""
    if ":" not in addr:
        raise DBMMcpInstanceNotFoundException(msg=f"addr must be ip:port, got: {addr}")
    ip, port_str = addr.rsplit(":", 1)
    try:
        port = int(port_str)
    except ValueError:
        raise DBMMcpInstanceNotFoundException(msg=f"invalid port in addr: {addr}")

    instances = list(
        StorageInstance.objects.filter(machine__ip=ip, port=port, cluster__cluster_type__in=ORACLE_ALLOW_CLUSTER_TYPES)
        .select_related("machine")
        .distinct()[:2]
    )
    if not instances:
        raise DBMMcpInstanceNotFoundException(msg=f"oracle instance not found: {addr}")
    if len(instances) > 1:
        raise DBMMcpInstanceNotFoundException(msg=f"addr {addr} matches multiple oracle instances")
    return instances[0]


def _render_literal(value: Any) -> str:
    """把绑定变量渲染为 SQL 字面量。仅支持 None / bool / int / float / str。"""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DBMMcpUnsafeIdentifierException(msg=f"invalid float bind value: {value}")
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise DBMMcpUnsafeIdentifierException(msg=f"unsupported bind value type: {type(value).__name__}")


def _render_sql(sql: str, binds: Optional[Dict[str, Any]]) -> str:
    """把 :name 占位符替换为字面量（只替换 binds 中存在的名字），并去掉结尾分号。"""
    if binds:
        rendered = {k: _render_literal(v) for k, v in binds.items()}
        sql = _BIND_RE.sub(lambda m: rendered.get(m.group(1), m.group(0)), sql)
    return sql.strip().rstrip(";").strip()


def _call_drs(addr: str, bk_cloud_id: int, cmds: List[str]) -> dict:
    params = {
        "bk_cloud_id": bk_cloud_id,
        "addresses": [addr],
        "cmds": cmds,
        "service_name": ORACLE_SERVICE_NAME,
        "force": False,
        "connect_timeout": ORACLE_CONNECT_TIMEOUT,
        "query_timeout": ORACLE_QUERY_TIMEOUT,
    }
    try:
        resp = DRSApi.oracle_rpc(params, timeout=ORACLE_QUERY_TIMEOUT + _DRS_EXTRA_TIMEOUT)
    except Exception as e:  # pylint: disable=broad-except
        logger.exception("call drs oracle rpc failed: %s", addr)
        raise DBMMcpOracleConnectionException(msg=f"call drs oracle rpc failed for {addr}: {e}")

    if not resp:
        raise DBMMcpOracleConnectionException(msg=f"drs oracle rpc returned empty result for {addr}")
    return resp[0]


def _parse_result(addr: str, addr_res: dict, cmds: List[str]) -> List[List[Dict[str, Any]]]:
    cmd_results = addr_res.get("cmd_results") or []
    addr_error = addr_res.get("error_msg") or ""

    if not cmd_results and addr_error:
        raise DBMMcpOracleConnectionException(msg=f"{addr}: {addr_error}")

    outputs = []
    for idx in range(len(cmds)):
        if idx >= len(cmd_results):
            raise DBMMcpOracleQueryException(msg=f"{addr}: query #{idx} not executed: {addr_error or 'unknown'}")
        res = cmd_results[idx]
        if res.get("error_msg"):
            raise DBMMcpOracleQueryException(msg=f"{addr}: query #{idx} failed: {res['error_msg']}")
        rows = res.get("table_data") or []
        outputs.append([{str(k).lower(): v for k, v in row.items()} for row in rows])
    return outputs


def run_queries(addr: str, queries: Sequence[Query]) -> List[List[Dict[str, Any]]]:
    """
    在同一个连接上顺序执行多条只读查询（一次 DRS 调用）。
    返回值与 queries 一一对应，每条为 [{col(小写): value}, ...]；
    NUMBER 列为 int/float，日期时间列为字符串（YYYY-MM-DD HH24:MI:SS[.FF6]）。

    建连失败/DRS 调用失败抛 DBMMcpOracleConnectionException；单条 SQL 报错抛 DBMMcpOracleQueryException。
    """
    if not queries:
        return []

    instance = resolve_instance(addr)
    cmds = [_render_sql(sql, binds) for sql, binds in queries]
    addr_res = _call_drs(instance.ip_port, instance.machine.bk_cloud_id, cmds)
    return _parse_result(addr, addr_res, cmds)


def run_query(addr: str, sql: str, binds: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """执行单条只读查询，返回 [{col(小写): value}, ...]。"""
    return run_queries(addr, [(sql, binds)])[0]
