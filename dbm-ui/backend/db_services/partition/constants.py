"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import ugettext_lazy as _

SWAGGER_TAG = _("分区管理")

PARTITION_NO_EXECUTE_CODE = 51029  # 分区执行无需发起

# 查询唯一索引的SQL语句
QUERY_UNIQUE_FIELDS_SQL = (
    "select distinct table_schema, table_name, index_name, "
    "group_concat(distinct column_name order by seq_in_index) as column_list "
    "from information_schema.statistics  where {table_sts} and {db_sts} and non_unique = 0 "
    "group by table_name, index_name;"
)
# 查询所有表的所有字段类型
QUERY_DATABASE_FIELD_TYPE = (
    "select table_schema, table_name, column_name, column_type "
    "from information_schema.columns where {table_sts} and {db_sts}"
)


class PartitionTypeEnum(str, StructuredEnum):
    INT = EnumField("int", _("整型"))
    DATETIME = EnumField("datetime", _("日期类型"))
    TIMESTAMP = EnumField("timestamp", _("时间戳类型"))
