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

import logging
import re

import sqlparse
from django.utils.translation import gettext as _

from backend.db_services.mysql.sqlparse.exceptions import SQLParseBaseException
from backend.flow.consts import SYSTEM_DBS
from backend.utils.md5 import count_md5

logger = logging.getLogger("root")

LIMIT = 1000


class SQLParseHandler:
    def __init__(self):
        self.sql_items = []
        self.commands = set()
        self.tables = set()
        self.table_token = None

    def parse_tokens(self, tokens):
        """
        parse token，用于递归解析
        """
        self.table_token = False
        for token in tokens:
            if token.ttype in [sqlparse.tokens.DDL, sqlparse.tokens.DML]:
                self.commands.add(token.value.upper())

            # 提取表名
            if token.is_keyword:
                if token.value.upper() in ["FROM", "UPDATE", "INTO", "TABLE", "JOIN"]:
                    self.table_token = True
            elif self.table_token:
                sub_tokens = getattr(token, "tokens", [])
                if isinstance(token, (sqlparse.sql.Identifier, sqlparse.sql.IdentifierList)):
                    if not any(
                        isinstance(x, sqlparse.sql.Parenthesis) or "SELECT" in x.value.upper() for x in sub_tokens
                    ):
                        fr = "".join(str(j) for j in token if j.value not in {"as", "\n"})
                        for t in re.findall(r"(?:\w+\.\w+|\w+)\s+\w+|(?:\w+\.\w+|\w+)", fr):
                            self.tables.add(t.split()[0])
                            self.table_token = False
                elif isinstance(token, sqlparse.sql.Function):
                    for _token in sub_tokens:
                        if isinstance(_token, sqlparse.sql.Identifier):
                            self.tables.add(_token.value)
                            self.table_token = False

            elif token.ttype == sqlparse.tokens.Punctuation:
                self.table_token = False

            if token.is_group:
                self.parse_tokens(token.tokens)
            else:
                if token.ttype.parent == sqlparse.tokens.Token.Literal.String:
                    self.sql_items.append("'?'")
                elif token.ttype.parent == sqlparse.tokens.Token.Literal.Number:
                    self.sql_items.append("?")
                else:
                    self.sql_items.append(token.value)

    def parse_sql(self, sql: str) -> dict:
        """
        解析 SQL
        """
        parsed_sqls = sqlparse.parse(sql)
        if len(parsed_sqls) == 0:
            return {}
        tokens = sqlparse.parse(sql)[0].tokens
        self.parse_tokens(tokens=tokens)
        digest_sql = " ".join(self.sql_items)
        for char in ["\r", "\n", "\t"]:
            digest_sql.replace(char, " ")
            sql.replace(char, " ")
        digest_sql = re.sub(r"\s+", " ", digest_sql)
        sql = re.sub(r"\s+", " ", sql)
        query_digest_md5 = count_md5(digest_sql)
        return {
            "command": ",".join(sorted(self.commands)),
            "query_string": sql.strip(" "),
            "query_digest_text": digest_sql.strip(" "),
            "query_digest_md5": query_digest_md5,
            "table_name": ",".join(sorted(self.tables)),
            "query_length": len(sql),
        }

    def parse_select_statement(self, sql: str, need_keywords: list = None):
        """判断并解析select语句"""
        # 默认select语句要有limit
        need_keywords = need_keywords or ["LIMIT"]

        def parse_show_desc_tokens(tokens):
            """允许特殊SQL语句"""
            # sql语句白名单
            allowed_statements = [
                "status",
                "desc",
                "describe",
                "use",
                "show databases",
                "show processlist",
                "show slave status",
                "show tables",
                "show create table",
                "show index",
                "show variables",
            ]
            tokens = [token.value.lower() for token in tokens if not token.is_whitespace]
            for allowed in allowed_statements:
                if " ".join(tokens).startswith(allowed):
                    return True
            return False

        def parse_select_tokens(statement, tokens):
            """解析是否为合法的select语句和包含对应的keyword"""
            is_select: bool = False
            keywords: list = []
            for token in tokens:
                # 这里只用检查外层包含keyword. 子查询可以忽略，因为不体现最后的输出数据
                if token.ttype is sqlparse.tokens.DML and token.value.upper() == "SELECT":
                    is_select = True
                elif token.ttype is sqlparse.tokens.Keyword:
                    keywords.append(token.value.upper())
                    # 如果是limit命令，上限为1000
                    if token.value.upper() == "LIMIT":
                        limit = statement.token_next(statement.token_index(token))[1]
                        if not limit or not limit.value.isdigit() or int(limit.value) > LIMIT:
                            raise SQLParseBaseException(_("LIMIT限制为空或者超过1000"))

            is_contain_keywords = set(keywords).issuperset(set(need_keywords))
            return is_select, is_contain_keywords

        # 一次性只解析一条sql语句
        parsed_sqls = sqlparse.parse(sql)
        if len(parsed_sqls) > 1:
            raise SQLParseBaseException(_("请保证一次只解析一条select语句"))

        # 允许特定查询语句
        if parse_show_desc_tokens(parsed_sqls[0].tokens):
            return

        # 判断解析表结构，不允许查询系统表
        dbs = [table.split(".")[0] for table in self.parse_sql(sql)["table_name"].split(",")]
        if dbs and set(dbs).intersection(set(SYSTEM_DBS)):
            raise SQLParseBaseException(_("不允许查询以下系统库表:{}").format(SYSTEM_DBS))

        valid_select = all(parse_select_tokens(parsed_sqls[0], parsed_sqls[0].tokens))
        if not valid_select:
            raise SQLParseBaseException(_("SQL语句不为查询语句，或者不包含{}命令").format(need_keywords))
