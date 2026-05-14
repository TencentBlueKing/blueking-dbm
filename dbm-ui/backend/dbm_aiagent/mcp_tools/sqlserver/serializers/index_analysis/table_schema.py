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
from rest_framework import serializers

from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.index_analysis.common import (
    IndexAnalysisBaseInputSerializer,
    PerTableResultBaseSerializer,
)


class SQLServerTableSchemaInputSerializer(IndexAnalysisBaseInputSerializer):
    pass


class _ColumnSerializer(serializers.Serializer):
    column_id = serializers.IntegerField(help_text=_("列 ID"))
    column_name = serializers.CharField(help_text=_("列名"))
    type_name = serializers.CharField(help_text=_("类型名（不含长度/精度）"))
    type_display = serializers.CharField(help_text=_("拼好长度/精度的类型展示，例如 NVARCHAR(50)"))
    max_length = serializers.IntegerField(help_text=_("最大长度（字节，varchar=-1 表示 MAX）"))
    precision = serializers.IntegerField(help_text=_("精度"))
    scale = serializers.IntegerField(help_text=_("小数位数"))
    is_nullable = serializers.IntegerField(help_text=_("是否可空 1/0"))
    is_identity = serializers.IntegerField(help_text=_("是否 IDENTITY 1/0"))
    is_computed = serializers.IntegerField(help_text=_("是否计算列 1/0"))
    is_persisted = serializers.IntegerField(help_text=_("计算列是否持久化 1/0"), allow_null=True)
    computed_definition = serializers.CharField(help_text=_("计算列表达式定义"), allow_null=True, allow_blank=True)
    is_rowguidcol = serializers.IntegerField(help_text=_("是否 ROWGUIDCOL 1/0"))
    is_rowversion = serializers.IntegerField(help_text=_("是否 rowversion/timestamp 1/0"))
    default_definition = serializers.CharField(help_text=_("默认值约束表达式"), allow_null=True, allow_blank=True)
    collation = serializers.CharField(help_text=_("排序规则"), allow_null=True, allow_blank=True)


class _PrimaryKeySerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("主键约束名"))
    type = serializers.CharField(help_text=_("索引类型描述（如 CLUSTERED）"))
    columns = serializers.ListField(child=serializers.CharField(), help_text=_("主键列（按 key_ordinal 排序）"))


class _ForeignKeySerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("外键名"))
    referenced_schema = serializers.CharField(help_text=_("被引用表 schema"))
    referenced_table = serializers.CharField(help_text=_("被引用表名"))
    on_delete = serializers.CharField(help_text=_("删除联动行为"), allow_null=True, allow_blank=True)
    on_update = serializers.CharField(help_text=_("更新联动行为"), allow_null=True, allow_blank=True)
    is_disabled = serializers.IntegerField(help_text=_("是否禁用 1/0"))
    is_not_trusted = serializers.IntegerField(help_text=_("是否未经信任 1/0"))
    columns = serializers.ListField(child=serializers.CharField(), help_text=_("本表参与外键的列（按列序）"))
    referenced_columns = serializers.ListField(child=serializers.CharField(), help_text=_("被引用表参与外键的列（按列序）"))


class _TableSchemaResultSerializer(PerTableResultBaseSerializer):
    """单表结果项：在公共字段（table/status/error）之上追加业务字段。"""

    columns = _ColumnSerializer(many=True, help_text=_("列清单；status 非 ok 时为空数组"), required=False)
    primary_key = _PrimaryKeySerializer(allow_null=True, help_text=_("主键信息；无主键或非 ok 时为 null"), required=False)
    foreign_keys = _ForeignKeySerializer(many=True, help_text=_("外键清单；status 非 ok 时为空数组"), required=False)


class SQLServerTableSchemaOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))
    results = _TableSchemaResultSerializer(many=True, help_text=_("每张表的结构结果，顺序与入参 tables 一致"))
