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

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import MYSQL_SIMULATION_DOMAIN


class _SQLSimulationApi(BaseApi):
    MODULE = _("SQL模拟执行")
    BASE = MYSQL_SIMULATION_DOMAIN

    def __init__(self):
        self.grammar_check = self.generate_data_api(
            method="POST",
            url="/syntax/check/file",
            description=_("sql语法检查"),
        )

        self.sqlserver_grammar_check = self.generate_data_api(
            method="POST",
            url="/sqlserver/syntax/check/file",
            description=_("sql语法检查-sqlserver专属"),
        )

        # 使用示例：
        # {
        #     "cluster_type": "mysql",
        #     "versions": ["5.7"],
        #     "sqls": ["create database `test001`  "]
        # }
        self.syntax_check_sql = self.generate_data_api(
            method="POST",
            url="/syntax/check/sql",
            description=_("sql string 语法检查"),
        )
        # 使用示例：
        # {
        #     "cluster_type": "mysql",
        #     "sql": "UPDATE `db1`.`t1` SET a=1"
        # }
        # 返回 data: [{"query_id":1,"command":"update","db_name":"db1","table_name":"t1","error_line":0}, ...]
        self.parse_sql_tables = self.generate_data_api(
            method="POST",
            url="/syntax/parse/sql/statement",
            description=_("解析单条 SQL string 为 ParseIncludeTableBase 列表"),
        )
        # 使用示例：
        # {
        #     "sql": "SELECT * FROM `db`.`t1` WHERE (id > 1)",
        #     "judge_subquery_diff_table": true
        # }
        # 返回 data: {"is_inject": false, "reason": ""}
        self.syntax_check_inject = self.generate_data_api(
            method="POST",
            url="/syntax/check/inject",
            description=_("sql 注入检查"),
        )
        self.mysql_simulation = self.generate_data_api(
            method="POST",
            url="/mysql/simulation",
            description=_("容器化SQL模拟执行"),
        )
        self.query_simulation_task = self.generate_data_api(
            method="POST",
            url="/mysql/task",
            description=_("查询模拟执行任务状态也"),
        )
        self.spider_simulation = self.generate_data_api(
            method="POST",
            url="/spider/simulation",
            description=_("容器化SQL模拟执行"),
        )
        self.query_semantic_result = self.generate_data_api(
            method="POST",
            url="/simulation/task/file",
            description=_("查询语义执行结果"),
        )
        self.query_relation_dbs_from_sqlfile = self.generate_data_api(
            method="POST",
            url="/syntax/parse/file/relation/db",
            description=_("查询语义执行结果"),
        )
        # 使用示例：
        # {
        #     "path": "mysql/sqlfile/123",
        #     "files": ["change.sql"],
        #     "include_sql_text": false
        # }
        self.parse_file_statement = self.generate_data_api(
            method="POST",
            url="/syntax/parse/file/statement",
            description=_("按文件解析 SQL 语句类型与 ALTER/DROP/TRUNCATE 表"),
        )


SQLSimulationApi = _SQLSimulationApi()
