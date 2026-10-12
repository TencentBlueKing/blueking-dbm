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
    ORACLE_ASH_MAX_LOOKBACK_DAYS,
    ORACLE_ASH_MAX_SPAN_HOURS,
    ORACLE_MAX_ROWS,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.basic_info import (
    TIME_HELP,
    OracleAddrMixin,
    OracleTimeWindowMixin,
)


class GetSqlPlanInputSerializer(OracleAddrMixin):
    sql_id = serializers.CharField(help_text=_("SQL ID（Oracle v$sql.sql_id）"))
    child_number = serializers.IntegerField(
        required=False, allow_null=True, default=None, help_text=_("子游标号，不传则输出全部子游标")
    )


class GetSqlPlanOutputSerializer(serializers.Serializer):
    sql_id = serializers.CharField()
    found = serializers.BooleanField(help_text=_("游标是否仍在共享池中"))
    plan_text = serializers.CharField(help_text=_("DBMS_XPLAN 格式化后的计划文本"))
    line_count = serializers.IntegerField(help_text=_("计划文本行数"))
    warnings = serializers.ListField(child=serializers.CharField(), help_text=_("影响计划可用性的提示"))


class GetSqlPlanAwrInputSerializer(OracleAddrMixin):
    sql_id = serializers.CharField(help_text=_("SQL ID（Oracle v$sql.sql_id）"))
    plan_hash_value = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text=_(
            "执行计划哈希值，取自 get_ash_history_top_sql / get_ash_top_sql 的 top_plan_hash_value；"
            "不传则输出该 sql_id 在 AWR 中的全部历史计划。"
            "注意这里不是 child_number——子游标是内存概念，历史快照中不存在"
        ),
    )


class GetSqlPlanAwrOutputSerializer(serializers.Serializer):
    sql_id = serializers.CharField()
    plan_hash_value = serializers.IntegerField(allow_null=True, help_text=_("请求的 plan_hash_value 回显"))
    found = serializers.BooleanField(help_text=_("dba_hist_sql_plan 中是否取到计划"))
    plan_text = serializers.CharField(help_text=_("DBMS_XPLAN.DISPLAY_AWR 格式化后的计划文本"))
    line_count = serializers.IntegerField(help_text=_("计划文本行数"))
    plan_hash_values = serializers.ListField(
        child=serializers.IntegerField(), help_text=_("该 sql_id 在 AWR 中留存的全部 plan_hash_value")
    )
    plans = serializers.ListField(
        child=serializers.DictField(),
        help_text=_("每个计划的 plan_hash_value 与 first_seen / last_seen，用于判断计划何时发生变更"),
    )
    warnings = serializers.ListField(child=serializers.CharField(), help_text=_("影响计划可用性的提示"))


# ---------- ASH ----------

_ASH_WINDOW_HELP = _(
    "实际统计窗口：actual_begin / actual_end 为真正被统计的区间（起点受 ASH 最早样本约束，终点受当前时刻约束）；"
    "coverage_pct 为实际覆盖请求窗口的比例，coverage_sufficient=false 表示内存 ASH 已被循环覆盖、"
    "结论不可信，应改用 get_ash_history_* 分析同一时段；warnings 给出具体降级原因；"
    "total_aas 为窗口内前台会话整体 AAS，total_samples 为原始样本数；"
    "load 为 CPU 繁忙度（level 由 aas_cpu / cpu_count 得出，aas_wait 为等待分量，"
    "wait_dominant=true 表示时间主要花在等待而非 CPU 上，summary 为该判定的文字说明）；"
    "activity 为数据库活跃度（level=idle/light/active + 峰值分钟 peak_minute / peak_minute_aas + "
    "sample_sufficient 样本是否足以支撑占比结论 + bursty=true 表示负载集中在峰值桶、被区间平均值掩盖，"
    "summary 为该判定的文字说明），与 load 正交"
)

_ASH_SLIM_WINDOW_HELP = _(
    "精简统计窗口，仅描述本次样本的统计区间与可信度：actual_begin / actual_end、effective_sec（aas 按它计算）、"
    "coverage_pct / coverage_sufficient / truncated、sample_sufficient（样本是否足以支撑占比结论）、"
    "total_db_time_sec、warnings；ASH 为循环缓冲区，各次调用的实际区间可能略有差异，以本字段为准。"
    "load / activity 等整体判定见 get_ash_wait_class"
)

_ASH_SPAN_HINT = _("跨度过大时统计量会被平均稀释，且扫描开销过高；分析更长的区间请改用 get_ash_history_*")


class AshWindowInputMixin(OracleAddrMixin, OracleTimeWindowMixin):
    max_span_hours = ORACLE_ASH_MAX_SPAN_HOURS
    span_exceeded_hint = _ASH_SPAN_HINT

    begin_time = serializers.CharField(
        help_text=_("起始时间，{fmt}；最早只能回溯 {days} 天，更早的时段请用 get_ash_history_*").format(
            fmt=TIME_HELP, days=ORACLE_ASH_MAX_LOOKBACK_DAYS
        )
    )
    end_time = serializers.CharField(
        help_text=_("结束时间（晚于 begin_time，与 begin_time 的跨度不超过 {hours} 小时），{fmt}").format(
            hours=ORACLE_ASH_MAX_SPAN_HOURS, fmt=TIME_HELP
        )
    )


class GetAshWaitClassInputSerializer(AshWindowInputMixin):
    pass


class GetAshWaitClassOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_ASH_WINDOW_HELP)
    wait_classes = serializers.ListField(child=serializers.DictField())
    count = serializers.IntegerField()


class GetAshTopEventsInputSerializer(AshWindowInputMixin):
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetAshTopEventsOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_ASH_SLIM_WINDOW_HELP)
    events = serializers.ListField(child=serializers.DictField())
    count = serializers.IntegerField()


class GetAshTopSqlInputSerializer(AshWindowInputMixin):
    limit = serializers.IntegerField(required=False, default=15, min_value=1, max_value=ORACLE_MAX_ROWS)


class GetAshTopSqlOutputSerializer(serializers.Serializer):
    window = serializers.DictField(help_text=_ASH_SLIM_WINDOW_HELP)
    top_sql = serializers.ListField(child=serializers.DictField())
    count = serializers.IntegerField()
