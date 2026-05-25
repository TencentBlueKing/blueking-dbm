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
import datetime
from typing import Dict, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses

# SQL 文本截断长度，与 top_requests / blocking_sessions 对齐
_SQL_TEXT_LIMIT = 256

# 时间窗口最大跨度，避免一次扫描过大区间
_MAX_TIME_RANGE = datetime.timedelta(days=7)

# 默认时间窗口：最近 1 小时
_DEFAULT_TIME_RANGE = datetime.timedelta(hours=1)

# order_by 入参 → 排序列 的白名单映射，避免任意列名注入到 ORDER BY
# 注意：DURATION 在 TRACE_TSQL 中单位是"微秒"，但排序方向不受单位影响
_ORDER_BY_COLUMN_MAP = {
    "duration": "DURATION",
    "cpu": "CPU",
    "reads": "READS",
    "writes": "WRITES",
    "starttime": "STARTTIME",
}


def _escape_sql_string(value: str) -> str:
    """把字符串中的单引号转义为两个单引号，避免拼接到 SQL 时被截断/注入。"""
    return value.replace("'", "''")


def _format_dt(dt: datetime.datetime) -> str:
    """统一格式化为 SQL Server 兼容的字面量（不含时区）。"""
    # TRACE_TSQL.STARTTIME 是 datetime 类型，使用 'YYYY-MM-DD HH:MM:SS' 字面量最稳妥
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _build_slow_log_sql(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    database_name: Optional[str],
    min_duration_ms: int,
    top: int,
    order_by_column: str,
) -> str:
    """构建慢日志查询 SQL。

    - 库切到 Monitor，因为 TRACE_TSQL 表落在 Monitor 库
    - DURATION 在 TRACE_TSQL 中是微秒，最终返回值统一换算为毫秒
    - 时间窗口、最低耗时、库名都在 WHERE 里限定，避免全表扫
    """
    # 库名白名单过滤片段（精确匹配）
    db_filter_clause = ""
    if database_name:
        db_filter_clause = f"AND DATABASENAME = N'{_escape_sql_string(database_name)}'"

    # min_duration_ms 转成微秒后参与比较
    min_duration_us = int(min_duration_ms) * 1000

    return f"""
SELECT TOP ({top})
    STARTTIME                          AS starttime,
    ENDTIME                            AS endtime,
    (DURATION / 1000)                  AS duration_ms,
    CPU                                AS cpu_ms,
    READS                              AS reads,
    WRITES                             AS writes,
    ROWCOUNTS                          AS row_counts,
    DATABASENAME                       AS database_name,
    LOGINNAME                          AS login_name,
    NTUSERNAME                         AS nt_user_name,
    APPLICATIONNAME                    AS application_name,
    OBJECTNAME                         AS object_name,
    ERROR                              AS error,
    LEFT(ISNULL(SQLTXT, TEXTDATA), {_SQL_TEXT_LIMIT}) AS sql_text,
    CASE WHEN DATALENGTH(ISNULL(SQLTXT, TEXTDATA)) > {_SQL_TEXT_LIMIT}
         THEN 1 ELSE 0 END             AS sql_text_truncated
FROM [Monitor].dbo.TRACE_TSQL
WHERE STARTTIME >= CONVERT(DATETIME, '{_format_dt(start_time)}', 120)
  AND STARTTIME <= CONVERT(DATETIME, '{_format_dt(end_time)}', 120)
  AND DURATION  >= {min_duration_us}
  {db_filter_clause}
ORDER BY {order_by_column} DESC
""".strip()


def sqlserver_slow_log_query(
    cluster_domain: str,
    address: Optional[str] = None,
    start_time: Optional[datetime.datetime] = None,
    end_time: Optional[datetime.datetime] = None,
    database_name: Optional[str] = None,
    min_duration_ms: int = 0,
    top: int = 20,
    order_by: str = "duration",
) -> Dict:
    """查询慢日志（来源：[Monitor].[dbo].[TRACE_TSQL]）。

    使用通道：sqlserver_sys_read_rpc（Monitor 属系统库范畴，无需业务库权限）。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则缺省查询 master
    :param start_time: 起始时间（含），默认 end_time - 1 小时
    :param end_time: 结束时间（含），默认当前时间
    :param database_name: 可选，按业务库名精确过滤
    :param min_duration_ms: 最小耗时阈值，单位毫秒，默认 0
    :param top: 返回条数上限，默认 20，最大 200
    :param order_by: 排序维度，仅允许 duration/cpu/reads/writes/starttime
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "filter": {...},
        "row_count": N,
        "slow_logs": [...]
    }
    """
    # —— 参数校验 ——
    if top <= 0 or top > 200:
        raise DBMMcpBaseException(msg="top must be in (0, 200]")

    if min_duration_ms < 0:
        raise DBMMcpBaseException(msg="min_duration_ms must be >= 0")

    order_by_column = _ORDER_BY_COLUMN_MAP.get(order_by)
    if not order_by_column:
        raise DBMMcpBaseException(msg=f"invalid order_by: {order_by}, allowed: {list(_ORDER_BY_COLUMN_MAP)}")

    # —— 时间窗口归一化 ——
    now = datetime.datetime.now()
    if end_time is None:
        end_time = now
    if start_time is None:
        start_time = end_time - _DEFAULT_TIME_RANGE

    if start_time >= end_time:
        raise DBMMcpBaseException(msg="start_time must be earlier than end_time")
    if (end_time - start_time) > _MAX_TIME_RANGE:
        raise DBMMcpBaseException(msg=f"time range too large, max allowed: {_MAX_TIME_RANGE.days} days")

    # —— 解析目标实例（缺省走 master）——
    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    # —— 构建并下发 SQL ——
    sql = _build_slow_log_sql(
        start_time=start_time,
        end_time=end_time,
        database_name=database_name,
        min_duration_ms=min_duration_ms,
        top=top,
        order_by_column=order_by_column,
    )

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": [sql],
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_res = rpc_res["cmd_results"][0]
    if cmd_res.get("error_msg"):
        raise DBMMcpBaseException(msg=cmd_res["error_msg"])

    slow_logs = cmd_res.get("table_data") or []

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "filter": {
            "start_time": _format_dt(start_time),
            "end_time": _format_dt(end_time),
            "database_name": database_name,
            "min_duration_ms": min_duration_ms,
            "order_by": order_by,
        },
        "row_count": len(slow_logs),
        "slow_logs": slow_logs,
    }
