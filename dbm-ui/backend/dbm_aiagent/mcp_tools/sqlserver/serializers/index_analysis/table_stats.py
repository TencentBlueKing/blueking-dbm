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


class SQLServerTableStatsInputSerializer(IndexAnalysisBaseInputSerializer):
    pass


class _StatsItemSerializer(serializers.Serializer):
    stats_id = serializers.IntegerField(help_text=_("统计对象 ID"))
    stats_name = serializers.CharField(help_text=_("统计对象名"))
    columns = serializers.ListField(child=serializers.CharField(), help_text=_("统计涉及的列（按 stats_column_id 排序）"))
    auto_created = serializers.IntegerField(help_text=_("是否系统自动创建 1/0"))
    user_created = serializers.IntegerField(help_text=_("是否用户显式创建 1/0"))
    no_recompute = serializers.IntegerField(help_text=_("是否禁止自动更新 1/0"))
    has_filter = serializers.IntegerField(help_text=_("是否过滤统计 1/0"))
    filter_definition = serializers.CharField(help_text=_("过滤统计条件"), allow_null=True, allow_blank=True)
    last_updated = serializers.CharField(help_text=_("统计最近更新时间"), allow_null=True, allow_blank=True)
    rows = serializers.IntegerField(help_text=_("统计时的总行数"), allow_null=True)
    rows_sampled = serializers.IntegerField(help_text=_("统计时实际采样的行数"), allow_null=True)
    unfiltered_rows = serializers.IntegerField(help_text=_("过滤前的行数（非过滤统计 == rows）"), allow_null=True)
    modification_counter = serializers.IntegerField(help_text=_("自上次统计更新以来表发生修改的次数"), allow_null=True)
    steps = serializers.IntegerField(help_text=_("直方图步数"), allow_null=True)
    bound_to_index = serializers.IntegerField(help_text=_("是否随某个索引自动维护 1/0"))
    bound_index_type = serializers.CharField(
        help_text=_("绑定索引的类型描述（仅当 bound_to_index=1 时有效）"),
        allow_null=True,
        allow_blank=True,
    )
    is_outdated = serializers.BooleanField(help_text=_("基于经验阈值的过期判定结果"))


class _TableStatsResultSerializer(PerTableResultBaseSerializer):
    stats = _StatsItemSerializer(many=True, help_text=_("统计对象清单；status 非 ok 时为空数组"), required=False)
    stats_count = serializers.IntegerField(help_text=_("统计对象数量；status 非 ok 时为 0"), required=False)
    outdated_count = serializers.IntegerField(help_text=_("被判定为过期的统计对象数量；status 非 ok 时为 0"), required=False)


class SQLServerTableStatsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))
    results = _TableStatsResultSerializer(many=True, help_text=_("每张表的统计对象结果，顺序与入参 tables 一致"))
