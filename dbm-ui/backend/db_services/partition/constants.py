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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum

SWAGGER_TAG = _("分区管理")

PARTITION_NO_EXECUTE_CODE = 51029  # 分区执行无需发起

# 查询唯一索引的SQL语句
QUERY_UNIQUE_FIELDS_SQL = (
    "select distinct table_schema as table_schema, table_name as table_name, index_name as index_name, "
    "group_concat(distinct column_name order by seq_in_index) as column_list "
    "from information_schema.statistics  where {table_sts} and {db_sts} and non_unique = 0 "
    "group by table_name, index_name;"
)
# 查询所有表的所有字段类型
QUERY_DATABASE_FIELD_TYPE = (
    "select table_schema as table_schema, table_name as table_name, "
    "column_name as column_name, column_type as column_type "
    "from information_schema.columns where {table_sts} and {db_sts}"
)

# 查询表信息 是否已经是分区表
Query_Tables_info_SQL = (
    "select TABLE_SCHEMA, TABLE_NAME, CREATE_OPTIONS " "from information_schema.tables where {condition_sts}"
)

Query_shard_info_SQL = (
    "SELECT Server_name, Host, Port "
    "FROM mysql.servers "
    "WHERE Server_name LIKE 'SPT%' AND Server_name NOT LIKE 'SPT_SLAVE%' "
    "ORDER BY Server_name"
)

Query_partition_info_SQL = (
    "SELECT PARTITION_NAME, PARTITION_DESCRIPTION "
    "FROM information_schema.partitions "
    "WHERE TABLE_SCHEMA='{dbname}' AND TABLE_NAME='{tb}' "
    "ORDER BY PARTITION_DESCRIPTION ASC"
)


class PartitionTypeEnum(StrStructuredEnum):
    INT = EnumField("int", _("整型"))
    DATETIME = EnumField("datetime", _("日期类型"))
    TIMESTAMP = EnumField("timestamp", _("时间戳类型"))
