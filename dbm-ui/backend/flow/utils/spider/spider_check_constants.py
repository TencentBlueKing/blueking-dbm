#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spider检查相关常量定义

本模块定义了Spider数据库检查过程中使用的各种常量，
包括检查类型、默认配置等，确保代码的一致性和可维护性。
"""

from typing import Dict, List

from django.utils.translation import gettext as _

# ================================
# 检查类型常量定义
# ================================

# 基础检查类型
TABLE_CHECK = "table_check"
COLUMN_CHECK = "column_check"
INDEX_CHECK = "index_check"
VIEW_CHECK = "view_check"
TRIGGER_CHECK = "trigger_check"
ROUTINE_CHECK = "routine_check"

# 检查类型列表
ALL_CHECK_TYPES = [
    TABLE_CHECK,
    COLUMN_CHECK,
    INDEX_CHECK,
    VIEW_CHECK,
    TRIGGER_CHECK,
    ROUTINE_CHECK,
]

# 常用检查类型组合
BASIC_CHECK_TYPES = [TABLE_CHECK, COLUMN_CHECK, INDEX_CHECK]
EXTENDED_CHECK_TYPES = [VIEW_CHECK, TRIGGER_CHECK, ROUTINE_CHECK]
DEFAULT_CHECK_TYPES = BASIC_CHECK_TYPES

# ================================
# 检查类型描述映射
# ================================

CHECK_TYPE_DESCRIPTIONS = {
    TABLE_CHECK: _("表名"),
    COLUMN_CHECK: _("列名"),
    INDEX_CHECK: _("索引名"),
    VIEW_CHECK: _("视图名"),
    TRIGGER_CHECK: _("触发器名"),
    ROUTINE_CHECK: _("函数/存储过程名"),
}

# 检查类型详细说明
CHECK_TYPE_DETAILS = {
    TABLE_CHECK: {
        "name": _("表名关键字冲突检查"),
        "description": _("检查表名是否与数据库关键字冲突"),
        "priority": "high",
        "sql_table": "information_schema.tables",
        "sql_column": "TABLE_NAME",
    },
    COLUMN_CHECK: {
        "name": _("列名关键字冲突检查"),
        "description": _("检查列名是否与数据库关键字冲突"),
        "priority": "high",
        "sql_table": "information_schema.columns",
        "sql_column": "COLUMN_NAME",
    },
    INDEX_CHECK: {
        "name": _("索引名关键字冲突检查"),
        "description": _("检查索引名是否与数据库关键字冲突"),
        "priority": "medium",
        "sql_table": "information_schema.statistics",
        "sql_column": "INDEX_NAME",
    },
    VIEW_CHECK: {
        "name": _("视图名关键字冲突检查"),
        "description": _("检查视图名是否与数据库关键字冲突"),
        "priority": "medium",
        "sql_table": "information_schema.views",
        "sql_column": "TABLE_NAME",
    },
    TRIGGER_CHECK: {
        "name": _("触发器名关键字冲突检查"),
        "description": _("检查触发器名是否与数据库关键字冲突"),
        "priority": "low",
        "sql_table": "information_schema.triggers",
        "sql_column": "TRIGGER_NAME",
    },
    ROUTINE_CHECK: {
        "name": _("函数/存储过程名关键字冲突检查"),
        "description": _("检查函数和存储过程名是否与数据库关键字冲突"),
        "priority": "low",
        "sql_table": "information_schema.routines",
        "sql_column": "ROUTINE_NAME",
    },
}

# ================================
# 检查配置常量
# ================================

# 默认检查配置
DEFAULT_CHECK_CONFIG = {
    "check_types": DEFAULT_CHECK_TYPES,
    "force_check": False,
    "fail_on_conflict": True,
    "generate_report": True,
    "include_suggestions": True,
}

# 检查优先级映射
CHECK_PRIORITY_MAP = {
    "high": [TABLE_CHECK, COLUMN_CHECK],
    "medium": [INDEX_CHECK, VIEW_CHECK],
    "low": [TRIGGER_CHECK, ROUTINE_CHECK],
}

# ================================
# 工具函数
# ================================


def get_check_type_description(check_type: str) -> str:
    """
    获取检查类型的描述.

    Args:
        check_type: 检查类型

    Returns:
        str: 检查类型描述
    """
    return CHECK_TYPE_DESCRIPTIONS.get(check_type, check_type)


def get_check_type_details(check_type: str) -> Dict:
    """
    获取检查类型的详细信息.

    Args:
        check_type: 检查类型

    Returns:
        Dict: 检查类型详细信息
    """
    return CHECK_TYPE_DETAILS.get(check_type, {})


def validate_check_types(check_types: List[str]) -> List[str]:
    """
    验证检查类型列表的有效性.

    Args:
        check_types: 检查类型列表

    Returns:
        List[str]: 有效的检查类型列表

    Raises:
        ValueError: 当包含无效检查类型时
    """
    if not check_types:
        return DEFAULT_CHECK_TYPES

    invalid_types = [ct for ct in check_types if ct not in ALL_CHECK_TYPES]
    if invalid_types:
        raise ValueError(_("无效的检查类型: {}. 支持的类型: {}").format(", ".join(invalid_types), ", ".join(ALL_CHECK_TYPES)))

    return check_types


def get_check_types_by_priority(priority: str) -> List[str]:
    """
    根据优先级获取检查类型列表.

    Args:
        priority: 优先级 (high/medium/low)

    Returns:
        List[str]: 对应优先级的检查类型列表
    """
    return CHECK_PRIORITY_MAP.get(priority, [])


def is_high_priority_check(check_type: str) -> bool:
    """
    判断是否为高优先级检查类型.

    Args:
        check_type: 检查类型

    Returns:
        bool: 是否为高优先级
    """
    return check_type in CHECK_PRIORITY_MAP["high"]
