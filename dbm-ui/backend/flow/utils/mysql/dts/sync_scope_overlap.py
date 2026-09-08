# -*- coding: utf-8 -*-
"""从 SyncScope 抽出源对象 / 落地对象，并判断包含式重叠。

同名：do_dbs × do_tables 笛卡尔积（表项 schema=* 时 table 套到各库），ignore 用可能相交判断做剔除。
重名：仍用 table_routes 的源/目标对象。空对象集合表示拒单，不表示全库。
"""
from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase

from backend.flow.utils.mysql.dts.migrate_plan import SyncScope, TableRoute

ObjectKey = tuple[str, str]


@dataclass(frozen=True)
class ScopeObjectSet:
    includes: frozenset[ObjectKey]
    ignore_dbs: tuple[str, ...] = ()
    ignore_tables: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.includes)


def _norm(name: str) -> str:
    return (name or "").strip() or "*"


def _is_star(name: str) -> bool:
    return _norm(name) == "*"


def _is_pattern(name: str) -> bool:
    """除整段 * 外，含 * 或 % 或 ? 的视为无法精确差集的通配。"""
    text = _norm(name)
    if text == "*":
        return False
    return "*" in text or "%" in text or "?" in text


def _names_may_intersect(left: str, right: str) -> bool:
    left_name, right_name = _norm(left), _norm(right)
    if _is_star(left_name) or _is_star(right_name):
        return True
    if left_name == right_name:
        return True
    if _is_pattern(left_name) or _is_pattern(right_name):
        return True
    return False


def _pair_overlap(left: ObjectKey, right: ObjectKey) -> bool:
    return _names_may_intersect(left[0], right[0]) and _names_may_intersect(left[1], right[1])


def _name_ignored(name: str, ignores: tuple[str, ...] | list[str]) -> bool:
    """精确名被 ignore 命中则剔除；通配 include 不会被精确 ignore 整段抹掉。"""
    text = _norm(name)
    normalized_ignores = [_norm(item) for item in (ignores or [])]
    if "*" in normalized_ignores or text in normalized_ignores:
        return True
    if _is_star(text) or _is_pattern(text):
        return False
    for ign_name in normalized_ignores:
        if fnmatchcase(text, ign_name.replace("%", "*")):
            return True
    return False


def _key_ignored(
    key: ObjectKey, ignore_dbs: tuple[str, ...] | list[str], ignore_tables: tuple[str, ...] | list[str]
) -> bool:
    return _name_ignored(key[0], ignore_dbs) or _name_ignored(key[1], ignore_tables)


def _route_source_key(route: TableRoute) -> ObjectKey:
    return (_norm(route.source_schema()), _norm(route.source_table_name()))


def _route_landing_key(route: TableRoute) -> ObjectKey:
    src_schema, src_table = _route_source_key(route)
    schema = _norm(route.target_db) if (route.target_db or "").strip() else src_schema
    table = _norm(route.target_table) if (route.target_table or "").strip() else src_table
    return (schema, table)


def _table_names(items) -> list[str]:
    names: list[str] = []
    for item in items or []:
        if isinstance(item, dict):
            names.append(_norm(item.get("table") or item.get("tablename") or "*"))
        elif isinstance(item, str) and item.strip():
            names.append(_norm(item))
    return names


def source_object_set(scope: SyncScope) -> ScopeObjectSet:
    ignore_dbs = tuple(scope.ignore_dbs or [])
    ignore_tables = tuple(_table_names(scope.ignore_tables))
    if scope.table_routes:
        includes = frozenset(_route_source_key(route) for route in scope.table_routes)
        return ScopeObjectSet(includes=includes, ignore_dbs=ignore_dbs, ignore_tables=ignore_tables)

    dbs = [_norm(db) for db in (scope.do_dbs or []) if (db or "").strip()]
    tables = _table_names(scope.do_tables)
    if not dbs or not tables:
        return ScopeObjectSet(includes=frozenset())
    includes = frozenset(
        (db, tb) for db in dbs for tb in tables if not _key_ignored((db, tb), ignore_dbs, ignore_tables)
    )
    return ScopeObjectSet(includes=includes, ignore_dbs=ignore_dbs, ignore_tables=ignore_tables)


def landing_object_set(scope: SyncScope) -> ScopeObjectSet:
    if scope.table_routes:
        ignore_dbs = tuple(scope.ignore_dbs or [])
        ignore_tables = tuple(_table_names(scope.ignore_tables))
        includes = frozenset(_route_landing_key(route) for route in scope.table_routes)
        return ScopeObjectSet(includes=includes, ignore_dbs=ignore_dbs, ignore_tables=ignore_tables)
    return source_object_set(scope)


def objects_overlap(left, right) -> bool:
    """两集合是否可能覆盖同一对象。任一侧 schema=* 盖住全部；命名库 table=* 盖住该库所有表。"""
    left_set = left if isinstance(left, ScopeObjectSet) else ScopeObjectSet(includes=frozenset(left or []))
    right_set = right if isinstance(right, ScopeObjectSet) else ScopeObjectSet(includes=frozenset(right or []))
    if not left_set.includes or not right_set.includes:
        return False
    for left_key in left_set.includes:
        for right_key in right_set.includes:
            if not _pair_overlap(left_key, right_key):
                continue
            if _key_ignored(right_key, left_set.ignore_dbs, left_set.ignore_tables):
                continue
            if _key_ignored(left_key, right_set.ignore_dbs, right_set.ignore_tables):
                continue
            return True
    return False
