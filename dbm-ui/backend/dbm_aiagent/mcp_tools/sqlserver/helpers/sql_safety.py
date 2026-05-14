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
import re
from typing import Tuple

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

# 数据库名 / 标识符的合法字符（SQL Server 规范子集，足够覆盖普通命名）
_IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#@]{0,127}$")

# SQL 长度上限：防止编译期 DoS（超长 SQL 让优化器搜索 plan space 时爆炸）
_MAX_SQL_LENGTH = 64 * 1024  # 64 KB

# 黑名单关键字：SHOWPLAN_XML 模式虽不会真正执行，但仍需在第一道防线里拦截
# 这里只放"无可争议必须禁止"的词，独立词边界匹配，大小写不敏感
_FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "TRUNCATE",
    "DROP",
    "CREATE",
    "ALTER",
    "GRANT",
    "REVOKE",
    "DENY",
    "EXEC",
    "EXECUTE",
    "BACKUP",
    "RESTORE",
    "SHUTDOWN",
    "BULK",
    "OPENROWSET",
    "OPENDATASOURCE",
    "OPENQUERY",
    "WAITFOR",
    "RECONFIGURE",
    "USE",
    "GO",
]
_FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(_FORBIDDEN_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# 系统过程前缀（xp_ / sp_）：禁止用户 SQL 直接调用
_SYS_PROC_PATTERN = re.compile(r"\b(xp_|sp_)\w+", re.IGNORECASE)


def quote_sqlserver_ident(name: str) -> str:
    """对 SQL Server 标识符（库名/表名）做安全包裹。

    仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}，否则直接拒绝。
    返回 "[name]" 形式，可安全用于 USE / FROM 等位置。
    """
    if not name or not _IDENT_PATTERN.match(name):
        raise DBMMcpBaseException(msg=f"invalid sqlserver identifier: '{name}'")
    return f"[{name}]"


def quote_table_idents(dbname: str, schema: str, table: str) -> Tuple[str, str, str]:
    """对 (dbname, schema, table) 三段标识符做严格白名单校验并加 [] 包裹。

    任一段不合法都会抛异常，安全用于拼接进 USE / FROM / sys.objects 过滤等位置。

    :return: (quoted_db, quoted_schema, quoted_table)，均为 "[xxx]" 形式
    """
    quoted_db = quote_sqlserver_ident(dbname)
    quoted_schema = quote_sqlserver_ident(schema)
    quoted_table = quote_sqlserver_ident(table)
    return quoted_db, quoted_schema, quoted_table


def _strip_sql_comments(sql: str) -> str:
    """去掉 SQL 中的 -- 行注释 和 /* */ 块注释，便于后续做关键字校验。"""
    # 块注释（非贪婪，跨行）
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # 行注释
    sql = re.sub(r"--[^\n]*", " ", sql)
    return sql


def _strip_string_literals(sql: str) -> str:
    """去掉 SQL 中的字符串字面量和方括号包裹的标识符，避免误杀。

    SQL Server 的字符串：用单引号包裹，内部 '' 表示转义。
    SQL Server 的标识符：可用 [xxx] 或 "xxx" 包裹（QUOTED_IDENTIFIER ON 时）。

    剥离掉这三类内容后再做关键字匹配，可以避免：
        WHERE name = 'DROP TABLE foo'   -- 字符串里的 DROP 被误杀
        SELECT [Update].x FROM ...      -- 标识符里的 Update 被误杀
        SELECT "Insert" FROM ...        -- QUOTED_IDENTIFIER 里的 Insert
    被错误识别为危险关键字。
    """
    # 单引号字符串（处理 '' 转义）
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    # 方括号标识符（[...]，内部 ]] 转义）
    sql = re.sub(r"\[(?:[^\]]|\]\])*\]", "[]", sql)
    # 双引号标识符（"..."，内部 "" 转义）
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    return sql


def sanitize_select_sql_for_sqlserver(query_sql: str) -> Tuple[str, bool]:
    """校验并归一化用户提交的 SQL，仅允许 SELECT / WITH(CTE) 形式的只读查询。

    校验规则（任一不满足则抛 DBMMcpBaseException）：
      1. 非空字符串 + 长度上限（防编译期 DoS）
      2. 去注释后必须以 SELECT 或 WITH 开头（大小写不敏感）
      3. 不允许多语句（去注释/字符串影响后，裸分号最多出现在末尾）
      4. 不允许出现写/DDL/系统过程等黑名单关键字
         （字符串字面量剥离后再匹配，避免列名/字符串里出现关键字被误杀）
      5. 不允许直接调用 xp_ / sp_ 系统过程

    :return: (clean_sql, was_rewritten)
        clean_sql      - 去掉首尾空白、去掉末尾分号后的 SQL，可直接拼入 cmds
        was_rewritten  - 第一阶段始终为 False，保留字段为后续若做改写预留
    """
    if not query_sql or not query_sql.strip():
        raise DBMMcpBaseException(msg="query_sql is empty")

    if len(query_sql) > _MAX_SQL_LENGTH:
        raise DBMMcpBaseException(msg=f"query_sql is too long ({len(query_sql)} > {_MAX_SQL_LENGTH} bytes)")

    # 先复制一份"干净版"用于规则校验，但最终返回的是去掉首尾空白和结尾分号的原始 SQL
    stripped_sql = _strip_sql_comments(query_sql).strip()

    # 规则 2：必须以 SELECT 或 WITH 开头
    if not re.match(r"^(SELECT|WITH)\b", stripped_sql, re.IGNORECASE):
        raise DBMMcpBaseException(msg="only SELECT / WITH(CTE) statements are allowed")

    # 规则 3：去掉末尾分号后，不允许再出现分号（即不允许多语句）
    body = stripped_sql.rstrip(";").rstrip()
    body_no_literal = _strip_string_literals(body)
    if ";" in body_no_literal:
        raise DBMMcpBaseException(msg="multi-statement is not allowed")

    # 规则 4：黑名单关键字（剥离字符串字面量后再匹配）
    forbidden = _FORBIDDEN_PATTERN.search(body_no_literal)
    if forbidden:
        raise DBMMcpBaseException(msg=f"forbidden keyword in query_sql: {forbidden.group(0).upper()}")

    # 规则 5：禁止 xp_ / sp_ 调用
    sys_proc = _SYS_PROC_PATTERN.search(body_no_literal)
    if sys_proc:
        raise DBMMcpBaseException(msg=f"system procedure is not allowed: {sys_proc.group(0)}")

    # 返回原始 SQL（去掉首尾空白和末尾分号），保持用户原文便于排查
    clean_sql = query_sql.strip().rstrip(";").rstrip()
    return clean_sql, False
