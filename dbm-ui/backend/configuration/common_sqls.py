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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType

MYSQL_COMMON_SQL_STATEMENTS = [
    {"name": _("查询链接信息"), "sql": """select * from information_schema.processlist limit 1;"""},
    {"name": _("查看主从信息"), "sql": """show slave status;"""},
]

SQLSERVER__COMMON_SQL_STATEMENTS = []

DB_TYPE__COMMON_SQL_MAP = {
    DBType.MySQL.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.TenDBCluster.value: MYSQL_COMMON_SQL_STATEMENTS,
    DBType.Sqlserver.value: SQLSERVER__COMMON_SQL_STATEMENTS,
}
