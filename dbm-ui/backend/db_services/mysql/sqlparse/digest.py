import hashlib
import re
from typing import List, Optional

import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Parenthesis, Where
from sqlparse.tokens import DML, Keyword, Literal, Number, String


def _normalize_sql(sql: str, stmt=None) -> str:
    """将 SQL 中的字面值替换为占位符 ?，生成 SQL 指纹"""
    if stmt is None:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return sql
        stmt = parsed[0]

    # 先用 sqlparse 做基本格式化：去除多余空格、换行
    normalized = sqlparse.format(
        str(stmt),
        strip_comments=True,
        strip_whitespace=True,
    )

    # 再次解析格式化后的 SQL
    parsed = sqlparse.parse(normalized)
    if not parsed:
        return normalized
    stmt = parsed[0]

    tokens = list(stmt.flatten())
    result = []
    prev_is_placeholder = False

    for token in tokens:
        # 替换数字字面值
        if token.ttype in (
            Number.Integer,
            Number.Float,
            Number.Hexadecimal,
            Literal.Number.Integer,
            Literal.Number.Float,
        ):
            if not prev_is_placeholder:
                result.append("?")
                prev_is_placeholder = True
            continue

        # 替换字符串字面值
        if token.ttype in (
            String.Single,
            String.Symbol,
            Literal.String.Single,
        ):
            if not prev_is_placeholder:
                result.append("?")
                prev_is_placeholder = True
            continue

        # 处理 IN (...) 中的多个占位符，合并为一个 ?
        # 这个在后处理中完成

        prev_is_placeholder = False
        result.append(token.value)

    text = "".join(result)

    # 合并 IN (?, ?, ?, ...) 为 IN (?)
    text = re.sub(r"\bIN\s*\(\s*\?(?:\s*,\s*\?)*\s*\)", "IN (?)", text, flags=re.IGNORECASE)

    # 合并 VALUES (?, ?, ...), (?, ?, ...) 为 VALUES (?)
    values_pattern = r"\bVALUES\s*\(\s*\?(?:\s*,\s*\?)*\s*\)(?:\s*,\s*\(\s*\?(?:\s*,\s*\?)*\s*\))*"
    text = re.sub(values_pattern, "VALUES (?)", text, flags=re.IGNORECASE)

    # 合并连续空白
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _extract_command(sql: str, stmt=None) -> str:
    """提取 SQL 命令类型，如 SELECT, INSERT, UPDATE, DELETE 等"""
    if stmt is None:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return "OTHER"
        stmt = parsed[0]
    for token in stmt.tokens:
        if token.ttype is DML:
            return token.value.upper()
        # 处理非 DML 语句，如 ALTER, CREATE, DROP, SHOW 等
        if token.ttype is Keyword or token.ttype in Keyword:
            return token.value.upper()
    return "OTHER"


# 期望后面紧跟表名的关键字集合
_TABLE_KEYWORDS = frozenset(
    {
        "FROM",
        "JOIN",
        "INNER JOIN",
        "LEFT JOIN",
        "RIGHT JOIN",
        "FULL JOIN",
        "CROSS JOIN",
        "LEFT OUTER JOIN",
        "RIGHT OUTER JOIN",
        "FULL OUTER JOIN",
        "STRAIGHT_JOIN",
        "INTO",
        "TABLE",
        "UPDATE",
    }
)


def _get_table_name(identifier: Identifier) -> Optional[str]:
    """从 Identifier 中获取真实表名（去掉别名），跳过子查询"""
    if any(t.ttype is DML for t in identifier.flatten()):
        return None
    name = identifier.get_real_name()
    if name is None:
        return None
    parent = identifier.get_parent_name()
    return f"{parent}.{name}" if parent else name


def _collect_from_identifier(token, tables: set) -> None:
    """从 Identifier 或 IdentifierList 中收集表名到 tables 集合"""
    if isinstance(token, IdentifierList):
        for ident in token.get_identifiers():
            _collect_from_identifier(ident, tables)
    elif isinstance(token, Identifier):
        name = _get_table_name(token)
        if name:
            tables.add(name)


def _walk_token_tree(token_list, tables: set) -> None:
    """递归遍历 token 树，在关键字后提取表名"""
    idx = 0
    tokens = token_list.tokens
    length = len(tokens)

    while idx < length:
        token = tokens[idx]

        # 递归进入括号（子查询）和 WHERE 子句
        if isinstance(token, (Parenthesis, Where)):
            _walk_token_tree(token, tables)
            idx += 1
            continue

        # 检测"期望表名"的关键字（DML 中的 UPDATE 或其他关键字）
        is_table_kw = False
        if token.ttype is DML and token.value.upper() == "UPDATE":
            is_table_kw = True
        elif token.ttype is Keyword and token.value.upper() in _TABLE_KEYWORDS:
            is_table_kw = True

        if is_table_kw:
            # 向后跳过空白，取紧跟的标识符
            nxt_idx = idx + 1
            while nxt_idx < length and tokens[nxt_idx].is_whitespace:
                nxt_idx += 1
            if nxt_idx < length:
                _collect_from_identifier(tokens[nxt_idx], tables)
                idx = nxt_idx + 1
                continue

        # Identifier 可能嵌套子查询，递归检查
        if isinstance(token, Identifier) and any(t.ttype is DML for t in token.flatten()):
            _walk_token_tree(token, tables)

        idx += 1


def _format_table_names(tables: set, default_db: str) -> List[str]:
    """处理表名：去掉反引号，没有库名前缀的表名加上 default_db"""
    result = set()
    for table in tables:
        clean_name = table.replace("`", "")
        if "." not in clean_name:
            clean_name = f"{default_db}.{clean_name}"
        result.add(clean_name)
    return sorted(result)


def _extract_table_names(sql: str, default_db: str, stmt=None) -> List[str]:
    """从 SQL 中提取表名，没有库名前缀时用 default_db 拼接"""
    if stmt is None:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return []
        stmt = parsed[0]

    tables: set = set()
    _walk_token_tree(stmt, tables)
    return _format_table_names(tables, default_db)


def generate_sql_fingerprint(sql: str, default_db: str = "") -> dict:
    """
    生成 MySQL SQL 指纹

    Args:
        sql: 原始 SQL 语句
        default_db: 默认数据库名，当表名没有库名前缀时使用

    Returns:
        dict: 包含以下字段：
            - command: SQL 命令类型 (SELECT, INSERT, UPDATE, DELETE 等)
            - query_digest_text: SQL 指纹文本（字面值被替换为 ?）
            - query_digest_md5: SQL 指纹的 MD5 哈希值
            - table_names: 去重后的表名列表（包含库名前缀）
    """
    # 只解析一次原始 SQL，将 stmt 传给各子函数复用
    parsed = sqlparse.parse(sql)
    stmt = parsed[0] if parsed else None

    # 提取命令类型
    command = _extract_command(sql, stmt)

    # 生成 SQL 指纹（内部对格式化后的 SQL 仍需二次解析，但省去了对原始 SQL 的重复解析）
    query_digest_text = _normalize_sql(sql, stmt)

    # 计算 MD5
    query_digest_md5 = hashlib.md5(query_digest_text.encode("utf-8")).hexdigest()

    # 提取表名
    table_names = _extract_table_names(sql, default_db, stmt)

    return {
        "command": command,
        "query_digest_text": query_digest_text,
        "query_digest_md5": query_digest_md5,
        "table_names": table_names,
        "query_len": len(sql),
    }


if __name__ == "__main__":
    test_cases = [
        (
            "SELECT a.id, b.name FROM users a JOIN orders b ON a.id = b.user_id "
            "WHERE a.age > 18 AND b.status = 'active'",
            "test_db",
        ),
        (
            "INSERT INTO `test_db`.`users` (name, age, email) VALUES "
            "('Alice', 25, 'alice@example.com'), ('Bob', 30, 'bob@example.com')",
            "default_db",
        ),
        ("UPDATE users SET name = 'test', age = 20 WHERE id = 100", "my_db"),
        ("DELETE FROM orders WHERE order_id IN (1, 2, 3, 4, 5)", "my_db"),
        ("SELECT * FROM db1.table1 t1 JOIN table2 t2 ON t1.id = t2.fk_id " "WHERE t1.status = 'ok'", "default_db"),
        (
            "SELECT id FROM users WHERE name = 'test' AND id IN " "(SELECT user_id FROM orders WHERE amount > 100)",
            "my_db",
        ),
    ]

    for sql, db in test_cases:
        result = generate_sql_fingerprint(sql, db)
        print(f"SQL:  {sql}")
        print(f"Command:   {result['command']}")
        print(f"Digest:    {result['query_digest_text']}")
        print(f"MD5:       {result['query_digest_md5']}")
        print(f"Tables:    {result['table_names']}")
        print("-" * 100)
