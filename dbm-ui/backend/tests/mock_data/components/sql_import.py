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


class SQLSimulationApiMock:
    """
    sql导入的相关mock
    """

    @classmethod
    def grammar_check(cls, *agrs, **kwargs):
        files = kwargs["params"].get("files", None)
        base_check_info = {
            "syntax_fails": None,
            "highrisk_warnings": None,
            "bancommand_warnings": None,
        }

        sql_check_info = {}
        for sql_file in files:
            sql_check_info[sql_file] = base_check_info

        return sql_check_info

    @classmethod
    def parse_sql_tables(cls, *args, **kwargs):
        return [
            {
                "query_id": 1,
                "command": "update",
                "db_name": "test_db",
                "table_name": "test_table",
                "error_line": 0,
            }
        ]

    @classmethod
    def parse_file_statement(cls, *args, **kwargs):
        params = kwargs.get("params") or {}
        files = params.get("files") or []
        include_sql_text = params.get("include_sql_text", False)
        file_name = files[0] if files else "change.sql"
        alter = {"db_name": "db1", "table_name": "t1"}
        if include_sql_text:
            alter["sql_text"] = "ALTER TABLE `t1` ADD COLUMN `foo` INT"
        return {
            "command_counts": {"alter_table": 1},
            "file_command_counts": {file_name: {"alter_table": 1}},
            "alter_tables": [{"file_name": file_name, "alters": [alter]}],
            "drop_tables": [],
            "truncate_tables": [],
        }
