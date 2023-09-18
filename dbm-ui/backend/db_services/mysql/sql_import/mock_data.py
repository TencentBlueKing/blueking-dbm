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
from django.utils.translation import ugettext_lazy as _

SQL_GRAMMAR_CHECK_REQUEST_DATA = {"sql_content": "select * from user where user.id = 1", "sql_file": None}
SQL_GRAMMAR_CHECK_RESPONSE_DATA = {
    "struct_update_202110102.sql": {
        "syntax_fails": None,
        "highrisk_warnings": [
            {
                "line": 1,
                "command_type": "drop_table",
                "sqltext": "DROP TABLE IF EXISTS `mem_chr_task_pass`;",
                "warn_info": _("存在高危命令:drop_table"),
            }
        ],
        "bancommand_warnings": None,
    },
}

SQL_SEMANTIC_CHECK_REQUEST_DATA = {
    "created_by": "admin",
    "bk_biz_id": "2005000194",
    "ticket_type": "MYSQL_SEMANTIC_CHECK",
    "charset": "default",
    "cluster_ids": [1, 2],
    "execute_sql_files": ["bar.sql", "foo.sql"],
    "execute_db_infos": [
        {"dbnames": ["db_log%"], "ignore_dbnames": ["db1", "db2"]},
        {"dbnames": ["user_log%"], "ignore_dbnames": ["user1", "user2"]},
    ],
    "ticket_mode": {"mode": "timer", "trigger_time": "2022-11-11 08:18:18.314432"},
    "import_mode": "file",
    "backup": [
        {"backup_on": "master", "db_patterns": ["db1%", "db2%"], "table_patterns": ["tb_role%", "tb_mail%", "*"]}
    ],
}
SQL_SEMANTIC_CHECK_RESPONSE_DATA = {"root_id": 278179279321, "node_id": "e1122c985095d46b885c9869f81c5c22e"}

SQL_TICKET_AUTO_COMMIT_REQUEST_DATA = {"root_id": 12232133211, "is_auto_commit": True}

USER_SEMANTIC_LIST_REQUEST_DATA = {"user": "admin", "cluster_type": "mysql"}
USER_SEMANTIC_LIST_RESPONSE_DATA = {
    "semantic_list": [
        {"root_id": 1231613324894, "created_at": "2011/11/11", "status": "RUNNING"},
        {"root_id": 4523161321294, "created_at": "2011/11/12", "status": "RUNNING"},
        {"root_id": 6123161114894, "created_at": "2011/11/13", "status": "RUNNING"},
    ]
}

DELETE_USER_SEMANTIC_LIST_REQUEST_DATA = {"task_ids": ["1", "2", "3"]}

REVOKE_SEMANTIC_CHECK_REQUEST_DATA = {"root_id": 278179279321}
REVOKE_SEMANTIC_CHECK_RESPONSE_DATA = {"result": True, "message": None, "data": None}

SEMANTIC_SQL_FILES = {
    "semantic_data": {
        "created_by": "admin",
        "bk_biz_id": 3,
        "ticket_type": "TENDBCLUSTER_SEMANTIC_CHECK",
        "charset": "default",
        "path": "mysql/sqlfile",
        "cluster_ids": [63],
        "highrisk_warnings": "",
        "ticket_mode": {"mode": "manual", "trigger_time": ""},
        "import_mode": "file",
        "backup": [],
        "uid": "202308306822cd",
        "blueking_language": "en",
        "execute_sql_files": ["xxtestxxx.sql"],
        "execute_db_infos": [{"dbnames": ["test"], "ignore_dbnames": []}],
    },
    "import_mode": "file",
    "sql_data_ready": True,
}
