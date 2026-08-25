# -*- coding: utf-8 -*-
"""从 SyncScope 抽出源对象 / 落地对象，并判断包含式重叠。

供迁移单据校验复用；与创建任务同一套 table_migrate_rule 白名单。
"""
from backend.flow.utils.mysql.dts.migrate_helper import _build_table_migrate_rules
from backend.flow.utils.mysql.dts.migrate_plan import SyncScope

ObjectKey = tuple[str, str]


def _norm(name: str) -> str:
    return (name or "").strip() or "*"


def _is_star(name: str) -> bool:
    return _norm(name) == "*"


def _is_pattern(name: str) -> bool:
    """除整段 * 外，含 * 或 % 的视为无法精确差集的通配。"""
    text = _norm(name)
    if text == "*":
        return False
    return "*" in text or "%" in text


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


def source_objects(scope: SyncScope) -> set[ObjectKey]:
    """源端 (schema, table)。空 scope 得到空集合（表示没有白名单，不是全库）。"""
    rules = _build_table_migrate_rules("", scope)
    return {(_norm(rule.source.schema), _norm(rule.source.table)) for rule in rules}


def landing_objects(scope: SyncScope) -> set[ObjectKey]:
    """目标端落地 (schema, table)。target 缺省回落源库/源表。"""
    keys: set[ObjectKey] = set()
    for rule in _build_table_migrate_rules("", scope):
        src_schema = _norm(rule.source.schema)
        src_table = _norm(rule.source.table)
        target = rule.target
        schema = _norm(target.schema) if target and target.schema else src_schema
        table = _norm(target.table) if target and target.table else src_table
        keys.add((schema, table))
    return keys


def objects_overlap(left: set[ObjectKey], right: set[ObjectKey]) -> bool:
    """两集合是否可能覆盖同一对象。任一侧 schema=* 盖住全部；命名库 table=* 盖住该库所有表。"""
    if not left or not right:
        return False
    for left_key in left:
        for right_key in right:
            if _pair_overlap(left_key, right_key):
                return True
    return False
