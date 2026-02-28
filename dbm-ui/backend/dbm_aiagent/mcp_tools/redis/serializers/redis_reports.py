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

from backend.db_report.enums import ReportStateType
from backend.dbm_aiagent.mcp_tools.redis.constants import get_creatable_subtype_choices
from backend.dbm_aiagent.mcp_tools.redis.enums import RedisReportSubtype


class RedisReportsByBizInputSerializer(serializers.Serializer):
    """Input params for querying Redis check reports by business."""

    bk_biz_id = serializers.IntegerField(help_text=_("Business ID"), default=None)
    bk_biz_abbr = serializers.CharField(
        help_text=_("Business abbreviation (db_app_abbr, alternative to bk_biz_id)"),
        default=None,
    )
    subtypes = serializers.ListField(
        child=serializers.ChoiceField(choices=RedisReportSubtype.get_choices()),
        allow_empty=True,
        default=None,
        help_text=_("Report subtype list. Defaults to all supported subtypes"),
    )
    states = serializers.ListField(
        child=serializers.ChoiceField(choices=ReportStateType.get_choices()),
        required=False,
        default=[ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value],
        help_text=_(
            'Filter by report state(s), e.g. ["warning","abnormal"] for non-normal, default is ["warning","abnormal"]'
        ),
    )
    start_time = serializers.DateTimeField(help_text=_("Start time"), default=None)
    end_time = serializers.DateTimeField(help_text=_("End time"), default=None)
    limit = serializers.IntegerField(help_text=_("Result limit"), min_value=1, max_value=200, default=100)

    def validate(self, attrs):
        if not attrs.get("bk_biz_id") and not attrs.get("bk_biz_abbr"):
            raise serializers.ValidationError(_("bk_biz_id or bk_biz_abbr is required"))
        if attrs.get("start_time") and attrs.get("end_time") and attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("Start time must be earlier than end time"))
        return attrs


class RedisReportsByClusterInputSerializer(serializers.Serializer):
    """Input params for querying Redis check reports by cluster."""

    cluster_domain = serializers.CharField(help_text=_("Cluster domain"))
    subtypes = serializers.ListField(
        child=serializers.ChoiceField(choices=RedisReportSubtype.get_choices()),
        allow_empty=True,
        default=None,
        help_text=_("Report subtype list. Defaults to all supported subtypes"),
    )
    states = serializers.ListField(
        child=serializers.ChoiceField(choices=ReportStateType.get_choices()),
        default=[ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value],
        help_text=_(
            'Filter by report state(s), e.g. ["warning","abnormal"] for non-normal, default is ["warning","abnormal"]'
        ),
    )
    start_time = serializers.DateTimeField(help_text=_("Start time"), default=None)
    end_time = serializers.DateTimeField(help_text=_("End time"), default=None)
    limit = serializers.IntegerField(help_text=_("Result limit"), min_value=1, max_value=200, default=100)

    def validate(self, attrs):
        if attrs.get("start_time") and attrs.get("end_time") and attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("Start time must be earlier than end time"))
        return attrs


class RedisReportsByMyBizsInputSerializer(serializers.Serializer):
    """Input params for querying Redis check reports across user's managed bizs."""

    subtypes = serializers.ListField(
        child=serializers.ChoiceField(choices=RedisReportSubtype.get_choices()),
        allow_empty=True,
        default=None,
        help_text=_("Report subtype list. Defaults to all supported subtypes"),
    )
    states = serializers.ListField(
        child=serializers.ChoiceField(choices=ReportStateType.get_choices()),
        allow_empty=True,
        default=[ReportStateType.ABNORMAL.value, ReportStateType.WARNING.value],
        help_text=_(
            'Filter by report state(s), e.g. ["warning","abnormal"] for non-normal, default is ["warning","abnormal"]'
        ),
    )
    start_time = serializers.DateTimeField(help_text=_("Start time"), default=None)
    end_time = serializers.DateTimeField(help_text=_("End time"), default=None)
    limit = serializers.IntegerField(help_text=_("Result limit"), min_value=1, max_value=200, default=100)

    def validate(self, attrs):
        if attrs.get("start_time") and attrs.get("end_time") and attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(_("Start time must be earlier than end time"))
        return attrs


class RedisReportItemSerializer(serializers.Serializer):
    """Redis report item payload."""

    bk_biz_id = serializers.IntegerField(help_text=_("Business ID"))
    cluster = serializers.CharField(help_text=_("Cluster domain"))
    cluster_type = serializers.CharField(help_text=_("Cluster type"))
    shard = serializers.CharField(help_text=_("Shard information"), required=False)
    instance = serializers.CharField(help_text=_("Instance information"), required=False)
    subtype = serializers.CharField(help_text=_("Report subtype"))
    msg = serializers.CharField(help_text=_("Detail message"))
    create_at = serializers.DateTimeField(help_text=_("Report creation time"))
    failed_days = serializers.IntegerField(help_text=_("Consecutive failed days"))
    state = serializers.CharField(help_text=_("State"))


class RedisReportsOutputSerializer(serializers.Serializer):
    """Output payload for Redis report query."""

    total = serializers.IntegerField(help_text=_("Total returned records"))
    items = RedisReportItemSerializer(many=True, help_text=_("Report records"))


class AddReportRecordInputSerializer(serializers.Serializer):
    """Input params for creating a Redis check report record."""

    subtype = serializers.ChoiceField(
        choices=get_creatable_subtype_choices(),
        default=RedisReportSubtype.AGENT_UNIVERSAL.value,
        help_text=_("Report subtype (must be in CREATABLE_REPORT_SUBTYPES)"),
    )
    cluster_domain = serializers.CharField(help_text=_("Cluster domain"), required=True)
    msg = serializers.CharField(help_text=_("Report message"), required=True)
    state = serializers.ChoiceField(
        choices=ReportStateType.get_choices(),
        default=ReportStateType.NORMAL.value,
        help_text=_("Report state (normal, warning, abnormal)"),
    )
    shard = serializers.CharField(help_text=_("Shard information (optional)"), required=False, default=None)
    instance = serializers.CharField(
        help_text=_("Instance information: ip:port (optional)"), required=False, default=None
    )
    creator = serializers.CharField(
        help_text=_("Creator of the report (optional). If omitted, uses request user."),
        required=False,
        default=None,
    )


class AddReportRecordOutputSerializer(serializers.Serializer):
    """Output payload for created Redis report record."""

    id = serializers.IntegerField(help_text=_("Created record ID"))
