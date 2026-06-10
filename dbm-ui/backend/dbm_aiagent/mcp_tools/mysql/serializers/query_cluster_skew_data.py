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


class QueryClusterSkewDataInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    from_date = serializers.DateTimeField(help_text=_("查询起始时间"))
    to_date = serializers.DateTimeField(help_text=_("查询截止时间"))

    def validate(self, attrs):
        if attrs["from_date"] > attrs["to_date"]:
            raise serializers.ValidationError(_("from_date 不能晚于 to_date"))
        return attrs


class QueryClusterSkewDataPeriodSerializer(serializers.Serializer):
    from_ = serializers.CharField(source="from", help_text=_("查询起始日期，ISO 8601 格式"))
    to = serializers.CharField(help_text=_("查询截止日期，ISO 8601 格式"))


class QueryClusterSkewEpisodesTableSerializer(serializers.Serializer):
    columns = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("列名：metric, role, pattern, start, end, hot_deviations, cold_deviations, transitions"),
    )
    rows = serializers.ListField(
        child=serializers.ListField(),
        help_text=_(
            "倾斜事件段行数据。"
            "每行对应一列 columns 中的字段："
            "pattern 为 fixed（热点节点固定）或 migrating（热点节点随时间迁移）；"
            "hot_deviations/cold_deviations 格式为 node:+pct 或 node:pct，表示 episode 内各节点相对均值的最大偏离百分比；"
            "transitions 仅在 pattern=migrating 时有值，格式为 HH:MM→nodes 的逗号分隔列表"
        ),
    )


class QueryClusterSkewDataOutputSerializer(serializers.Serializer):
    has_skew = serializers.BooleanField(help_text=_("查询时间段内是否存在倾斜事件"))
    cluster = serializers.CharField(help_text=_("集群域名"))
    period = QueryClusterSkewDataPeriodSerializer(help_text=_("实际查询的日期范围"))
    episodes = QueryClusterSkewEpisodesTableSerializer(help_text=_("倾斜事件段列表（columns + rows 表格格式）"))
