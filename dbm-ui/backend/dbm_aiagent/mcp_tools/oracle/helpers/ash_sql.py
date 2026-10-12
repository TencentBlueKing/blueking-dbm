# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

内存 ASH（v$active_session_history）与历史 ASH（dba_hist_active_sess_history）共用的聚合 SQL。

两者的聚合口径必须一致，差异由参数传入：表名、过滤条件、样本倍率、是否有子游标、
sql_text 的取值优先级。
"""

from typing import List

# ON CPU 样本没有 wait_class / event，统一归并，口径与 AWR 报告一致
_WAIT_CLASS = "CASE WHEN h.session_state = 'ON CPU' THEN 'CPU' ELSE h.wait_class END"
_EVENT = "CASE WHEN h.session_state = 'ON CPU' THEN 'CPU + CPU Wait' ELSE h.event END"

# sql_text 取值片段，r.sql_id 为外层 ranked 子查询的列
SQLSTATS_TEXT = "(SELECT SUBSTR(s.sql_text, 1, 200) FROM v$sqlstats s WHERE s.sql_id = r.sql_id AND ROWNUM = 1)"
HIST_SQLTEXT = (
    "(SELECT DBMS_LOB.SUBSTR(h.sql_text, 200, 1) FROM dba_hist_sqltext h WHERE h.sql_id = r.sql_id AND ROWNUM = 1)"
)


def wait_class_sql(table: str, where: str, interval: int) -> str:
    """DB time 按 wait_class 汇总。"""
    return f"""
SELECT {_WAIT_CLASS}                                      AS wait_class,
       COUNT(*)                                           AS samples,
       COUNT(*) * {interval}                              AS db_time_sec,
       ROUND(RATIO_TO_REPORT(COUNT(*)) OVER () * 100, 2)  AS pct
FROM   {table} h
WHERE  {where}
GROUP BY {_WAIT_CLASS}
ORDER BY 2 DESC
"""


def top_events_sql(table: str, where: str, interval: int) -> str:
    """Top 等待事件，附累计占比、涉及会话数、贡献最多的 SQL。

    pct / pct_cum 在截断前的全量数据上计算，故 RATIO_TO_REPORT 必须在 ROWNUM 子查询内层。
    """
    return f"""
WITH ash AS (
    SELECT {_EVENT} AS event, {_WAIT_CLASS} AS wait_class,
           h.sql_id, h.session_id, h.session_serial#
    FROM   {table} h
    WHERE  {where}
), per_sql AS (
    SELECT event, wait_class, sql_id, COUNT(*) AS cnt
    FROM   ash
    GROUP  BY event, wait_class, sql_id
), agg AS (
    SELECT event, wait_class, SUM(cnt) AS samples,
           MAX(sql_id) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS top_sql_id,
           MAX(cnt)    KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS top_sql_samples
    FROM   per_sql
    GROUP  BY event, wait_class
), sess AS (
    SELECT event, wait_class, COUNT(DISTINCT session_id || ',' || session_serial#) AS sessions
    FROM   ash
    GROUP  BY event, wait_class
)
SELECT * FROM (
    SELECT a.event,
           a.wait_class,
           a.samples,
           a.samples * {interval}                                     AS db_time_sec,
           ROUND(RATIO_TO_REPORT(a.samples) OVER () * 100, 2)         AS pct,
           ROUND(SUM(a.samples) OVER (ORDER BY a.samples DESC, a.event ROWS UNBOUNDED PRECEDING)
                 / SUM(a.samples) OVER () * 100, 2)                   AS pct_cum,
           s.sessions,
           a.top_sql_id,
           a.top_sql_samples * {interval}                             AS top_sql_sec
    FROM   agg a
    JOIN   sess s ON s.event = a.event AND s.wait_class = a.wait_class
    ORDER  BY a.samples DESC, a.event
) WHERE ROWNUM <= :row_limit
"""


def top_sql_sql(
    table: str,
    where: str,
    interval: int,
    sql_text_sources: List[str],
    with_child_number: bool = False,
) -> str:
    """Top SQL（按 DB time），附主要等待事件、执行计划个数、SQL 文本。

    plan_hash_value=0 表示样本未关联到计划，排序时压到最后、取值时置 NULL，避免把 0 传给下游取计划的工具。
    with_child_number 仅对内存 ASH 有意义：子游标是内存概念，历史快照中不存在。
    """
    child_select = ", h.sql_child_number" if with_child_number else ""
    child_group = ", sql_child_number" if with_child_number else ""
    child_col = ", sql_child_number AS child_number" if with_child_number else ""
    # 无计划的样本压到最后，末位列为稳定 tie-break；top_child_number 与 top_plan_hash_value
    # 共用该排序，保证两者描述同一个游标
    plan_rank = "CASE WHEN phv = 0 THEN 1 ELSE 0 END, cnt DESC, " + ("child_number" if with_child_number else "phv")
    child_agg = (
        f"MAX(child_number) KEEP (DENSE_RANK FIRST ORDER BY {plan_rank}) AS top_child_number,"
        if with_child_number
        else ""
    )
    child_out = ", p.top_child_number" if with_child_number else ""

    return f"""
WITH ash AS (
    SELECT h.sql_id, h.sql_plan_hash_value{child_select},
           {_WAIT_CLASS} AS event
    FROM   {table} h
    WHERE  {where}
), tot AS (
    SELECT COUNT(*) AS total_samples FROM ash
), ev AS (
    SELECT sql_id, event, COUNT(*) AS cnt
    FROM   ash
    WHERE  sql_id IS NOT NULL
    GROUP  BY sql_id, event
), agg AS (
    SELECT sql_id, SUM(cnt) AS samples,
           MAX(event) KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS top_event,
           MAX(cnt)   KEEP (DENSE_RANK FIRST ORDER BY cnt DESC) AS top_event_samples
    FROM   ev
    GROUP  BY sql_id
), pl0 AS (
    SELECT sql_id, sql_plan_hash_value AS phv{child_col}, COUNT(*) AS cnt
    FROM   ash
    WHERE  sql_id IS NOT NULL
    GROUP  BY sql_id, sql_plan_hash_value{child_group}
), pl AS (
    SELECT sql_id,
           COUNT(DISTINCT CASE WHEN phv <> 0 THEN phv END)                AS plan_count,
           {child_agg}
           MAX(CASE WHEN phv <> 0 THEN phv END)
               KEEP (DENSE_RANK FIRST ORDER BY {plan_rank})               AS top_plan_hash_value
    FROM   pl0
    GROUP  BY sql_id
), ranked AS (
    SELECT * FROM (
        SELECT a.sql_id,
               a.samples,
               a.samples * {interval}                                AS db_time_sec,
               ROUND(RATIO_TO_REPORT(a.samples) OVER () * 100, 2)    AS pct_of_sql_time,
               ROUND(a.samples * 100 / NULLIF(t.total_samples, 0), 2) AS pct_of_db_time,
               a.top_event,
               ROUND(a.top_event_samples * 100 / a.samples, 1)       AS top_event_pct,
               p.plan_count,
               p.top_plan_hash_value{child_out}
        FROM   agg a
        JOIN   pl p ON p.sql_id = a.sql_id
        CROSS  JOIN tot t
        ORDER  BY a.samples DESC, a.sql_id
    ) WHERE ROWNUM <= :row_limit
)
SELECT r.*, COALESCE({', '.join(sql_text_sources)}) AS sql_text
FROM ranked r
ORDER BY r.db_time_sec DESC, r.sql_id
"""
