# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

跨版本（SQL Server 2008 → 2022）"统计过期度" SQL 构造器。

设计动机：
    高版本（2008 R2 SP2 / 2012 SP1+）才有 sys.dm_db_stats_properties，
    能直接拿到 modification_counter / rows_sampled。但我们必须兼容 2008 RTM。

选择"统一低公分母"方案：
    全版本统一使用 sys.sysindexes（2008 RTM 起即可用，2022 仍存在）的
    rowmodctr / rowcnt 字段做判定，避免在调用方做版本探测和分支。

字段语义对齐：
    sys.sysindexes.rowmodctr ≈ sys.dm_db_stats_properties.modification_counter
    sys.sysindexes.rowcnt    ≈ sys.dm_db_stats_properties.rows
    精度略粗但业务结论等价（同一组阈值下判定结果一致）。

风险与兜底：
    sys.sysindexes 已被微软标记为 deprecated（目前所有支持版本仍保留）。
    将来若被移除，仅需修改本文件这一处即可，调用方零感知。

经验阈值：
    - 修改 < 500：不算过期
    - 表行数 < 500 且修改 >= 500：算过期（小表敏感）
    - 否则修改占比 >= 20%：算过期
"""

_STATS_OUTDATED_SQL_LEGACY = """
SELECT
    si.id                                             AS object_id,
    SUM(ISNULL(si.rowmodctr, 0))                      AS total_modification_counter,
    SUM(
        CASE
            WHEN si.rowcnt IS NULL OR si.rowcnt = 0 THEN 0
            WHEN si.rowmodctr < 500                 THEN 0
            WHEN si.rowcnt   < 500                  THEN 1
            WHEN si.rowmodctr * 1.0 / si.rowcnt >= 0.20 THEN 1
            ELSE 0
        END
    )                                                 AS stats_outdated_count
FROM sys.sysindexes si
JOIN sys.objects o ON o.object_id = si.id
WHERE o.type = 'U'
  AND o.is_ms_shipped = 0
  -- 排除堆主行 (indid=0) 与 LOB 分配单元 (indid=255)：
  -- 堆主行无统计；255 是 text/image 分配单元，不参与统计判定
  AND si.indid BETWEEN 1 AND 254
GROUP BY si.id
""".strip()


def build_stats_outdated_sql() -> str:
    """返回"按 object_id 聚合的统计过期度"子查询 SQL。

    返回结果列：
        - object_id                    : 表对象 ID
        - total_modification_counter   : 该表所有索引/统计累计的未消化修改次数总和
        - stats_outdated_count         : 基于经验阈值判定的过期统计对象数量

    用法：作为子查询/CTE LEFT JOIN 到主查询的 sys.objects 上。

    维护说明：
        若未来 sys.sysindexes 被微软移除，仅需替换本函数实现即可，
        所有调用方（list_table_status / index_analysis.* 等）零感知。
    """
    return _STATS_OUTDATED_SQL_LEGACY
