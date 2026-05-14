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


class SQLServerIndexFragmentationInputSerializer(IndexAnalysisBaseInputSerializer):
    min_page_count = serializers.IntegerField(
        help_text=_("仅返回 page_count >= 该阈值的索引；默认 1000；" "0 表示不过滤。业界经验：page_count<1000 的索引碎片对实际性能基本无影响"),
        required=False,
        default=1000,
        min_value=0,
    )


class _IndexFragItemSerializer(serializers.Serializer):
    index_id = serializers.IntegerField(help_text=_("索引 ID"))
    index_name = serializers.CharField(help_text=_("索引名"), allow_null=True, allow_blank=True)
    index_type_desc = serializers.CharField(help_text=_("索引类型描述"))
    alloc_unit_type = serializers.CharField(help_text=_("分配单元类型，如 IN_ROW_DATA / LOB_DATA"))
    partition_number = serializers.IntegerField(help_text=_("分区号"))
    avg_fragmentation_pct = serializers.FloatField(help_text=_("平均碎片率（%）"))
    fragment_count = serializers.IntegerField(help_text=_("碎片数量"), allow_null=True)
    avg_fragment_size_pages = serializers.FloatField(help_text=_("平均碎片大小（页）"), allow_null=True)
    page_count = serializers.IntegerField(help_text=_("页数（决定是否值得维护）"))
    record_count = serializers.IntegerField(help_text=_("记录数"), allow_null=True)


class _IndexFragResultSerializer(PerTableResultBaseSerializer):
    indexes = _IndexFragItemSerializer(many=True, help_text=_("各索引碎片信息；status 非 ok 时为空数组"), required=False)
    row_count = serializers.IntegerField(help_text=_("返回行数；status 非 ok 时为 0"), required=False)


class SQLServerIndexFragmentationOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    scan_mode = serializers.CharField(help_text=_("扫描模式（固定 LIMITED）"))
    min_page_count = serializers.IntegerField(help_text=_("过滤的最小页数阈值"))
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))
    results = _IndexFragResultSerializer(many=True, help_text=_("每张表的碎片结果，顺序与入参 tables 一致"))
