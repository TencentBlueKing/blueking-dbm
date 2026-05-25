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


class SQLServerTableIndexesInputSerializer(IndexAnalysisBaseInputSerializer):
    pass


class _IndexKeyColumnSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("列名"))
    ordinal = serializers.IntegerField(help_text=_("键序（key_ordinal）"))
    is_descending = serializers.BooleanField(help_text=_("是否降序键"))


class _IndexIncludedColumnSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("INCLUDE 列名"))


class _IndexItemSerializer(serializers.Serializer):
    index_id = serializers.IntegerField(help_text=_("索引 ID"))
    index_name = serializers.CharField(help_text=_("索引名"), allow_null=True, allow_blank=True)
    type_id = serializers.IntegerField(help_text=_("索引类型 ID"))
    type_desc = serializers.CharField(help_text=_("索引类型描述"))
    is_unique = serializers.IntegerField(help_text=_("是否唯一 1/0"))
    is_primary_key = serializers.IntegerField(help_text=_("是否主键 1/0"))
    is_unique_constraint = serializers.IntegerField(help_text=_("是否唯一约束 1/0"))
    is_disabled = serializers.IntegerField(help_text=_("是否禁用 1/0"))
    has_filter = serializers.IntegerField(help_text=_("是否过滤索引 1/0"))
    filter_definition = serializers.CharField(help_text=_("过滤索引的过滤条件"), allow_null=True, allow_blank=True)
    fill_factor = serializers.IntegerField(help_text=_("填充因子"))
    is_padded = serializers.IntegerField(help_text=_("是否填充 1/0"))
    approx_rows = serializers.IntegerField(help_text=_("索引第一个分区的近似行数"))
    data_compression = serializers.CharField(
        help_text=_("数据压缩状态 NONE/ROW/PAGE/COLUMNSTORE 等"), allow_null=True, allow_blank=True
    )
    key_columns = _IndexKeyColumnSerializer(many=True, help_text=_("键列（按 key_ordinal 排序）"))
    included_columns = _IndexIncludedColumnSerializer(many=True, help_text=_("INCLUDE 列"))


class _TableIndexesResultSerializer(PerTableResultBaseSerializer):
    indexes = _IndexItemSerializer(many=True, help_text=_("索引清单；status 非 ok 时为空数组"), required=False)
    index_count = serializers.IntegerField(help_text=_("索引数量；status 非 ok 时为 0"), required=False)


class SQLServerTableIndexesOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))
    results = _TableIndexesResultSerializer(many=True, help_text=_("每张表的索引结果，顺序与入参 tables 一致"))
