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

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_instances
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpInstanceNotFoundException,
    DBMMcpNotSupportMachineTypeException,
)
from backend.dbm_aiagent.mcp_tools.oracle.helpers.assert_clustertype import assert_cluster_type
from backend.dbm_aiagent.mcp_tools.oracle.impl.ash_history import (
    get_ash_history_timeline,
    get_ash_history_top_events,
    get_ash_history_top_sql,
    get_ash_history_wait_class,
)
from backend.dbm_aiagent.mcp_tools.oracle.impl.awr import (
    generate_awr_report,
    generate_awr_report_by_time,
    get_awr_load_profile,
    list_awr_snapshots,
)
from backend.dbm_aiagent.mcp_tools.oracle.impl.capacity import get_sga_pga_usage, get_tablespace_usage, get_undo_usage
from backend.dbm_aiagent.mcp_tools.oracle.impl.performance import (
    get_ash_top_events,
    get_ash_top_sql,
    get_ash_wait_class,
    get_sql_plan,
    get_sql_plan_awr,
)
from backend.dbm_aiagent.mcp_tools.oracle.impl.session_activity import (
    get_active_sessions,
    get_blocking_sessions,
    get_long_running_queries,
)
from backend.dbm_aiagent.mcp_tools.oracle.impl.status import check_instance_status, get_alert_log_errors
from backend.dbm_aiagent.mcp_tools.oracle.serializers.ash_history import (
    GetAshHistoryTimelineInputSerializer,
    GetAshHistoryTimelineOutputSerializer,
    GetAshHistoryTopEventsInputSerializer,
    GetAshHistoryTopEventsOutputSerializer,
    GetAshHistoryTopSqlInputSerializer,
    GetAshHistoryTopSqlOutputSerializer,
    GetAshHistoryWaitClassInputSerializer,
    GetAshHistoryWaitClassOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.awr import (
    GenerateAwrReportByTimeInputSerializer,
    GenerateAwrReportByTimeOutputSerializer,
    GenerateAwrReportInputSerializer,
    GenerateAwrReportOutputSerializer,
    GetAwrLoadProfileInputSerializer,
    GetAwrLoadProfileOutputSerializer,
    ListAwrSnapshotsInputSerializer,
    ListAwrSnapshotsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.capacity import (
    GetSgaPgaUsageInputSerializer,
    GetSgaPgaUsageOutputSerializer,
    GetTablespaceUsageInputSerializer,
    GetTablespaceUsageOutputSerializer,
    GetUndoUsageInputSerializer,
    GetUndoUsageOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.performance import (
    GetAshTopEventsInputSerializer,
    GetAshTopEventsOutputSerializer,
    GetAshTopSqlInputSerializer,
    GetAshTopSqlOutputSerializer,
    GetAshWaitClassInputSerializer,
    GetAshWaitClassOutputSerializer,
    GetSqlPlanAwrInputSerializer,
    GetSqlPlanAwrOutputSerializer,
    GetSqlPlanInputSerializer,
    GetSqlPlanOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.session_activity import (
    GetActiveSessionsInputSerializer,
    GetActiveSessionsOutputSerializer,
    GetBlockingSessionsInputSerializer,
    GetBlockingSessionsOutputSerializer,
    GetLongRunningInputSerializer,
    GetLongRunningOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.oracle.serializers.status import (
    CheckInstanceStatusInputSerializer,
    CheckInstanceStatusOutputSerializer,
    GetAlertLogErrorsInputSerializer,
    GetAlertLogErrorsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterDetailPermission

logger = logging.getLogger("root")


class OracleQueryMcpToolsViewSet(McpToolsViewSet):
    """Oracle 只读查询 MCP 工具集（oracle-query）。

    鉴权维度：实例所属集群（bk_cloud_id + address）；统一走 McpClusterDetailPermission + auth_parse_instances。
    对应 MCP server: `oracle-query`，覆盖状态探活 / 会话与活动 / 性能分析（内存 ASH）/
    历史 ASH / 容量 / AWR 等能力。
    """

    default_permission_class = [DBManagePermission()]

    def _resolve_address(self) -> str:
        """校验 bk_cloud_id + address 指向一个 Oracle 实例，返回该 address。

        所有工具的统一前置：先确认机器存在且类型为 ORACLE，再确认其所属集群是 Oracle 集群，
        避免借 address 连接任意实例。
        """
        address = self.get_param("address")
        machine_obj = _validate_and_get_machine(self.get_param("bk_cloud_id"), address)
        assert_cluster_type(machine_obj)
        return address

    @mcp_tools_api_decorator(
        description=str(
            _(
                "Oracle 实例综合状态探活：连接是否可达、v$instance/v$database 关键状态、会话数与上限使用率、"
                "DG 角色与切换状态，聚合输出 healthy/warning/critical 结论与原因列表，以及本次探活耗时。"
            )
        ),
        request_slz=CheckInstanceStatusInputSerializer,
        response_slz=CheckInstanceStatusOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def check_instance_status(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            check_instance_status(
                addr=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询近 N 分钟 Oracle 告警日志中的 ORA 错误（v$diag_alert_ext），默认 120 分钟。"
                "结果按错误码聚合，每项含 occurrences（出现次数）、first_seen / last_seen 与 sample_text"
                "（最近一次的消息，含 trace 文件路径）；count 为去重后的错误码个数。"
                "不含 ORA 错误的消息（日志切换、实例启停等）不返回，实例是否刚重启可看 "
                "check_instance_status 的 state.startup_time。"
            )
        ),
        request_slz=GetAlertLogErrorsInputSerializer,
        response_slz=GetAlertLogErrorsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_alert_log_errors(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_alert_log_errors(
                addr=address,
                minutes=self.get_param("minutes"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 Oracle 活跃会话（v$session, status=ACTIVE 且非 Idle 等待类）。"
                "返回的 sql_id + child_number 可直接传给 get_sql_plan 查看该会话正在执行的计划。"
            )
        ),
        request_slz=GetActiveSessionsInputSerializer,
        response_slz=GetActiveSessionsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_active_sessions(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_active_sessions(
                addr=address,
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 Oracle 阻塞链（blocker → waiter），用于锁争用排查。"
                "blocker_sql_id + blocker_child_number（或 waiter_ 前缀的一对）可传给 get_sql_plan 查看对应计划。"
            )
        ),
        request_slz=GetBlockingSessionsInputSerializer,
        response_slz=GetBlockingSessionsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_blocking_sessions(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_blocking_sessions(
                addr=address,
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询长时间运行的 SQL（基于 v$session.last_call_et），min_seconds 可指定最小阈值。"
                "返回的 sql_id + child_number 可直接传给 get_sql_plan 查看其执行计划。"
            )
        ),
        request_slz=GetLongRunningInputSerializer,
        response_slz=GetLongRunningOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_long_running_queries(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_long_running_queries(
                addr=address,
                min_seconds=self.get_param("min_seconds"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询指定 sql_id 的【当前】执行计划（DBMS_XPLAN.DISPLAY_CURSOR，固定 ALL 格式），返回带缩进的执行树、"
                "Predicate Information、Column Projection 与 Note 等官方格式化文本。"
                "依赖共享池，SQL 被 age out 后 found=false——分析历史时段请改用 get_sql_plan_awr。"
                "child_number 只能取自其他工具返回的 child_number / top_child_number 字段，"
                "禁止用 plan_hash_value、plan_count 等其他数值填充；不确定时省略，此时输出全部子游标。"
            )
        ),
        request_slz=GetSqlPlanInputSerializer,
        response_slz=GetSqlPlanOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_sql_plan(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_sql_plan(
                sql_id=self.get_param("sql_id"),
                addr=address,
                child_number=self.get_param("child_number"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询指定 sql_id 的【历史】执行计划（DBMS_XPLAN.DISPLAY_AWR，读 dba_hist_sql_plan），"
                "不依赖共享池，游标被 age out 后仍可取到，是历史性能分析链路的终点。"
                "定位维度是 plan_hash_value（取自 get_ash_history_top_sql / get_ash_top_sql 的 top_plan_hash_value），"
                "不是 child_number；省略则输出该 sql_id 的全部历史计划。"
                "出参 plan_hash_values 与 plans 给出该 SQL 在 AWR 中留存的所有计划及其出现时间，"
                "可据此判断执行计划是否在某个时点发生过变更。"
                "若 get_sql_plan 返回 found=false，改用本工具重试。"
            )
        ),
        request_slz=GetSqlPlanAwrInputSerializer,
        response_slz=GetSqlPlanAwrOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_sql_plan_awr(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_sql_plan_awr(
                addr=address,
                sql_id=self.get_param("sql_id"),
                plan_hash_value=self.get_param("plan_hash_value"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "ASH 下钻第 1 步：指定时间窗口 [begin_time, end_time] 内前台会话 DB time 按 wait_class 汇总"
                "（v$active_session_history，1 样本≈1 秒），用于判断时间主要花在 CPU / User I/O / Concurrency / "
                "Application 等哪个方向。返回 db_time_sec、aas、pct。"
                "时间为 ISO 8601 带时区偏移（例 '2026-11-18T11:07:34+08:00'），"
                "最早回溯 3 天，跨度不超过 6 小时；"
                "「最近 N 分钟」等相对描述需由调用方先换算为绝对区间，超出限制时改用 generate_awr_report_by_time。"
                "window.coverage_sufficient=false 表示内存 ASH 已被循环覆盖、结论不可信，"
                "应改用 generate_awr_report_by_time 分析同一时段；window.load 为 CPU 繁忙度；"
                "window.activity 为数据库活跃度（idle / light / active），含峰值分钟及其 AAS；"
                "activity.sample_sufficient=false 时各项 pct 不具统计意义，不应据此下钻。"
                "需开启 ORACLE_ENABLE_AWR（Diagnostics Pack）。"
            )
        ),
        request_slz=GetAshWaitClassInputSerializer,
        response_slz=GetAshWaitClassOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_wait_class(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_wait_class(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "ASH 下钻第 2 步：指定时间窗口 [begin_time, end_time] 内前台会话 Top 等待事件，"
                "含 db_time_sec、aas、pct、pct_cum（累计占比）、sessions（涉及会话数）、"
                "top_sql_id（该事件下贡献最多的 SQL）。时间窗口与限制同 get_ash_wait_class。"
                "window 为精简版（统计区间、coverage_sufficient、sample_sufficient、warnings），"
                "load / activity 等整体判定见 get_ash_wait_class。"
                "需开启 ORACLE_ENABLE_AWR。"
            )
        ),
        request_slz=GetAshTopEventsInputSerializer,
        response_slz=GetAshTopEventsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_top_events(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_top_events(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "ASH 下钻第 3 步：指定时间窗口 [begin_time, end_time] 内按 DB time 排序的 Top SQL，"
                "含 aas、pct_of_db_time、top_event / top_event_pct（主要等待）、"
                "plan_count（窗口内不同执行计划个数，>1 可能发生计划变化）、"
                "top_plan_hash_value、top_child_number、sql_text。时间窗口与限制同 get_ash_wait_class。"
                "window 为精简版（统计区间、coverage_sufficient、sample_sufficient、warnings），"
                "load / activity 等整体判定见 get_ash_wait_class。"
                "可用 sql_id + top_child_number 调 get_sql_plan 查看执行计划；"
                "该 child_number 是历史快照，查不到计划时省略它重试。需开启 ORACLE_ENABLE_AWR。"
            )
        ),
        request_slz=GetAshTopSqlInputSerializer,
        response_slz=GetAshTopSqlOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_top_sql(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_top_sql(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "历史分析第 2 步（定位尖峰）：输出指定历史时段内 AAS 的时间曲线"
                "（dba_hist_active_sess_history 按时间分桶）。"
                "AWR 报告给的是区间平均值，1 小时快照会把 10 分钟的尖峰完全抹平；本工具按分桶画出 AAS 走势，"
                "用于找到负载到底集中在哪几分钟，再对那个窄窗口单独下钻。"
                "每行含 bucket_begin、aas（按桶长计算）、aas_cpu、top_wait_class、top_wait_pct；"
                "把各桶 aas 与 window.total_aas 对比即可量化尖峰被平均掩盖的程度。"
                "无活跃样本的时间桶不会出现在序列中（表示该时段空闲）。"
                "bucket_minutes 可选 1/5/15/30/60，不传则自动选取。"
                "时间为 ISO 8601 带时区偏移（例 '2026-11-18T11:07:34+08:00'），跨度不超过 24 小时。"
                "需开启 ORACLE_ENABLE_AWR（Diagnostics Pack）。"
            )
        ),
        request_slz=GetAshHistoryTimelineInputSerializer,
        response_slz=GetAshHistoryTimelineOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_history_timeline(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_history_timeline(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                bucket_minutes=self.get_param("bucket_minutes"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "历史 ASH 下钻第 1 步：指定历史时段 [begin_time, end_time] 内前台会话 DB time 按 wait_class 汇总"
                "（dba_hist_active_sess_history），用于判断时间主要花在 CPU / User I/O / Concurrency / "
                "Application 等哪个方向。"
                "与内存 ASH 版（get_ash_wait_class）的分工：超过内存 ASH 回溯范围的「过去某时段」用本工具，"
                "正在发生的问题用内存版（1 秒粒度、会话级信息、游标仍在共享池）。"
                "历史 ASH 每个样本代表 10 秒，db_time_sec 已按该倍率换算；"
                "window.total_samples 为原始样本数，sample_sufficient 按它判定。"
                "window.coverage_sufficient=false 表示请求起点早于 AWR 保留期；"
                "window.unflushed_sec > 0 表示请求终点落在尚未落盘的区间，该段需改用内存 ASH 工具。"
                "window.load 为 CPU 繁忙度，window.activity 为数据库活跃度（峰值桶为 5 分钟粒度）。"
                "时间为 ISO 8601 带时区偏移，跨度不超过 24 小时。需开启 ORACLE_ENABLE_AWR。"
            )
        ),
        request_slz=GetAshHistoryWaitClassInputSerializer,
        response_slz=GetAshHistoryWaitClassOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_history_wait_class(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_history_wait_class(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "历史 ASH 下钻第 2 步：指定历史时段内前台会话 Top 等待事件，"
                "含 samples、db_time_sec、aas、pct、pct_cum（累计占比）、sessions（涉及会话数）、"
                "top_sql_id（该事件下贡献最多的 SQL）。时间窗口与限制同 get_ash_history_wait_class。"
                "window 为精简版，load / activity 等整体判定见 get_ash_history_wait_class。"
                "需开启 ORACLE_ENABLE_AWR。"
            )
        ),
        request_slz=GetAshHistoryTopEventsInputSerializer,
        response_slz=GetAshHistoryTopEventsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_history_top_events(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_history_top_events(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "历史 ASH 下钻第 3 步：指定历史时段内按 DB time 排序的 Top SQL，"
                "含 samples、db_time_sec、aas、pct_of_db_time、top_event / top_event_pct（主要等待）、"
                "plan_count（窗口内不同执行计划个数，>1 说明期间发生过计划变化）、top_plan_hash_value、sql_text。"
                "时间窗口与限制同 get_ash_history_wait_class。"
                "window 为精简版，load / activity 等整体判定见 get_ash_history_wait_class。"
                "下一步用 sql_id + top_plan_hash_value 调 get_sql_plan_awr 查看执行计划；"
                "本工具不返回 child_number（历史快照中没有子游标概念），不要拿 plan_hash_value 去填 "
                "get_sql_plan 的 child_number。需开启 ORACLE_ENABLE_AWR。"
            )
        ),
        request_slz=GetAshHistoryTopSqlInputSerializer,
        response_slz=GetAshHistoryTopSqlOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_ash_history_top_sql(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_ash_history_top_sql(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 Oracle 表空间使用率（按已用占比降序，含 autoextensible 与 max_mb）。")),
        request_slz=GetTablespaceUsageInputSerializer,
        response_slz=GetTablespaceUsageOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_tablespace_usage(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_tablespace_usage(
                addr=address,
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 Oracle Undo 表空间使用情况（按 ACTIVE/UNEXPIRED/EXPIRED 分组）。")),
        request_slz=GetUndoUsageInputSerializer,
        response_slz=GetUndoUsageOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_undo_usage(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_undo_usage(
                addr=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("查询 Oracle SGA / PGA 使用情况（v$sga + v$pgastat）。")),
        request_slz=GetSgaPgaUsageInputSerializer,
        response_slz=GetSgaPgaUsageOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_sga_pga_usage(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_sga_pga_usage(
                addr=address,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出最近 N 天的 AWR 快照（dba_hist_snapshot），默认 7 天。"
                "除 snap_id 与区间时刻外还返回 interval_sec（快照间隔），"
                "可据此确认目标时段的快照是否连续、有无采集缺口。"
            )
        ),
        request_slz=ListAwrSnapshotsInputSerializer,
        response_slz=ListAwrSnapshotsOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def list_awr_snapshots(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            list_awr_snapshots(
                addr=address,
                days=self.get_param("days"),
                limit=self.get_param("limit"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "生成指定快照区间 [begin_snap, end_snap] 的 AWR 报告（dbms_workload_repository）。"
                "format=text（默认）供分析，html 供人工查看。"
                "【警告】返回完整报告，体积通常 200KB-2MB，必须由脚本/CLI 调用后裁剪再使用，"
                "禁止直接调用，否则会占满上下文。若只需定位时间范围，请先用 list_awr_snapshots。"
            )
        ),
        request_slz=GenerateAwrReportInputSerializer,
        response_slz=GenerateAwrReportOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def generate_awr_report(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            generate_awr_report(
                begin_snap=self.get_param("begin_snap"),
                end_snap=self.get_param("end_snap"),
                addr=address,
                report_format=self.get_param("format"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "按时间区间生成 AWR 报告：自动把 [begin_time, end_time] 解析为快照区间，无需先查 snap_id。"
                "时间为 ISO 8601 带时区偏移（例 '2026-11-18T11:07:34+08:00'），跨度上限 24 小时。"
                "快照按外扩策略选取，实际区间可能宽于请求，由出参 actual_begin_snap / actual_end_snap 与 "
                "actual_begin_time / actual_end_time 回显。"
                "format=text（默认）供分析，html 供人工查看。"
                "【警告】返回完整报告，体积通常 200KB-2MB，必须由脚本/CLI 调用后裁剪再使用，"
                "禁止直接调用，否则会占满上下文。"
            )
        ),
        request_slz=GenerateAwrReportByTimeInputSerializer,
        response_slz=GenerateAwrReportByTimeOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def generate_awr_report_by_time(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            generate_awr_report_by_time(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
                report_format=self.get_param("format"),
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                "历史分析第 1 步（定性与基线对比）：按快照逐段输出负载指标序列，数据源为 "
                "dba_hist_sys_time_model 与 dba_hist_sysstat 的增量，返回结构化 JSON（通常几 KB），"
                "可直接调用，无需裁剪。"
                "指标含 db_time_sec / db_cpu_sec / aas / db_cpu_pct、逻辑读与物理读写每秒值、redo_mb_per_sec、"
                "executes_per_sec / user_calls_per_sec / transactions_per_sec、"
                "parses_per_sec / hard_parses_per_sec / hard_parse_pct。"
                "巡检与基线对比的主入口：AWR 报告只给一个区间的聚合值，无法回答「是否偏离正常水平」；"
                "本工具给的是逐快照序列，既能看走势，也能把另一时段的同结构结果拿来直接对比。"
                "profile 按 snap_id 升序，逐段对比即可看出指标走势与偏离。"
                "时间为 ISO 8601 带时区偏移，跨度上限 24 小时。"
                "若需要表空间 I/O、Segment 级统计等本工具未覆盖的明细，再用 generate_awr_report_by_time。"
            )
        ),
        request_slz=GetAwrLoadProfileInputSerializer,
        response_slz=GetAwrLoadProfileOutputSerializer,
        permission_classes=[McpClusterDetailPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.ORACLE_QUERY],
        name_prefix="oracle_query",
    )
    def get_awr_load_profile(self, request, *args, **kwargs):
        address = self._resolve_address()

        return Response(
            get_awr_load_profile(
                addr=address,
                begin_time=self.get_param("begin_time"),
                end_time=self.get_param("end_time"),
            )
        )


def _validate_and_get_machine(bk_cloud_id: int, address: str) -> Machine:
    """根据云区域和实例地址获取 Oracle 机器。"""
    ip = address.rsplit(IP_PORT_DIVIDER, 1)[0]
    machine_obj = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if not machine_obj:
        raise DBMMcpInstanceNotFoundException(msg=f"machine not found: bk_cloud_id={bk_cloud_id}, ip={ip}")

    if machine_obj.machine_type != MachineType.ORACLE:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_obj.machine_type)

    return machine_obj
