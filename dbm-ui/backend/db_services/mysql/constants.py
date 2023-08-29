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

# 端口最大最小值
SERVER_PORT_LIMIT_MAX = 2 ** 16
SERVER_PORT_LIMIT_MIN = 0

# 默认起始端口
DEFAULT_ORIGIN_PROXY_PORT = 10000
DEFAULT_ORIGIN_MYSQL_PORT = 20000

# 查询库表sql语句
QUERY_SCHEMA_DBS_SQL = (
    "SELECT SCHEMA_NAME from information_schema.SCHEMATA WHERE {db_sts} and SCHEMA_NAME not in {sys_db_list}"
)
QUERY_SCHEMA_TABLES_SQL = (
    "SELECT TABLE_SCHEMA,TABLE_NAME FROM information_schema.TABLES "
    "WHERE TABLE_TYPE='BASE TABLE' AND (TABLE_SCHEMA IN {db_list}) AND {table_sts}"
)
