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

from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from django.utils.translation import gettext as _

from backend.flow.consts import SYSTEM_DBS
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError


@dataclass
class SyncScope:
    do_dbs: list[str] = field(default_factory=list)
    ignore_dbs: list[str] = field(default_factory=list)
    do_tables: list[dict] = field(default_factory=list)
    ignore_tables: list[dict] = field(default_factory=list)
    table_routes: list[dict] = field(default_factory=list)
    source_tables: list[dict] = field(default_factory=list)


def _table_db(item: dict) -> str:
    return str(item.get("db") or item.get("source_db") or "")


def _expand(patterns: list[str], schemas: list[str]) -> set[str]:
    return {schema for schema in schemas if any(fnmatchcase(schema, pattern) for pattern in patterns)}


def resolve_schemas(scope: SyncScope, all_user_schemas: list[str]) -> list[str]:
    user_schemas = sorted(set(all_user_schemas) - set(SYSTEM_DBS))

    if scope.table_routes:
        source_patterns = [
            str(route.get("source_db_pattern") or route.get("source_db") or "")
            for route in scope.table_routes
            if route.get("source_db_pattern") or route.get("source_db")
        ]
        selected = _expand(source_patterns, user_schemas)
    else:
        include_patterns = [pattern for pattern in scope.do_dbs if pattern]
        include_patterns.extend(db for db in (_table_db(item) for item in scope.do_tables) if db)
        selected = _expand(include_patterns, user_schemas) if include_patterns else set(user_schemas)

        ignore_patterns = [pattern for pattern in scope.ignore_dbs if pattern]
        ignore_patterns.extend(db for db in (_table_db(item) for item in scope.ignore_tables) if db)
        selected -= _expand(ignore_patterns, user_schemas)

    selected -= set(SYSTEM_DBS)
    if not selected:
        raise PrecheckCollectError(_("同步范围解析后没有可检查的用户库"))
    return sorted(selected)


def _normalize_pattern(raw: str) -> str:
    return raw.replace("%", "*")


def _match_names(names: list[str], pattern: str) -> list[str]:
    fnmatch_pattern = _normalize_pattern(pattern)
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


def resolve_migration_databases(scope: SyncScope, all_user_schemas: list[str]) -> list[str]:
    """优先按 source_tables 的库通配解析；否则走 sync_scope / 全部用户库。"""
    user_schemas = sorted(set(all_user_schemas) - set(SYSTEM_DBS))
    if not scope.source_tables:
        return resolve_schemas(scope, user_schemas)

    selected = set()
    for item in scope.source_tables:
        database = str(item.get("db") or "").strip()
        if not database:
            continue
        selected.update(_match_names(user_schemas, database))
    selected -= _expand([pattern for pattern in scope.ignore_dbs if pattern], user_schemas)
    selected -= set(SYSTEM_DBS)
    if not selected:
        raise PrecheckCollectError(_("source_tables 未匹配到源端用户库"))
    return sorted(selected)


def table_patterns_for_database(database: str, scope: SyncScope) -> list[str] | None:
    """
    返回某库应检查的表通配。
    - None: 检查该库全部表（未传 source_tables，或命中条目未指定 tables）
    - list: 按通配过滤表名
    """
    if not scope.source_tables:
        return None
    collected: list[str] = []
    hit = False
    for item in scope.source_tables:
        db_pattern = str(item.get("db") or "").strip()
        if not db_pattern or database not in _match_names([database], db_pattern):
            continue
        hit = True
        patterns = _table_patterns(item)
        if not patterns:
            return None
        for pattern in patterns:
            if pattern not in collected:
                collected.append(pattern)
    if not hit:
        return []
    return collected


def database_ignored(name: str, scope: SyncScope) -> bool:
    patterns = [pattern for pattern in scope.ignore_dbs if pattern]
    return bool(patterns) and bool(_expand(patterns, [name]))


def table_ignored(database: str, table: str, scope: SyncScope) -> bool:
    for item in scope.ignore_tables or []:
        if isinstance(item, str):
            db_pattern, table_pattern = "*", item
        else:
            db_pattern = str(item.get("schema") or item.get("db") or "*")
            table_pattern = str(item.get("table") or item.get("tablename") or "")
        if not table_pattern:
            continue
        if db_pattern not in ("", "*") and database not in _match_names([database], db_pattern):
            continue
        if table in _match_names([table], table_pattern):
            return True
    return False


def filter_tables_for_database(database: str, tables: list[str], scope: SyncScope) -> list[str]:
    patterns = table_patterns_for_database(database, scope)
    if patterns is None:
        selected = list(tables)
    else:
        selected = []
        for pattern in patterns:
            for table in _match_names(tables, pattern):
                if table not in selected:
                    selected.append(table)
    return [table for table in selected if not table_ignored(database, table, scope)]
