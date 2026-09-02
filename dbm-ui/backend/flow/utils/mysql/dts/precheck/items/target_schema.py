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

from fnmatch import fnmatchcase

from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.collector import InstanceCollector, PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.scope import database_ignored, table_ignored
from backend.flow.utils.mysql.dts.precheck.sqlutil import quote_str_list

DISPLAY_LIMIT = 50


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _pattern(raw: str) -> str:
    """单据通配：* 和 % 匹配任意长度，? 匹配一个字符。"""
    return raw.replace("%", "*")


def _matched(names: list[str], pattern: str) -> list[str]:
    fnmatch_pattern = _pattern(pattern)
    return [name for name in names if fnmatchcase(name, fnmatch_pattern)]


def _table_patterns(item: dict) -> list[str]:
    patterns = []
    for name in item.get("tables") or []:
        text = str(name).strip()
        if text and text not in patterns:
            patterns.append(text)
    single = str(item.get("table") or "").strip()
    if single and single not in patterns:
        patterns.append(single)
    return patterns


def _specs(source_tables: list[dict]) -> list[dict]:
    specs = []
    for item in source_tables or []:
        database = str(item.get("db") or "").strip()
        if not database:
            continue
        specs.append({"db": database, "tables": _table_patterns(item)})
    return specs


def _rows_by_schema(rows: list[dict]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for row in rows or []:
        schema = row.get("TABLE_SCHEMA") or row.get("table_schema")
        table = row.get("TABLE_NAME") or row.get("table_name")
        if not schema or not table:
            continue
        grouped.setdefault(str(schema), set()).add(str(table))
    return grouped


def _load_tables(collector: InstanceCollector, databases: list[str]) -> dict[str, set[str]]:
    sql = (
        "SELECT TABLE_SCHEMA, TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA IN {}"
    ).format(quote_str_list(databases))
    return _rows_by_schema(collector.query(sql))


@register("target_schema", _("待迁移库表冲突检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    """
    确认源端有待迁移库/表（可导出），目标端没有同名库/表（导入不冲突）。

    - 只传 db：源端库必须存在，目标端同名库必须不存在。
    - 传 tables：源端表必须存在，目标端同名表必须不存在；目标端已有库本身不算冲突。
    """
    specs = _specs(ctx.scope.source_tables or [])
    if not specs:
        return [
            CheckResult(
                ok=False,
                code="target_schema.empty",
                message=_("未指定待迁移的源库表"),
                level=CheckLevel.FAIL,
            )
        ]
    try:
        source_databases = ctx.source.user_schemas()
        target_databases = set(ctx.target.user_schemas())
        source_missing_databases = []
        target_conflict_databases = []
        resolved: list[tuple[dict, list[str]]] = []
        for spec in specs:
            matched = [
                database
                for database in _matched(source_databases, spec["db"])
                if not database_ignored(database, ctx.scope)
            ]
            if not matched:
                if _matched(source_databases, spec["db"]):
                    continue
                source_missing_databases.append(spec["db"])
                continue
            resolved.append((spec, matched))
            if not spec["tables"]:
                target_conflict_databases.extend(database for database in matched if database in target_databases)

        table_databases = sorted({database for spec, matched in resolved if spec["tables"] for database in matched})
        source_tables = _load_tables(ctx.source, table_databases) if table_databases else {}
        target_table_databases = [database for database in table_databases if database in target_databases]
        target_tables = _load_tables(ctx.target, target_table_databases) if target_table_databases else {}
    except PrecheckCollectError as exc:
        return [
            CheckResult(
                ok=False,
                code="target_schema.collect_error",
                message=_("查询源/目标库表失败: {}").format(exc),
                level=CheckLevel.FAIL,
            )
        ]

    source_missing_tables = []
    target_conflict_tables = []
    for spec, matched in resolved:
        if not spec["tables"]:
            continue
        for database in matched:
            for pattern in spec["tables"]:
                tables = _matched(sorted(source_tables.get(database, set())), pattern)
                if not tables:
                    source_missing_tables.append(f"{database}.{pattern}")
                    continue
                if database not in target_databases:
                    continue
                target_conflict_tables.extend(
                    f"{database}.{table}"
                    for table in tables
                    if not table_ignored(database, table, ctx.scope) and table in target_tables.get(database, set())
                )

    source_missing_databases = _unique(source_missing_databases)
    source_missing_tables = _unique(source_missing_tables)
    target_conflict_databases = _unique(target_conflict_databases)
    target_conflict_tables = _unique(target_conflict_tables)
    details = {
        "source_missing_databases": source_missing_databases[:DISPLAY_LIMIT],
        "source_missing_tables": source_missing_tables[:DISPLAY_LIMIT],
        "target_conflict_databases": target_conflict_databases[:DISPLAY_LIMIT],
        "target_conflict_tables": target_conflict_tables[:DISPLAY_LIMIT],
    }
    total = (
        len(source_missing_databases)
        + len(source_missing_tables)
        + len(target_conflict_databases)
        + len(target_conflict_tables)
    )
    if total:
        return [
            CheckResult(
                ok=False,
                code="target_schema.conflict",
                message=_("源端缺少 {} 个待迁移对象，或目标端存在 {} 个同名冲突").format(
                    len(source_missing_databases) + len(source_missing_tables),
                    len(target_conflict_databases) + len(target_conflict_tables),
                ),
                level=CheckLevel.FAIL,
                details={**details, "total": total, "truncated": total > DISPLAY_LIMIT},
            )
        ]
    checked_tables = any(spec["tables"] for spec, _matched_databases in resolved)
    return [
        CheckResult(
            ok=True,
            code="target_schema.ok",
            message=_("源端有待迁移表且目标端无同名冲突") if checked_tables else _("源端有待迁移库且目标端无同名冲突"),
            level=CheckLevel.FAIL,
            details=details,
        )
    ]
