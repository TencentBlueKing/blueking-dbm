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
    from_ = serializers.CharField(source="from", help_text=_("查询起始时间，集群时区 YYYY-MM-DD HH:MM"))
    to = serializers.CharField(help_text=_("查询截止时间，集群时区 YYYY-MM-DD HH:MM"))
    time_zone = serializers.CharField(help_text=_("集群时区，如 +08:00"))


class QueryClusterSkewEpisodesTableSerializer(serializers.Serializer):
    columns = serializers.ListField(
        child=serializers.CharField(),
        help_text=_("列名：metric, role, pattern, start, end, group_mean, hot_nodes, cold_nodes, transitions"),
    )
    rows = serializers.ListField(
        child=serializers.ListField(),
        help_text=_(
            "倾斜事件段行数据。"
            "group_mean 为 episode 内 role 组均值代表值；"
            "hot_nodes/cold_nodes 每条格式为 "
            "node value=X mean=Y pct=±Z% abs_dev=W，多条以 ; 分隔；"
            "pattern 为 fixed 或 migrating；"
            "transitions 仅在 migrating 时有值，格式为 HH:MM→nodes；"
            "start/end/transitions 时间为集群时区"
        ),
    )


class QueryClusterSkewDataOutputSerializer(serializers.Serializer):
    has_skew = serializers.BooleanField(help_text=_("查询时间段内是否存在倾斜事件"))
    cluster = serializers.CharField(help_text=_("集群域名"))
    period = QueryClusterSkewDataPeriodSerializer(help_text=_("实际查询的日期范围"))
    episodes = QueryClusterSkewEpisodesTableSerializer(help_text=_("倾斜事件段列表（columns + rows 表格格式）"))
