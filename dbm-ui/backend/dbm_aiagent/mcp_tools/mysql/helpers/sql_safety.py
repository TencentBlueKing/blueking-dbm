# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQL 安全工具：

- ``quote_ident``：把库/表/列等标识符安全地包裹为 ``` `name` ```，拒绝可能用于注入逃逸的字符。
- ``sanitize_select_sql``：严格校验用户提交的 SQL，仅放行 SELECT/UPDATE/DELETE/INSERT 四类，
  并把 UPDATE/DELETE/INSERT...SELECT 改写为等价 SELECT，使其能在只读账号下走 EXPLAIN。

校验流程（任一层失败即拒绝）：

1. 原文黑名单：``/*!`` 可执行注释 / NUL 字节
2. 剥掉字符串字面量与普通注释后，再次跑关键字黑名单
   （挡 ``INTO/**/OUTFILE`` 之类用注释拆关键字的绕过，同时避免误杀字符串内容）
3. ``sqlglot.parse(sql, read="mysql")`` 必须返回恰好 1 条 statement
4. 顶层节点必须 ∈ ``{Select, SetOperation, Update, Delete, Insert}``
5. AST 内不允许出现 ``Into`` / ``Lock`` / ``Command`` / 危险匿名函数
6. 改写为等价 SELECT
7. ``root.sql(dialect="mysql")`` 重新序列化后下发，注释/hint 一并归一化
"""
import re
from typing import Tuple

import sqlglot
from sqlglot import exp

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpUnsafeIdentifierException, DBMMcpUnsafeSQLException

# ---------- Spider 分片库名改写 ----------

# Spider 中间件分片后缀，dbname 改写为 dbname{_SPIDER_SHARD_SUFFIX}
_SPIDER_SHARD_SUFFIX = "_0"

# 系统库白名单：这些库名不做 Spider 分片改写
_SPIDER_REWRITE_SKIP_DBS = frozenset(
    {
        "mysql",
        "sys",
        "information_schema",
        "performance_schema",
        "test",
        "infodba_schema",
    }
)

# ---------- 标识符 ----------

# MySQL 标识符的最大字节长度（与 information_schema 一致）
_MAX_IDENT_BYTES = 64

# 这些字符要么不可能出现在合法库表名里（控制字符 / NUL），要么会破坏反引号包裹（反引号自身）
_FORBIDDEN_IDENT_CHARS = ("\x00", "\n", "\r", "\t", "`")

# 字符串字面量场景下的禁用字符：NUL / 换行 / 回车（合法库表名里不会出现）
_FORBIDDEN_STRING_LITERAL_CHARS = ("\x00", "\n", "\r")


def quote_string_literal(value: str) -> str:
    """把库/表名等用户输入安全地包裹为 MySQL 字符串字面量 ``'value'``。

    用于 WHERE 子句里 ``table_schema = 'xxx'`` / ``table_name IN ('a','b')`` 这种**值比较**
    场景，注意与 ``quote_ident`` 的区别：后者用反引号包裹，是**标识符引用**，不能用作字符串值。

    校验：

    - 拒绝空字符串
    - 拒绝长度 > 64 字节（与 MySQL 标识符上限一致）
    - 拒绝 NUL / ``\\n`` / ``\\r``
    - 转义反斜杠和单引号（``\\`` → ``\\\\``，``'`` → ``''``），同时挡住单引号转义与字符串拼接绕过
    """
    if not value:
        raise DBMMcpUnsafeIdentifierException(msg="empty string literal")

    if len(value.encode("utf-8")) > _MAX_IDENT_BYTES:
        raise DBMMcpUnsafeIdentifierException(msg=f"string literal too long (>64 bytes): {value!r}")

    for bad in _FORBIDDEN_STRING_LITERAL_CHARS:
        if bad in value:
            raise DBMMcpUnsafeIdentifierException(msg=f"invalid character in string literal: {value!r}")

    escaped = value.replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def quote_ident(name: str) -> str:
    """把库/表名安全地包裹为反引号形式。

    兼容历史含 ``-`` / ``.`` / ``$`` / 中文等的库表名，仅拒绝：

    - 空字符串
    - 长度 > 64 字节
    - 含 NUL / ``\\n`` / ``\\r`` / ``\\t`` / 反引号

    其余字符一律放行，输出 ``` `name` ```。
    """
    if not name:
        raise DBMMcpUnsafeIdentifierException(msg="empty identifier")

    if len(name.encode("utf-8")) > _MAX_IDENT_BYTES:
        raise DBMMcpUnsafeIdentifierException(msg=f"identifier too long (>64 bytes): {name!r}")

    for bad in _FORBIDDEN_IDENT_CHARS:
        if bad in name:
            raise DBMMcpUnsafeIdentifierException(msg=f"invalid character in identifier: {name!r}")

    return f"`{name}`"


# ---------- SQL 主体 ----------

# 这两组正则的语义不同：
#
# - ``_FORBIDDEN_PRE_STRIP``：在剥字符串/注释之前匹配。这里只放 ``/*!`` 与 NUL，
#   因为它们只要原文里出现就视为攻击意图（即使包在字符串里也极其可疑）。
# - ``_FORBIDDEN_POST_STRIP``：在剥掉字符串字面量与普通注释后再匹配，避免把
#   ``SELECT 'INTO OUTFILE /tmp'`` 这种合法只读查询误杀，同时确保
#   ``INTO/**/OUTFILE`` / ``FOR/**/UPDATE`` 这类用注释拆关键字的绕过也能命中。
_FORBIDDEN_PRE_STRIP = (
    # MySQL 可执行注释：/*!50000 ... */ 会被 MySQL 真实执行，但 sqlglot 仅当成普通注释，
    # 是非常典型的 AST 校验绕过手法，因此原文一旦出现就拒绝。
    re.compile(r"/\*!"),
    re.compile(r"\x00"),
)

_FORBIDDEN_POST_STRIP = (
    re.compile(r"\bINTO\s+(OUTFILE|DUMPFILE)\b", re.IGNORECASE),
    re.compile(r"\bFOR\s+UPDATE\b", re.IGNORECASE),
    re.compile(r"\bLOCK\s+IN\s+SHARE\s+MODE\b", re.IGNORECASE),
    re.compile(
        r"\b(LOAD_FILE|SLEEP|BENCHMARK|GET_LOCK|RELEASE_LOCK|RELEASE_ALL_LOCKS"
        r"|MASTER_POS_WAIT|WAIT_FOR_EXECUTED_GTID_SET|SYS_EXEC|SYS_EVAL|PG_SLEEP)\s*\(",
        re.IGNORECASE,
    ),
)


def _strip_strings_and_comments(sql: str) -> str:
    """把 SQL 里的字符串字面量、反引号标识符、块/行注释统一替换为空格。

    目的是给关键字黑名单提供一个"只剩代码骨架"的视图：

    - ``'xxx'`` / ``"xxx"`` / ``` `xxx` ``` 里的内容不再参与匹配，避免误杀
      ``SELECT 'INTO OUTFILE /tmp'`` 这种合法语句；
    - ``/* ... */``（含 ``/*! ... */``，``/*!`` 已在前置正则单独拦下）会被替换为单空格，
      因此 ``INTO/**/OUTFILE`` 在剥后变成 ``INTO OUTFILE``，可被 ``\\bINTO\\s+OUTFILE\\b`` 命中；
    - ``-- `` 行注释（MySQL 要求 ``--`` 后跟空白才算注释）与 ``#`` 行注释剥到行尾。
    """
    out = []
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]

        # 字符串字面量与反引号标识符
        if c in ("'", '"', "`"):
            quote = c
            out.append(" ")
            i += 1
            while i < n:
                ch = sql[i]
                # 反斜杠转义只对 ' " 字符串生效，反引号不识别 \\ 转义
                if ch == "\\" and quote != "`" and i + 1 < n:
                    i += 2
                    continue
                if ch == quote:
                    # 双写转义： '' 或 "" 或 ``
                    if i + 1 < n and sql[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue

        # 块注释 /* ... */
        if c == "/" and i + 1 < n and sql[i + 1] == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            out.append(" ")
            continue

        # 行注释 -- （MySQL 要求 -- 后跟空白才算注释；其余按减号处理）
        if c == "-" and i + 1 < n and sql[i + 1] == "-":
            if i + 2 < n and sql[i + 2] in (" ", "\t", "\n", "\r"):
                while i < n and sql[i] != "\n":
                    i += 1
                out.append(" ")
                continue

        # 行注释 #
        if c == "#":
            while i < n and sql[i] != "\n":
                i += 1
            out.append(" ")
            continue

        out.append(c)
        i += 1

    return "".join(out)


# 顶层 AST 节点白名单：
# - Select / Update / Delete / Insert 是经典 DML
# - SetOperation（UNION / INTERSECT / EXCEPT）也是只读多结果集查询，可以直接 EXPLAIN
_ALLOWED_ROOT_TYPES = (exp.Select, exp.SetOperation, exp.Update, exp.Delete, exp.Insert)

# 在 AST 中出现即拒绝的节点类型
_FORBIDDEN_NODE_TYPES = (exp.Into, exp.Lock, exp.Command)

# 危险匿名函数（资源消耗 / 锁 / 文件 / 复制等副作用）
_DANGEROUS_FUNCTIONS = frozenset(
    {
        "sleep",
        "benchmark",
        "get_lock",
        "release_lock",
        "release_all_locks",
        "load_file",
        "master_pos_wait",
        "wait_for_executed_gtid_set",
        "sys_exec",
        "sys_eval",
    }
)


def sanitize_select_sql(query_sql: str, rewrite_spider_dbname: bool = False) -> Tuple[str, bool]:
    """校验用户提交的 SQL 并归一化为可被 EXPLAIN 的 SELECT。

    返回 ``(sanitized_sql, was_rewritten)``：

    - ``sanitized_sql``：归一化后的 SELECT 字符串，调用方加 ``EXPLAIN `` 前缀即可下发。
    - ``was_rewritten``：用户传入的语句是否被改写（UPDATE/DELETE/INSERT...SELECT 都会被改写）。

    参数：

    - ``rewrite_spider_dbname``：若为 True，将 SQL 中 ``dbname.tablename`` 形式的库名
      改写为 ``dbname_0.tablename``（系统库除外），用于 Spider 中间件场景下路由到分片实例。
    """
    if not query_sql or not query_sql.strip():
        raise DBMMcpUnsafeSQLException(msg="empty sql")

    # 第 1 层：原文黑名单（``/*!`` / NUL 等只要出现就有问题，无视字符串语境）
    for pat in _FORBIDDEN_PRE_STRIP:
        if pat.search(query_sql):
            raise DBMMcpUnsafeSQLException(msg=f"forbidden token matched: {pat.pattern}")

    # 第 2 层：剥掉字符串字面量与普通注释后再做关键字黑名单，防住
    # ``INTO/**/OUTFILE`` 这种用注释拆关键字的绕过，同时避免误杀字符串内容
    skeleton = _strip_strings_and_comments(query_sql)
    for pat in _FORBIDDEN_POST_STRIP:
        if pat.search(skeleton):
            raise DBMMcpUnsafeSQLException(msg=f"forbidden token matched: {pat.pattern}")

    try:
        # 同时捕 ParseError 与 TokenError；后者会在反引号未闭合等场景抛出
        statements = sqlglot.parse(query_sql, read="mysql")
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        raise DBMMcpUnsafeSQLException(msg=f"sql parse failed: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise DBMMcpUnsafeSQLException(msg=f"must be exactly one statement, got {len(statements)}")

    root = statements[0]
    if not isinstance(root, _ALLOWED_ROOT_TYPES):
        raise DBMMcpUnsafeSQLException(
            msg=f"only top-level SELECT/UPDATE/DELETE/INSERT is allowed, got {type(root).__name__}"
        )

    for node in root.walk():
        if isinstance(node, _FORBIDDEN_NODE_TYPES):
            raise DBMMcpUnsafeSQLException(msg=f"forbidden node: {type(node).__name__}")
        if isinstance(node, exp.Anonymous):
            func_name = (node.name or "").lower()
            if func_name in _DANGEROUS_FUNCTIONS:
                raise DBMMcpUnsafeSQLException(msg=f"forbidden function: {node.name}")

    rewritten_ast, was_rewritten = _rewrite_to_select(root)

    # Spider 分片库名改写：dbname.tablename → dbname_0.tablename（系统库除外）
    if rewrite_spider_dbname:
        _rewrite_spider_db(rewritten_ast)

    return rewritten_ast.sql(dialect="mysql"), was_rewritten


def _rewrite_spider_db(ast: exp.Expression) -> None:
    """将 AST 中所有 dbname.tablename 的库名改写为 dbname{_SPIDER_SHARD_SUFFIX}。

    同时处理：
    - FROM/JOIN 子句中的 Table 节点（dbname.tablename）
    - ON/WHERE/SELECT 等子句中的 Column 节点（dbname.tablename.column）

    系统库（mysql/sys/information_schema/performance_schema/test/infodba_schema）不改写。
    直接原地修改 AST，无返回值。
    """
    # 改写 Table 节点中的 db
    for table in ast.find_all(exp.Table):
        db = table.args.get("db")
        if db and isinstance(db, exp.Identifier):
            original_name = db.this
            if original_name.lower() not in _SPIDER_REWRITE_SKIP_DBS:
                db.set("this", f"{original_name}{_SPIDER_SHARD_SUFFIX}")

    # 改写 Column 节点中的 db（如 mydb.t1.id 中的 mydb）
    for col in ast.find_all(exp.Column):
        db = col.args.get("db")
        if db and isinstance(db, exp.Identifier):
            original_name = db.this
            if original_name.lower() not in _SPIDER_REWRITE_SKIP_DBS:
                db.set("this", f"{original_name}{_SPIDER_SHARD_SUFFIX}")


def _rewrite_to_select(root: exp.Expression) -> Tuple[exp.Expression, bool]:
    """把 UPDATE/DELETE/INSERT...SELECT 改写为等价 SELECT 以便 EXPLAIN。

    - ``SELECT`` / ``UNION`` 等只读查询：原样返回
    - ``UPDATE t [JOIN ...] SET ... WHERE c [ORDER BY] [LIMIT]``
      → ``SELECT * FROM t [JOIN ...] WHERE c [ORDER BY] [LIMIT]``
    - ``DELETE FROM t WHERE c`` / ``DELETE t1 FROM t1, t2 WHERE c`` /
      ``DELETE FROM t1 USING t1, t2 WHERE c`` → ``SELECT * FROM ... WHERE c``
    - ``INSERT INTO t [(...)] SELECT ...`` → 内层 ``SELECT ...``
    - ``INSERT INTO t VALUES (...)`` 拒绝（无可分析的 plan）
    """
    if isinstance(root, exp.Select):
        return root, False

    if isinstance(root, exp.SetOperation):
        # UNION / INTERSECT / EXCEPT 已经是只读查询，直接放行
        return root, False

    if isinstance(root, exp.Update):
        sel = exp.Select().select(exp.Star()).from_(root.args["this"])
        return _attach_where_order_limit(sel, root), True

    if isinstance(root, exp.Delete):
        # `args.get("using")` 在非 USING 形式下可能为 None / False，统一兜底为空列表
        using = root.args.get("using") or []
        if using:
            sel = exp.Select().select(exp.Star()).from_(using[0])
            for extra in using[1:]:
                sel = sel.join(extra)
        else:
            sel = exp.Select().select(exp.Star()).from_(root.args["this"])
        return _attach_where_order_limit(sel, root), True

    if isinstance(root, exp.Insert):
        inner = root.args.get("expression")
        # INSERT ... SELECT 的内层是 Select；INSERT ... SELECT ... UNION ... 是 SetOperation
        if isinstance(inner, (exp.Select, exp.SetOperation)):
            return inner, True
        raise DBMMcpUnsafeSQLException(
            msg=(
                "INSERT/REPLACE VALUES has no meaningful EXPLAIN plan, "
                "please provide an INSERT ... SELECT form instead"
            )
        )

    raise DBMMcpUnsafeSQLException(msg=f"unsupported root: {type(root).__name__}")


def _attach_where_order_limit(sel: exp.Select, src: exp.Expression) -> exp.Select:
    where = src.args.get("where")
    if isinstance(where, exp.Where):
        sel = sel.where(where.this)
    for k in ("order", "limit"):
        v = src.args.get(k)
        if v is not None:
            sel.set(k, v)
    return sel
