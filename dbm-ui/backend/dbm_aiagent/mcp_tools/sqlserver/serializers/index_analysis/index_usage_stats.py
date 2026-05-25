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


class SQLServerIndexUsageStatsInputSerializer(IndexAnalysisBaseInputSerializer):
    pass


class _IndexUsageItemSerializer(serializers.Serializer):
    index_id = serializers.IntegerField(help_text=_("索引 ID"))
    index_name = serializers.CharField(help_text=_("索引名"), allow_null=True, allow_blank=True)
    type_desc = serializers.CharField(help_text=_("索引类型描述"))
    is_unique = serializers.IntegerField(help_text=_("是否唯一 1/0"))
    is_primary_key = serializers.IntegerField(help_text=_("是否主键 1/0"))
    user_seeks = serializers.IntegerField(help_text=_("用户 seek 次数（启动以来累计）"))
    user_scans = serializers.IntegerField(help_text=_("用户 scan 次数（启动以来累计）"))
    user_lookups = serializers.IntegerField(help_text=_("用户 lookup 次数（启动以来累计）"))
    user_updates = serializers.IntegerField(help_text=_("索引维护引发的更新次数（启动以来累计）"))
    last_user_seek = serializers.CharField(help_text=_("最近一次 seek 时间"), allow_null=True, allow_blank=True)
    last_user_scan = serializers.CharField(help_text=_("最近一次 scan 时间"), allow_null=True, allow_blank=True)
    last_user_lookup = serializers.CharField(help_text=_("最近一次 lookup 时间"), allow_null=True, allow_blank=True)
    last_user_update = serializers.CharField(help_text=_("最近一次因更新触发索引维护的时间"), allow_null=True, allow_blank=True)


class _IndexUsageResultSerializer(PerTableResultBaseSerializer):
    indexes = _IndexUsageItemSerializer(many=True, help_text=_("索引使用画像清单；status 非 ok 时为空数组"), required=False)
    index_count = serializers.IntegerField(help_text=_("索引数量；status 非 ok 时为 0"), required=False)


class SQLServerIndexUsageStatsOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(help_text=_("实际查询的实例地址"))
    role = serializers.CharField(help_text=_("查询实例的角色"))
    dbname = serializers.CharField(help_text=_("目标数据库名"))
    schema = serializers.CharField(help_text=_("批量共用的 schema"))
    sqlserver_start_time = serializers.CharField(
        help_text=_("实例启动时间（累计计数样本起点；全实例共享，故置于顶层）"),
        allow_null=True,
        allow_blank=True,
    )
    table_count = serializers.IntegerField(help_text=_("入参表数量（去重后）"))
    ok_count = serializers.IntegerField(help_text=_("status=ok 的表数量"))
    results = _IndexUsageResultSerializer(many=True, help_text=_("每张表的索引使用画像，顺序与入参 tables 一致"))
