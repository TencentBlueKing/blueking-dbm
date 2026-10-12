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

from backend.dbm_aiagent.mcp_tools.oracle.constants import (
    ORACLE_ASH_TIMELINE_BUCKET_CHOICES,
    ORACLE_HIST_ASH_MAX_SPAN_HOURS,
    ORACLE_MAX_ROWS,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.basic_info import (
    TIME_HELP,
    OracleAddrMixin,
    OracleTimeWindowMixin,
)

_HIST_WINDOW_HELP = _(
    "实际统计窗口：actual_begin / actual_end 为真正被统计的区间（起点受 AWR 保留期约束，"
    "终点受最新快照时刻约束——晚于最新快照的 ASH 样本尚未落盘，历史视图中不可见）；"
    "unflushed_sec > 0 即请求终点落在未落盘区间，该段需改用内存 ASH 工具；"
    "coverage_pct / coverage_sufficient 同内存 ASH 口径，false 表示请求起点早于保留期；"
    "sample_interval_sec=10 说明每个样本代表 10 秒，db_time_sec 已按该倍率换算；"
    "total_samples 为原始样本数，sample_sufficient 按它判定（不乘倍率）；"
    "snap_lo / snap_hi 为本次实际扫描的快照区间，snap_interval_min 为实例的快照采集间隔；"
    "load 为 CPU 繁忙度（含 wait_dominant 与 summary 文字说明），"
    "activity 为数据库活跃度（峰值桶为 5 分钟粒度，字段 peak_bucket，含 bursty 与 summary 文字说明）"
)

_HIST_SLIM_WINDOW_HELP = _(
    "精简统计窗口：actual_begin / actual_end、effective_sec（aas 按它计算）、"
    "coverage_pct / coverage_sufficient / truncated、sample_sufficient、total_db_time_sec、warnings；"
    "load / activity 等整体判定见 get_ash_history_wait_class"
)

_HIST_SPAN_HINT = _("跨度过大时统计量会被平均稀释，若只想看整体负载规模请改用 get_awr_load_profile")


class HistAshWindowInputMixin(OracleAddrMixin, OracleTimeWindowMixin):
    max_span_hours = ORACLE_HIST_ASH_MAX_SPAN_HOURS
    span_exceeded_hint = _HIST_SPAN_HINT

    begin_time = serializers.CharField(
        help_text=_("起始时间，{fmt}；可回溯范围取决于 AWR 实际保留期，起点早于保留期时出参 coverage_sufficient=false").format(fmt=TIME_HELP)
    )
    end_time = serializers.CharField(
        help_text=_("结束时间（晚于 begin_time，与 begin_time 的跨度不超过 {hours} 小时），{fmt}").format(
            hours=ORACLE_HIST_ASH_MAX_SPAN_HOURS, fmt=TIME_HELP
        )
    )


class GetAshHistoryTimelineInputSerializer(HistAshWindowInputMixin):
    bucket_minutes = serializers.ChoiceField(
        choices=[(value, str(value)) for value in ORACLE_ASH_TIMELINE_BUCKET_CHOICES],
        required=False,
        allow_null=True,
        default=None,
        help_text=_("分桶粒度（分钟），可选 {choices}；不传则自动选取最细且行数不超过 {rows} 的粒度").format(
            choices=list(ORACLE_ASH_TIMELINE_BUCKET_CHOICES), rows=ORACLE_MAX_ROWS
        ),
    )


class GetAshHistoryTimelineOutputSerializer(serializers.Serializer):
    window = serializers.DictField(
        help_text=_(
            "{base}；另含 bucket_minutes（实际分桶粒度）、bucket_count / expected_bucket_count"
            "（两者之差即无活跃样本的空闲桶数）、total_aas（窗口整体平均，与曲线峰值对比可量化尖峰程度）"
        ).format(base=_HIST_SLIM_WINDOW_HELP)
    )
    timeline = serializers.ListField(
        child=serializers.DictField(),
        help_text=_(
            "按时间升序的分桶序列：bucket_begin、samples、db_time_sec、aas（按桶长计算）、aas_cpu、"
            "top_wait_class、top_wait_pct；无样本的桶不会出现在序列中"
        ),
    )
    count = serializers.IntegerField()


class GetAshHistoryWaitClassInputSerializer(HistAshWindowInputMixin):
    pass


class GetAshHistoryWaitClassOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_HIST_WINDOW_HELP)
    wait_classes = serializers.ListField(
        child=serializers.DictField(), help_text=_("wait_class、samples、db_time_sec、aas、pct")
    )
    count = serializers.IntegerField()


class GetAshHistoryTopEventsInputSerializer(HistAshWindowInputMixin):
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetAshHistoryTopEventsOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_HIST_SLIM_WINDOW_HELP)
    events = serializers.ListField(
        child=serializers.DictField(),
        help_text=_("event、wait_class、samples、db_time_sec、aas、pct、pct_cum、sessions、top_sql_id、top_sql_sec"),
    )
    count = serializers.IntegerField()


class GetAshHistoryTopSqlInputSerializer(HistAshWindowInputMixin):
    limit = serializers.IntegerField(required=False, default=15, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetAshHistoryTopSqlOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_HIST_SLIM_WINDOW_HELP)
    top_sql = serializers.ListField(
        child=serializers.DictField(),
        help_text=_(
            "sql_id、samples、db_time_sec、aas、pct_of_sql_time、pct_of_db_time、top_event、top_event_pct、"
            "plan_count（窗口内不同执行计划个数，>1 说明期间发生过计划变化）、top_plan_hash_value、sql_text。"
            "不返回 child_number：历史计划用 sql_id + top_plan_hash_value 调 get_sql_plan_awr 获取"
        ),
    )
    count = serializers.IntegerField()
