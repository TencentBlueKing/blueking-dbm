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
import pytest

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpUnsafeIdentifierException, DBMMcpUnsafeSQLException
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_ident, sanitize_select_sql


class TestQuoteIdent:
    """``quote_ident`` 兼容历史含 -/./$/中文 的库表名，仅拒绝控制字符与反引号自身"""

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("db_a", "`db_a`"),
            ("db-a", "`db-a`"),
            ("db.a", "`db.a`"),
            ("a$b", "`a$b`"),
            ("订单库", "`订单库`"),
            ("MixedCase_123", "`MixedCase_123`"),
            ("a" * 64, "`" + "a" * 64 + "`"),
        ],
    )
    def test_pass(self, name, expected):
        assert quote_ident(name) == expected

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "a" * 65,
            "中" * 22,  # 22*3=66 bytes in utf-8
            "has`tick",
            "has\nnl",
            "has\rcr",
            "has\ttab",
            "has\x00nul",
        ],
    )
    def test_reject(self, name):
        with pytest.raises(DBMMcpUnsafeIdentifierException):
            quote_ident(name)


class TestSanitizeSelectSql:
    """``sanitize_select_sql`` 严格白名单 + DML 改写"""

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 1",
            "SELECT * FROM t WHERE id=1",
            "SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
            "SELECT * FROM (SELECT id FROM t) x",
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT 1 UNION SELECT 2",
        ],
    )
    def test_select_pass(self, sql):
        out, rewritten = sanitize_select_sql(sql)
        assert rewritten is False
        assert out  # non-empty

    @pytest.mark.parametrize(
        "sql,expected_select",
        [
            (
                "UPDATE t SET a=1 WHERE id=2",
                "SELECT * FROM t WHERE id = 2",
            ),
            (
                "UPDATE t SET a=1 WHERE id=2 ORDER BY id LIMIT 10",
                "SELECT * FROM t WHERE id = 2 ORDER BY id LIMIT 10",
            ),
            (
                "UPDATE t1 JOIN t2 ON t1.id=t2.id SET t1.x=t2.y WHERE t1.c<10",
                "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id WHERE t1.c < 10",
            ),
            (
                "DELETE FROM t WHERE a IN (1,2,3) LIMIT 100",
                "SELECT * FROM t WHERE a IN (1, 2, 3) LIMIT 100",
            ),
            (
                "DELETE t1 FROM t1, t2 WHERE t1.id=t2.id",
                "SELECT * FROM t1, t2 WHERE t1.id = t2.id",
            ),
            (
                "DELETE FROM t1 USING t1, t2 WHERE t1.id=t2.id",
                "SELECT * FROM t1, t2 WHERE t1.id = t2.id",
            ),
            (
                "INSERT INTO t1 (a,b) SELECT a,b FROM t2 WHERE c<10",
                "SELECT a, b FROM t2 WHERE c < 10",
            ),
            (
                "INSERT INTO t SELECT * FROM s",
                "SELECT * FROM s",
            ),
            (
                "INSERT INTO t (a) SELECT a FROM s WHERE x=1 UNION ALL SELECT a FROM s WHERE x=2",
                "SELECT a FROM s WHERE x = 1 UNION ALL SELECT a FROM s WHERE x = 2",
            ),
        ],
    )
    def test_dml_rewrite(self, sql, expected_select):
        out, rewritten = sanitize_select_sql(sql)
        assert rewritten is True
        assert out == expected_select

    @pytest.mark.parametrize(
        "sql",
        [
            # ANALYZE/EXPLAIN/DESCRIBE 前缀
            "ANALYZE SELECT 1",
            "ANALYZE UPDATE t SET a=1",
            "EXPLAIN SELECT 1",
            "EXPLAIN UPDATE t SET a=1",
            # DDL
            "DROP TABLE t",
            "CREATE TABLE x (a INT)",
            "ALTER TABLE t ADD COLUMN b INT",
            "TRUNCATE TABLE t",
            # 控制 / 元命令
            "CALL p()",
            "KILL 1",
            "FLUSH PRIVILEGES",
            "SET autocommit=0",
            "SET GLOBAL max_connections=100",
            "SHOW TABLES",
            "USE db",
            "BEGIN",
            "COMMIT",
            "GRANT SELECT ON *.* TO 'u'@'%'",
            # 多语句
            "SELECT 1; SELECT 2",
            "SELECT 1; DROP TABLE t",
            # 危险函数
            "SELECT SLEEP(1)",
            "SELECT BENCHMARK(1000, MD5('x'))",
            "SELECT GET_LOCK('x', 1)",
            "SELECT RELEASE_LOCK('x')",
            "SELECT LOAD_FILE('/etc/passwd')",
            # 文件 / 锁
            "SELECT * FROM t INTO OUTFILE '/tmp/x'",
            "SELECT * FROM t INTO DUMPFILE '/tmp/x'",
            "SELECT * FROM t FOR UPDATE",
            "SELECT * FROM t LOCK IN SHARE MODE",
            # INSERT VALUES
            "INSERT INTO t VALUES (1,2)",
            "INSERT INTO t (a) VALUES (1) ON DUPLICATE KEY UPDATE a=a+1",
            "REPLACE INTO t VALUES (1,2)",
            # 空 / 全注释
            "",
            "   ",
            "/* only comment */",
            # NUL 字节
            "SELECT \x00 FROM t",
        ],
    )
    def test_reject(self, sql):
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql(sql)

    def test_hint_preserved_but_normalized(self):
        # MySQL 优化器 hint 不构成安全风险（DRS 走 Go context 超时，
        # MAX_EXECUTION_TIME 等会话变量绕不开）；归一化后字符串本身合法
        out, rewritten = sanitize_select_sql("SELECT /*+ MAX_EXECUTION_TIME(0) */ * FROM t")
        assert rewritten is False
        assert "SELECT" in out
        assert "FROM t" in out

    def test_mysql_executable_comment_blocked(self):
        # MySQL `/*!版本号 ... */` 可执行注释会被 MySQL 真实执行，
        # 但 sqlglot 仅当成普通注释，是经典 AST 校验绕过手法，必须直接拒绝
        for sql in (
            "SELECT /*!50000 SLEEP(1) */",
            "SELECT 1 /*!50000 ; DROP TABLE t */",
            "SELECT * /*!50000 INTO OUTFILE '/tmp/x' */ FROM t",
            "SELECT /*! 1 */ FROM t",
        ):
            with pytest.raises(DBMMcpUnsafeSQLException):
                sanitize_select_sql(sql)

    def test_multistatement_via_comment_trick(self):
        # 即使用注释 / 换行掩护第二条语句也会被 1-statement 校验拒绝
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql("SELECT 1 /* trick */; DROP TABLE t")
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql("SELECT 1 -- trick\n; DROP TABLE t")

    @pytest.mark.parametrize(
        "sql",
        [
            # 用块注释拆危险关键词，绕过普通 \\bA\\s+B\\b 正则
            "SELECT * FROM t FOR/**/UPDATE",
            "SELECT * FROM t LOCK/**/IN/**/SHARE/**/MODE",
            "SELECT 1 INTO/**/OUTFILE '/tmp/x'",
            "SELECT 1 INTO/**/DUMPFILE '/tmp/x'",
            # 函数名前后插注释（剥后由黑名单或 AST 命中）
            "SELECT/**/SLEEP/**/(0)",
            "SELECT SLEEP/**/(0)",
            # 大小写混淆 + 制表符 / 换行作为分隔
            "SELECT 1\tINTO\tOUTFILE\t'/tmp/x'",
            "select 1 into\nOutfile\n'/tmp/x'",
        ],
    )
    def test_comment_split_keyword_blocked(self, sql):
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            # 危险函数藏在子查询 / CTE / IF / CASE / 窗口中
            "SELECT * FROM (SELECT SLEEP(1)) t",
            "SELECT 1 FROM dual WHERE 1=(SELECT SLEEP(1))",
            "SELECT 1 ORDER BY (SELECT SLEEP(1))",
            "SELECT 1 GROUP BY (SELECT SLEEP(1)) HAVING 1",
            "SELECT 1 HAVING SLEEP(1)",
            "WITH x AS (SELECT SLEEP(1) AS y) SELECT * FROM x",
            "SELECT IF(1=1, SLEEP(1), 0)",
            "SELECT CASE WHEN 1=1 THEN SLEEP(1) END",
            "SELECT (SELECT GET_LOCK('x', 1))",
            "SELECT SUM(SLEEP(1)) OVER () FROM t",
            # 改写后的 DML 也要扫到内部危险函数
            "UPDATE t SET a=SLEEP(1) WHERE id=0",
            "DELETE FROM t WHERE SLEEP(1)",
            # 其余危险函数
            "SELECT RELEASE_ALL_LOCKS()",
            "SELECT MASTER_POS_WAIT('m', 0)",
            "SELECT WAIT_FOR_EXECUTED_GTID_SET('x')",
            "SELECT SYS_EXEC('id')",
            "SELECT SYS_EVAL('id')",
        ],
    )
    def test_dangerous_function_in_subexpressions_blocked(self, sql):
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            # tokenizer 异常（反引号未闭合等）也必须被吃掉并转成统一异常
            "SELECT * FROM `t`extra`",
            "SELECT 'unterminated",
            "SELECT `unterminated",
        ],
    )
    def test_tokenizer_error_treated_as_unsafe(self, sql):
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql(sql)

    @pytest.mark.parametrize(
        "sql",
        [
            # 字符串里出现"看似危险"的关键词不应被误杀
            "SELECT 'INTO OUTFILE /tmp/x' AS x",
            "SELECT 'SLEEP(1)' AS x",
            "SELECT '-- LOAD_FILE(/etc/passwd)' AS x",
            "SELECT 'GET_LOCK(x,1)' AS x",
            'SELECT "FOR UPDATE in string" AS x',
            # 反引号包裹关键字作为别名也合法
            "SELECT 1 AS `select`",
            "SELECT 1 AS `for update`",
        ],
    )
    def test_string_literal_with_dangerous_lookalike_passes(self, sql):
        out, rewritten = sanitize_select_sql(sql)
        assert rewritten is False
        assert out

    @pytest.mark.parametrize(
        "sql",
        [
            # 其余在白名单根类型外的语句
            "ANALYZE TABLE t",
            "OPTIMIZE TABLE t",
            "REPAIR TABLE t",
            "CHECKSUM TABLE t",
            "HANDLER t OPEN",
            "PREPARE s FROM 'SELECT 1'",
            "EXECUTE s",
            "DEALLOCATE PREPARE s",
            "DO SLEEP(1)",
            "LOAD DATA INFILE '/tmp/x' INTO TABLE t",
            "LOAD INDEX INTO CACHE t",
            "RESET MASTER",
            "PURGE BINARY LOGS BEFORE NOW()",
            "SHUTDOWN",
            "XA START 'tx'",
            "ROLLBACK",
            "SAVEPOINT s1",
            "LOCK TABLES t WRITE",
            "UNLOCK TABLES",
            "EXPLAIN ANALYZE SELECT 1",
            "EXPLAIN FORMAT=JSON SELECT 1",
            "DESCRIBE t",
            "INSERT INTO t SET a=1",
        ],
    )
    def test_other_admin_or_unsupported_statements_rejected(self, sql):
        with pytest.raises(DBMMcpUnsafeSQLException):
            sanitize_select_sql(sql)
