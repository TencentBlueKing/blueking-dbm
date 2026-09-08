# -*- coding: utf-8 -*-
"""从 SyncScope 抽出源端 DRS 存在性查询入参。"""
from collections.abc import Iterable
from dataclasses import dataclass

from backend.flow.utils.mysql.dts.migrate_plan import SyncScope


@dataclass(frozen=True)
class SourceExistQuery:
    """DRS 查询入参。表全是 * 或未填写时只检查库。"""

    dbs: list[str]
    ignore_dbs: list[str]
    tables: list[str]
    ignore_tables: list[str]
    need_check_tables: bool


def _norm(name: str) -> str:
    return (name or "").strip()


def _unique_keep_order(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for name in names:
        text = _norm(name)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _table_name(item) -> str:
    if isinstance(item, dict):
        return item.get("table") or item.get("tablename") or "*"
    if isinstance(item, str) and "." in item:
        return item.split(".", 1)[1]
    if isinstance(item, str):
        return item
    return "*"


def scope_to_exist_query(scope: SyncScope) -> SourceExistQuery:
    """抽出用户写的库表通配；table_routes 优先且只读源端。"""
    ignore_dbs = _unique_keep_order(scope.ignore_dbs or [])
    ignore_tables = _unique_keep_order(_table_name(item) for item in (scope.ignore_tables or []))
    if scope.table_routes:
        dbs = _unique_keep_order(route.source_schema() for route in scope.table_routes)
        tables = _unique_keep_order(route.source_table_name() for route in scope.table_routes)
    else:
        dbs = _unique_keep_order(scope.do_dbs or [])
        tables = _unique_keep_order(_table_name(item) for item in (scope.do_tables or []))

    return SourceExistQuery(
        dbs=dbs,
        ignore_dbs=ignore_dbs,
        tables=tables,
        ignore_tables=ignore_tables,
        need_check_tables=any(table != "*" for table in tables),
    )
