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

import os

# Oracle 连接使用的 service_name
ORACLE_SERVICE_NAME = os.getenv("ORACLE_SERVICE_NAME", "CFDB")

# AWR / ASH 功能开关
ORACLE_ENABLE_AWR = os.getenv("ORACLE_ENABLE_AWR", "true").lower() == "true"

# ASH 回溯上限（天），更早的时段走 AWR 报告
ORACLE_ASH_MAX_LOOKBACK_DAYS = int(os.getenv("ORACLE_MCP_ASH_MAX_LOOKBACK_DAYS", "3"))

# ASH 单次窗口跨度上限（小时）
ORACLE_ASH_MAX_SPAN_HOURS = 6

# ASH 实际覆盖率（%）下限，低于该值结论不可信
ORACLE_ASH_MIN_COVERAGE_PCT = 90.0

# 历史 ASH（dba_hist_active_sess_history）：磁盘样本由 MMON 每 10 秒从内存 ASH 抽取一个，
# 故 1 个样本代表约 10 秒 DB time（内存 ASH 为 1 秒）。DB time / AAS 必须按该倍率换算，
# 但样本量是否足以支撑占比结论仍以原始样本数判定，不得乘以该倍率。
ORACLE_HIST_ASH_SAMPLE_INTERVAL_SEC = 10

# 历史 ASH 单次窗口跨度上限（小时），与 AWR 对齐
ORACLE_HIST_ASH_MAX_SPAN_HOURS = 24

# ASH 时间曲线可选的分桶粒度（分钟），由小到大；不指定时自动选到行数不超过 ORACLE_MAX_ROWS
ORACLE_ASH_TIMELINE_BUCKET_CHOICES = (1, 5, 15, 30, 60)

# 结果行数上限
ORACLE_MAX_ROWS = int(os.getenv("ORACLE_MCP_MAX_ROWS", "200"))

# DRS 建连超时（秒）
ORACLE_CONNECT_TIMEOUT = int(os.getenv("ORACLE_MCP_CONNECT_TIMEOUT", "5"))

# 单条查询超时（秒）
ORACLE_QUERY_TIMEOUT = int(os.getenv("ORACLE_MCP_QUERY_TIMEOUT", "60"))

# 时间入参/出参：ISO 8601 带时区偏移，如 2026-11-18T11:07:34+08:00
# 入参统一换算为该时区后参与比较，出参（含提示文案）统一以该时区展示，默认东八区
ORACLE_DISPLAY_TZ = os.getenv("ORACLE_MCP_DISPLAY_TZ", "+08:00")
ORACLE_SQL_TZ_FORMAT = 'YYYY-MM-DD"T"HH24:MI:SSTZH:TZM'
ORACLE_SQL_TZ_MINUTE_FORMAT = 'YYYY-MM-DD"T"HH24:MITZH:TZM'

# AWR 报告行数上限（DRS 侧限制），达到即视为被截断
ORACLE_AWR_MAX_LINES = 100000

# 按时间生成 AWR 报告的最大跨度（小时）
ORACLE_AWR_MAX_SPAN_HOURS = 24

# 执行计划文本行数上限
ORACLE_XPLAN_MAX_LINES = 2000
