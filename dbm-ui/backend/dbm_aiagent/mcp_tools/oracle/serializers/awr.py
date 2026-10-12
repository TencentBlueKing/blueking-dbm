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

from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_AWR_MAX_SPAN_HOURS, ORACLE_MAX_ROWS
from backend.dbm_aiagent.mcp_tools.oracle.enums import OracleAwrFormat
from backend.dbm_aiagent.mcp_tools.oracle.serializers.basic_info import OracleAddrMixin, OracleTimeWindowMixin


class ListAwrSnapshotsInputSerializer(OracleAddrMixin):
    days = serializers.IntegerField(required=False, default=7, min_value=1, max_value=90, help_text=_("回溯天数"))
    limit = serializers.IntegerField(required=False, default=ORACLE_MAX_ROWS, min_value=1, max_value=ORACLE_MAX_ROWS)


class ListAwrSnapshotsOutputSerializer(serializers.Serializer):
    snapshots = serializers.ListField(
        child=serializers.DictField(),
        help_text=_("snap_id、begin_interval_time / end_interval_time、interval_sec（快照间隔，用于发现采集缺口）"),
    )
    count = serializers.IntegerField()
    days = serializers.IntegerField()


class AwrFormatMixin(serializers.Serializer):
    """AWR 报告格式入参：默认 text（体积约为 html 的 1/4，便于裁剪与 LLM 分析）。"""

    format = serializers.ChoiceField(
        choices=OracleAwrFormat.get_choices(),
        required=False,
        default=OracleAwrFormat.TEXT.value,
        help_text=_("报告格式：text（默认，供分析）/ html（供人工查看）"),
    )


class AwrReportOutputMixin(serializers.Serializer):
    begin_snap = serializers.IntegerField()
    end_snap = serializers.IntegerField()
    format = serializers.CharField(help_text=_("实际使用的报告格式"))
    report = serializers.CharField(help_text=_("完整报告内容，体积很大"))
    report_size = serializers.IntegerField(help_text=_("报告字符数"))
    truncated = serializers.BooleanField(help_text=_("是否因触达 DRS 行数上限而被截断"))
    warnings = serializers.ListField(child=serializers.CharField(), help_text=_("影响报告可信度的提示"))


class GenerateAwrReportInputSerializer(OracleAddrMixin, AwrFormatMixin):
    begin_snap = serializers.IntegerField(min_value=1, help_text=_("起始快照 ID"))
    end_snap = serializers.IntegerField(min_value=1, help_text=_("结束快照 ID（> begin_snap）"))

    def validate(self, attrs):
        if attrs["end_snap"] <= attrs["begin_snap"]:
            raise serializers.ValidationError(_("end_snap 必须大于 begin_snap"))
        return attrs


class GenerateAwrReportOutputSerializer(AwrReportOutputMixin):
    pass


class GenerateAwrReportByTimeInputSerializer(OracleAddrMixin, OracleTimeWindowMixin, AwrFormatMixin):
    max_span_hours = ORACLE_AWR_MAX_SPAN_HOURS
    span_exceeded_hint = _("跨度过大时统计量会被平均稀释")


class GenerateAwrReportByTimeOutputSerializer(AwrReportOutputMixin):
    requested_begin_time = serializers.CharField(help_text=_("请求的起始时间"))
    requested_end_time = serializers.CharField(help_text=_("请求的结束时间"))
    actual_begin_snap = serializers.IntegerField(help_text=_("实际使用的起始快照 ID（同 begin_snap）"))
    actual_end_snap = serializers.IntegerField(help_text=_("实际使用的结束快照 ID（同 end_snap）"))
    actual_begin_time = serializers.CharField(help_text=_("begin_snap 对应时刻，可能早于请求起点"))
    actual_end_time = serializers.CharField(help_text=_("end_snap 对应时刻，可能晚于请求终点"))


class GetAwrLoadProfileInputSerializer(OracleAddrMixin, OracleTimeWindowMixin):
    max_span_hours = ORACLE_AWR_MAX_SPAN_HOURS
    span_exceeded_hint = _("区间过长会产生过多快照行，请分段查询")


class GetAwrLoadProfileOutputSerializer(serializers.Serializer):
    requested_begin_time = serializers.CharField(help_text=_("请求的起始时间"))
    requested_end_time = serializers.CharField(help_text=_("请求的结束时间"))
    actual_begin_snap = serializers.IntegerField(help_text=_("delta 基线快照 ID（其本身不产生数据行）"))
    actual_end_snap = serializers.IntegerField()
    actual_begin_time = serializers.CharField(help_text=_("实际覆盖区间起点，可能早于请求起点"))
    actual_end_time = serializers.CharField(help_text=_("实际覆盖区间终点，可能晚于请求终点"))
    snapshot_count = serializers.IntegerField(help_text=_("数据行数，即相邻快照对的个数"))
    profile = serializers.ListField(
        child=serializers.DictField(),
        help_text=_(
            "按 snap_id 升序的逐段指标：begin_time / end_time / interval_sec、"
            "db_time_sec / db_cpu_sec / aas / db_cpu_pct、"
            "logical_reads_per_sec / physical_reads_per_sec / physical_writes_per_sec / redo_mb_per_sec、"
            "executes_per_sec / user_calls_per_sec / transactions_per_sec、"
            "parses_per_sec / hard_parses_per_sec / hard_parse_pct"
        ),
    )
    warnings = serializers.ListField(child=serializers.CharField())
