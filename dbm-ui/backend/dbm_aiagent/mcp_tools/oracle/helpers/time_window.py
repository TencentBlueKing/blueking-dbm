# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

带时区时间与 Oracle 本地时间（sample_time / end_interval_time / SYSDATE）互转的 SQL 片段。
入参先由 serializer 规范化为展示时区（ORACLE_DISPLAY_TZ，默认 +08:00），出参统一按展示时区输出。
"""

from datetime import datetime, tzinfo

from backend.dbm_aiagent.mcp_tools.oracle.constants import ORACLE_DISPLAY_TZ, ORACLE_SQL_TZ_FORMAT

# 数据库服务器时区（与 SYSDATE、sample_time 同源）
DB_TZ = "TO_CHAR(SYSTIMESTAMP, 'TZH:TZM')"

# 展示时区（SQL 字面量 / Python tzinfo）
DISPLAY_TZ = f"'{ORACLE_DISPLAY_TZ}'"
DISPLAY_TZINFO: tzinfo = datetime.strptime(ORACLE_DISPLAY_TZ, "%z").tzinfo


def to_display_tz(dt: datetime) -> datetime:
    """带时区 datetime -> 展示时区。"""
    return dt.astimezone(DISPLAY_TZINFO)


def tz_to_local(bind: str) -> str:
    """ISO 8601 带时区入参 -> 数据库服务器本地时间（DATE），用于与本地时间列比较。"""
    return f"CAST(TO_TIMESTAMP_TZ(:{bind}, '{ORACLE_SQL_TZ_FORMAT}') AT TIME ZONE {DB_TZ} AS DATE)"


def local_to_tz(column: str, fmt: str = ORACLE_SQL_TZ_FORMAT) -> str:
    """数据库服务器本地时间列（DATE / TIMESTAMP）-> 展示时区的 ISO 8601 文本（NULL 仍为 NULL）。"""
    return f"TO_CHAR(FROM_TZ(CAST({column} AS TIMESTAMP), {DB_TZ}) AT TIME ZONE {DISPLAY_TZ}, '{fmt}')"


def tstz_to_tz(column: str, fmt: str = ORACLE_SQL_TZ_FORMAT) -> str:
    """TIMESTAMP WITH TIME ZONE 列 -> 展示时区的 ISO 8601 文本（NULL 仍为 NULL）。"""
    return f"TO_CHAR(({column}) AT TIME ZONE {DISPLAY_TZ}, '{fmt}')"
