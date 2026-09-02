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
from backend.flow.utils.mysql.dts.precheck.collector import InstanceCollector, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.constants import DTS_PRECHECK_DISPLAY_LIMIT
from backend.flow.utils.mysql.dts.precheck.scope import filter_tables_for_database, resolve_migration_databases
from backend.flow.utils.mysql.dts.precheck.sqlutil import quote_str_list


def _row_get(row: dict, *keys):
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def _normalize_pair(charset, collation) -> tuple[str, str] | None:
    charset_text = ("" if charset is None else str(charset)).strip()
    collation_text = ("" if collation is None else str(collation)).strip()
    if not charset_text or not collation_text:
        return None
    return charset_text, collation_text


def _load_source_pairs(
    collector: InstanceCollector, databases: list[str], tables: list[str] | None
) -> list[tuple[str, str, str]]:
    if tables is not None and not tables:
        return []
    schema_in = quote_str_list(databases)
    table_filter = ""
    if tables is not None:
        table_filter = " AND t.TABLE_NAME IN {}".format(quote_str_list(tables))
        column_table_filter = " AND col.TABLE_NAME IN {}".format(quote_str_list(tables))
    else:
        column_table_filter = ""
    sql = (
        "SELECT CHARACTER_SET_NAME, COLLATION_NAME, MIN(sample) AS sample FROM ("
        "SELECT c.CHARACTER_SET_NAME, t.TABLE_COLLATION AS COLLATION_NAME, "
        "CONCAT(t.TABLE_SCHEMA, '.', t.TABLE_NAME) AS sample "
        "FROM information_schema.TABLES t "
        "JOIN information_schema.COLLATION_CHARACTER_SET_APPLICABILITY c "
        "ON c.COLLATION_NAME = t.TABLE_COLLATION "
        "WHERE t.TABLE_TYPE = 'BASE TABLE' AND t.TABLE_SCHEMA IN {schemas}{table_filter} "
        "UNION ALL "
        "SELECT col.CHARACTER_SET_NAME, col.COLLATION_NAME, "
        "CONCAT(col.TABLE_SCHEMA, '.', col.TABLE_NAME) AS sample "
        "FROM information_schema.COLUMNS col "
        "JOIN information_schema.TABLES t "
        "ON t.TABLE_SCHEMA = col.TABLE_SCHEMA AND t.TABLE_NAME = col.TABLE_NAME "
        "WHERE t.TABLE_TYPE = 'BASE TABLE' AND col.TABLE_SCHEMA IN {schemas}{column_table_filter} "
        "AND col.CHARACTER_SET_NAME IS NOT NULL AND col.COLLATION_NAME IS NOT NULL"
        ") x GROUP BY CHARACTER_SET_NAME, COLLATION_NAME"
    ).format(schemas=schema_in, table_filter=table_filter, column_table_filter=column_table_filter)
    pairs = []
    for row in collector.query(sql):
        pair = _normalize_pair(
            _row_get(row, "CHARACTER_SET_NAME", "charset_name"),
            _row_get(row, "COLLATION_NAME", "collation_name"),
        )
        if pair is None:
            continue
        sample = _row_get(row, "sample") or ""
        pairs.append((pair[0], pair[1], str(sample)))
    return pairs


def _load_target_pairs(collector: InstanceCollector) -> set[tuple[str, str]]:
    rows = collector.query("SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLLATIONS")
    keys = set()
    for row in rows:
        pair = _normalize_pair(
            _row_get(row, "CHARACTER_SET_NAME", "charset_name"),
            _row_get(row, "COLLATION_NAME", "collation_name"),
        )
        if pair:
            keys.add((pair[0].lower(), pair[1].lower()))
    return keys


def _resolve_table_names(ctx: CheckContext, databases: list[str]) -> list[str] | None:
    """未限定表时返回 None；否则返回去重后的具体表名列表。"""
    if not ctx.scope.source_tables:
        return None
    sql = (
        "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA IN {}"
    ).format(quote_str_list(databases))
    by_db: dict[str, list[str]] = {database: [] for database in databases}
    for row in ctx.source.query(sql):
        schema = str(_row_get(row, "TABLE_SCHEMA", "table_schema") or "")
        table = str(_row_get(row, "TABLE_NAME", "table_name") or "")
        if schema in by_db and table:
            by_db[schema].append(table)
    selected = []
    for database in databases:
        for table in filter_tables_for_database(database, by_db.get(database, []), ctx.scope):
            if table not in selected:
                selected.append(table)
    return selected


@register("charset_collation", _("字符集/排序集检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    try:
        databases = resolve_migration_databases(ctx.scope, ctx.source.user_schemas())
        tables = _resolve_table_names(ctx, databases)
        source_pairs = _load_source_pairs(ctx.source, databases, tables)
        target_keys = _load_target_pairs(ctx.target)
    except PrecheckCollectError as exc:
        return [
            CheckResult(
                ok=False,
                code="charset_collation.collect_error",
                message=_("字符集/排序集采集失败: {}").format(exc),
                level=CheckLevel.FAIL,
            )
        ]

    missing = []
    seen = set()
    for charset, collation, sample in source_pairs:
        key = (charset.lower(), collation.lower())
        if key in target_keys or key in seen:
            continue
        seen.add(key)
        missing.append({"charset": charset, "collation": collation, "sample": sample})

    total = len(missing)
    ok = total == 0
    return [
        CheckResult(
            ok=ok,
            code="charset_collation.supported",
            message=(_("源端待迁移库表的字符集/排序集目标端均支持") if ok else _("目标端不支持源端使用的 {} 组字符集/排序集").format(total)),
            level=CheckLevel.FAIL,
            details={
                "databases": databases,
                "tables": tables,
                "total": total,
                "missing": missing[:DTS_PRECHECK_DISPLAY_LIMIT],
                "truncated": total > DTS_PRECHECK_DISPLAY_LIMIT,
            },
        )
    ]
