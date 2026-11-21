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

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.constants import (
    DTS_PRECHECK_CONNECT_TIMEOUT_MIN,
    DTS_PRECHECK_DISPLAY_LIMIT,
    DTS_PRECHECK_LONG_SQL_SECONDS,
    DTS_PRECHECK_ONE_GB,
)
from backend.flow.utils.mysql.dts.precheck.scope import filter_tables_for_database, resolve_migration_databases
from backend.flow.utils.mysql.dts.precheck.sqlutil import quote_str_list

_VAR_NAMES = ("lower_case_table_names", "max_allowed_packet", "connect_timeout")


def _as_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _row_get(row: dict, *keys):
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def _check_row_format(ctx: CheckContext) -> CheckResult:
    databases = resolve_migration_databases(ctx.scope, ctx.source.user_schemas())
    sql = (
        "SELECT TABLE_SCHEMA, TABLE_NAME, ROW_FORMAT FROM information_schema.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA IN {}"
    ).format(quote_str_list(databases))
    fixed = []
    for row in ctx.source.query(sql):
        schema = str(_row_get(row, "TABLE_SCHEMA", "table_schema") or "")
        table = str(_row_get(row, "TABLE_NAME", "table_name") or "")
        row_format = str(_row_get(row, "ROW_FORMAT", "row_format") or "")
        if not schema or not table:
            continue
        if table not in filter_tables_for_database(schema, [table], ctx.scope):
            continue
        if row_format.strip().upper() == "FIXED":
            fixed.append({"schema": schema, "table": table, "row_format": row_format})
    total = len(fixed)
    ok = total == 0
    return CheckResult(
        ok=ok,
        code="instance_vars.row_format",
        message=_("源端待迁移表 row_format 均不是 FIXED") if ok else _("源端存在 {} 张 row_format=FIXED 的表").format(total),
        level=CheckLevel.FAIL,
        details={
            "total": total,
            "tables": fixed[:DTS_PRECHECK_DISPLAY_LIMIT],
            "truncated": total > DTS_PRECHECK_DISPLAY_LIMIT,
        },
    )


def _check_lower_case(source_vars: dict[str, str], target_vars: dict[str, str]) -> CheckResult:
    source_value = source_vars.get("lower_case_table_names", "")
    target_value = target_vars.get("lower_case_table_names", "")
    ok = source_value == target_value and source_value != ""
    return CheckResult(
        ok=ok,
        code="instance_vars.lower_case_table_names",
        message=_("两端 lower_case_table_names 一致") if ok else _("两端 lower_case_table_names 不一致或缺失"),
        level=CheckLevel.FAIL,
        details={"source": source_value, "target": target_value},
    )


def _check_target_packet(target_vars: dict[str, str]) -> CheckResult:
    value = _as_int(target_vars.get("max_allowed_packet", "0"))
    ok = value >= DTS_PRECHECK_ONE_GB
    return CheckResult(
        ok=ok,
        code="instance_vars.max_allowed_packet",
        message=_("目标端 max_allowed_packet ≥ 1GB") if ok else _("目标端 max_allowed_packet 小于 1GB"),
        level=CheckLevel.FAIL,
        details={"target": value, "required": DTS_PRECHECK_ONE_GB},
    )


def _check_connect_timeout(source_vars: dict[str, str]) -> CheckResult:
    value = _as_int(source_vars.get("connect_timeout", "0"))
    ok = value >= DTS_PRECHECK_CONNECT_TIMEOUT_MIN
    return CheckResult(
        ok=ok,
        code="instance_vars.connect_timeout",
        message=_("源端 connect_timeout ≥ 10") if ok else _("源端 connect_timeout 小于 10"),
        level=CheckLevel.FAIL,
        details={"source": value, "required": DTS_PRECHECK_CONNECT_TIMEOUT_MIN},
    )


def _check_long_sql(ctx: CheckContext) -> CheckResult:
    sql = (
        "SELECT ID, USER, HOST, DB, TIME, STATE, LEFT(INFO, 200) AS INFO "
        "FROM information_schema.PROCESSLIST "
        "WHERE COMMAND NOT IN ('Sleep', 'Binlog Dump', 'Binlog Dump GTID', 'Daemon') "
        f"AND TIME > {DTS_PRECHECK_LONG_SQL_SECONDS} "
        "AND USER NOT IN ('system user', 'event_scheduler')"
    )
    rows = ctx.source.query(sql)
    displayed = []
    for row in rows:
        displayed.append(
            {
                "id": _row_get(row, "ID", "id"),
                "user": _row_get(row, "USER", "user"),
                "host": _row_get(row, "HOST", "host"),
                "db": _row_get(row, "DB", "db"),
                "time": _row_get(row, "TIME", "time"),
                "state": _row_get(row, "STATE", "state"),
                "info": _row_get(row, "INFO", "info"),
            }
        )
        if len(displayed) >= DTS_PRECHECK_DISPLAY_LIMIT:
            break
    total = len(rows)
    ok = total == 0
    return CheckResult(
        ok=ok,
        code="instance_vars.long_sql",
        message=_("源端无长耗时 SQL") if ok else _("源端存在 {} 条长耗时 SQL").format(total),
        level=CheckLevel.WARN,
        details={
            "threshold_seconds": DTS_PRECHECK_LONG_SQL_SECONDS,
            "total": total,
            "queries": displayed,
            "truncated": total > DTS_PRECHECK_DISPLAY_LIMIT,
        },
    )


@register("instance_vars", _("部分实例参数检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    results = []
    try:
        source_vars = ctx.source.global_variables(list(_VAR_NAMES))
        target_vars = ctx.target.global_variables(list(_VAR_NAMES))
        results.append(_check_row_format(ctx))
        results.append(_check_lower_case(source_vars, target_vars))
        # results.append(_check_target_packet(target_vars))  # 暂缓
        results.append(_check_connect_timeout(source_vars))
        results.append(_check_long_sql(ctx))
    except PrecheckCollectError as exc:
        return [
            CheckResult(
                ok=False,
                code="instance_vars.collect_error",
                message=_("实例参数采集失败: {}").format(exc),
                level=CheckLevel.FAIL,
            )
        ]
    return results
