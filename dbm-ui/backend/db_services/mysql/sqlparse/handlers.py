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

import sqlparse

from backend.utils.md5 import count_md5


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
