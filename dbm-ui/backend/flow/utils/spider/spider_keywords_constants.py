#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MariaDB 10.3.7相较于Percona 5.5新增的关键字、保留字常量定义

本文件包含了从MariaDB 10.3.7版本中新增的各类关键字，
这些关键字在使用时可能需要用反引号包裹以避免语法冲突。
"""

from typing import List

# MariaDB 10.3.7新增的保留关键字 (13个)
MARIADB_10_3_7_NEW_RESERVED_KEYWORDS: List[str] = [
    "CURRENT_ROLE",  # SQL:2003标准保留关键字，当前角色
    "DELETE_DOMAIN_ID",  # 用于删除域ID
    "DO_DOMAIN_IDS",  # 用于域ID操作
    "EXCEPT",  # SQL标准保留关键字，集合操作
    "IGNORE_DOMAIN_IDS",  # 用于忽略域ID
    "OVER",  # SQL标准保留关键字，窗口函数
    "PAGE_CHECKSUM",  # 用于页校验和
    "PARSE_VCOL_EXPR",  # 用于解析虚拟列表达式
    "RECURSIVE",  # SQL标准保留关键字，递归查询
    "RETURNING",  # SQL标准保留关键字，返回子句
    "STATS_AUTO_RECALC",  # 用于统计信息自动重计算
    "STATS_PERSISTENT",  # 用于持久化统计信息
    "STATS_SAMPLE_PAGES",  # 用于统计信息采样页数
]


# MariaDB 11.4.2相较于10.3.7新增的保留关键字 (14个)
MARIADB_11_4_2_NEW_RESERVED_KEYWORDS: List[str] = [
    "EMPTY",  # SQL:2016标准保留关键字，用于JSON空值处理
    "IGNORED",  # MySQL扩展保留关键字，用于忽略约束
    "JSON_ARRAYAGG",  # JSON聚合函数，将多行聚合成JSON数组
    "JSON_OBJECTAGG",  # JSON聚合函数，将多行聚合成JSON对象
    "JSON_TABLE",  # JSON表函数，将JSON数据转为关系表
    "MINUS",  # Oracle兼容的MINUS集合操作符
    "NESTED",  # SQL标准嵌套关键字
    "ORDINALITY",  # SQL标准序数关键字，用于JSON_TABLE
    "OVERLAPS",  # SQL标准时间段重叠检测操作符
    "PORTION",  # SQL:2016标准保留关键字
    "ROWNUM",  # Oracle兼容行号伪列
    "SKIP",  # MySQL扩展保留关键字，用于查询跳过行数
    "VALIDATION",  # MySQL扩展保留关键字，用于数据验证
    "VISIBLE",  # MySQL 8.0兼容保留关键字，列可见性控制
]

# MariaDB 10.3.7新增的非保留关键字 (90个)
MARIADB_10_3_7_NEW_NON_RESERVED_KEYWORDS: List[str] = [
    "ADMIN",  # MySQL扩展非保留关键字，用于权限管理
    "ALWAYS",  # 用于GENERATED ALWAYS AS语法
    "AUTO",  # 用于自动增量和自动扩展
    "BODY",  # Oracle兼容，PL/SQL中用于定义存储过程体
    "CLOB",  # SQL标准数据类型，字符大对象
    "COLUMN_ADD",  # 用于动态列操作，添加列
    "COLUMN_CHECK",  # 用于动态列检查
    "COLUMN_CREATE",  # 用于动态列创建
    "COLUMN_DELETE",  # 用于动态列删除
    "COLUMN_GET",  # 用于动态列获取
    "CHECKPOINT",  # 用于检查点操作
    "CURRENT",  # 用于当前值操作
    "CURRENT_POS",  # 用于当前位置操作
    "CYCLE",  # SQL标准非保留关键字，用于序列循环
    "DIAGNOSTICS",  # SQL标准非保留关键字，用于诊断信息
    "ELSIF",  # Oracle兼容，PL/SQL中的条件语句
    "EXAMINED",  # 用于EXAMINED关键字
    "EXCHANGE",  # 用于分区交换操作
    "EXCLUDE",  # SQL标准非保留关键字，用于排除操作
    "EXCEPTION",  # SQL标准非保留关键字，异常处理
    "EXPORT",  # 用于导出操作
    "FOLLOWING",  # SQL标准非保留关键字，窗口函数
    "FOLLOWS",  # MySQL扩展，用于触发器顺序
    "FORMAT",  # 用于格式化操作
    "GENERATED",  # 用于生成列
    "GOTO",  # Oracle兼容，PL/SQL中的跳转语句
    "HARD",  # 用于硬链接或硬操作
    "HISTORY",  # MySQL扩展，用于历史表
    "ID",  # MySQL扩展非保留关键字
    "IF_SYM",  # 条件语句关键字
    "IMMEDIATE",  # SQL标准保留关键字
    "INCREMENT",  # 用于增量操作
    "INVISIBLE",  # 用于不可见索引
    "ISOPEN",  # Oracle兼容，游标状态检查
    "JSON",  # JSON数据类型支持
    "LAST_VALUE",  # 窗口函数，获取最后一个值
    "LASTVAL",  # PostgreSQL兼容，序列函数
    "MASTER_DELAY",  # 用于主从复制延迟
    "MASTER_GTID_POS",  # 用于GTID位置
    "MASTER_SSL_CRL",  # 用于SSL证书吊销列表
    "MASTER_SSL_CRLPATH",  # 用于SSL证书路径
    "MASTER_USE_GTID",  # 用于GTID复制
    "MAX_STATEMENT_TIME",  # 用于最大语句执行时间
    "MINVALUE",  # 用于序列最小值
    "NOMAXVALUE",  # 用于序列无最大值
    "NOMINVALUE",  # 用于序列无最小值
    "NOCACHE",  # 用于序列无缓存
    "NOCYCLE",  # 用于序列无循环
    "NOWAIT",  # 用于无等待操作
    "NUMBER",  # SQL标准非保留关键字
    "OF",  # SQL标准保留关键字
    "ONLINE",  # 用于在线操作
    "ONLY",  # SQL标准保留关键字
    "OTHERS",  # SQL标准非保留关键字
    "PACKAGE",  # Oracle兼容，包定义
    "PERIOD",  # SQL标准保留关键字，用于系统时间
    "PERSISTENT",  # 用于持久化操作
    "PRECEDES",  # MySQL扩展，用于触发器顺序
    "PRECEDING",  # SQL标准非保留关键字，窗口函数
    "PREVIOUS",  # 用于前一个值操作
    "RAISE",  # Oracle兼容，PL/SQL中的异常抛出
    "RAW",  # Oracle兼容，原始数据类型
    "RESTART",  # 用于重启操作
    "RETURNED_SQLSTATE",  # SQL标准非保留关键字
    "REUSE",  # Oracle兼容，重用操作
    "REVERSE",  # 用于反向操作
    "ROLE",  # 用于角色管理
    "ROWCOUNT",  # Oracle兼容，行计数
    "ROWTYPE",  # Oracle兼容，PL/SQL中的行类型
    "ROW_COUNT",  # SQL标准非保留关键字
    "SEQUENCE",  # 用于序列操作
    "SETVAL",  # PostgreSQL兼容，序列函数
    "SLAVES",  # 用于从服务器管理
    "SLAVE_POS",  # 用于从服务器位置
    "SOFT",  # 用于软操作
    "STATEMENT",  # 用于语句级操作
    "STORED",  # 用于存储过程/函数
    "SYSTEM",  # SQL标准保留关键字
    "SYSTEM_TIME",  # SQL标准保留关键字，系统时间
    "TIES",  # SQL标准非保留关键字
    "TRANSACTIONAL",  # 用于事务操作
    "UNBOUNDED",  # SQL标准非保留关键字
    "VIA",  # 用于通过某个路径
    "VIRTUAL",  # 用于虚拟列
    "VERSIONING",  # SQL标准保留关键字，版本控制
    "WEIGHT_STRING",  # 用于权重字符串
    "WINDOW",  # SQL标准保留关键字，窗口函数
    "WITHIN",  # 用于范围内操作
    "WITHOUT",  # SQL标准保留关键字
]

# MariaDB 11.4.2相较于10.3.7新增的非保留关键字 (13个)
MARIADB_11_4_2_NEW_NON_RESERVED_KEYWORDS: List[str] = [
    "ACCOUNT",  # MySQL扩展非保留关键字，用于账户管理
    "CHANNEL",  # MySQL扩展非保留关键字，用于复制通道管理
    "EXPIRE",  # MySQL扩展非保留关键字，用于密码过期策略管理
    "FEDERATED",  # MariaDB权限关键字，管理FEDERATED存储引擎权限
    "LOCKED",  # MySQL扩展非保留关键字，用于表锁定状态管理
    "MASTER_DEMOTE_TO_REPLICA",  # MySQL扩展非保留关键字，用于主从复制管理
    "MONITOR",  # MariaDB权限关键字，用于监控权限管理
    "NEVER",  # MySQL扩展非保留关键字，通用否定语义关键字
    "REPLAY",  # MariaDB权限关键字，用于复制回放权限管理
    "SQL_AFTER_GTIDS",  # MySQL扩展非保留关键字，用于GTID复制位置指定
    "SQL_BEFORE_GTIDS",  # MySQL扩展非保留关键字，用于GTID复制位置指定
    "STAGE",  # MySQL扩展非保留关键字，用于复制阶段管理
    "THREADS",  # MySQL扩展非保留关键字，用于线程管理
]

# Oracle兼容模式新增的保留关键字对照 (12对)
ORACLE_COMPATIBILITY_RESERVED_KEYWORDS: List[str] = [
    "BODY",  # PL/SQL包体定义
    "CONTINUE",  # 循环控制语句
    "DECLARE",  # 变量声明
    "ELSIF",  # 条件判断
    "EXCEPTION",  # 异常处理
    "EXIT",  # 退出循环
    "GOTO",  # 无条件跳转
    "OTHERS",  # 异常捕获
    "PACKAGE",  # 包定义
    "RAISE",  # 异常抛出
    "RETURN",  # 返回值
    "ROWTYPE",  # 行类型定义
]

# Oracle兼容模式数据类型关键字 (5个)
ORACLE_COMPATIBILITY_DATA_TYPE_KEYWORDS: List[str] = [
    "BLOB",  # 二进制大对象
    "CLOB",  # 字符大对象
    "NUMBER",  # 数值类型
    "RAW",  # 原始二进制数据
    "VARCHAR2",  # 变长字符串
]

# MariaDB 10.3.7新增的函数关键字 (16个，均为非保留关键字)
MARIADB_10_3_7_NEW_FUNCTION_KEYWORDS: List[str] = [
    "CUME_DIST",  # SQL标准窗口函数，累积分布
    "DATE_FORMAT",  # MySQL函数，日期格式化
    "DECODE",  # Oracle兼容函数，解码操作
    "DENSE_RANK",  # SQL标准窗口函数，密集排名
    "FIRST_VALUE",  # SQL标准窗口函数，第一个值
    "LAG",  # SQL标准窗口函数，滞后值
    "LEAD",  # SQL标准窗口函数，领先值
    "MEDIAN",  # SQL标准窗口函数，中位数
    "NTH_VALUE",  # SQL标准窗口函数，第N个值
    "NTILE",  # SQL标准窗口函数，分组
    "PERCENT_RANK",  # SQL标准窗口函数，百分比排名
    "PERCENTILE_CONT",  # SQL标准窗口函数，连续百分位
    "PERCENTILE_DISC",  # SQL标准窗口函数，离散百分位
    "RANK",  # SQL标准窗口函数，排名
    "ROW_NUMBER",  # SQL标准窗口函数，行号
    "TRIM_ORACLE",  # Oracle兼容的TRIM函数
]


# 从Percona 5.5中删除的关键字 (3个)
PERCONA_REMOVED_KEYWORDS: List[str] = [
    "GCS",  # Percona扩展，GCS行格式
    "GCS_DYNAMIC",  # Percona扩展，GCS动态行格式
    "SPIDER_RONE_SHARD",  # Percona扩展，Spider分片
]

# 可能影响数据类型和约束的关键字
DATA_TYPE_CONSTRAINT_AFFECTING_KEYWORDS: List[str] = [
    "STORED",  # 生成列实际存储，能加索引、约束
    "VIRTUAL",  # 生成列不存储，不能加普通索引、NOT NULL
    "PERSISTENT",  # 历史别名，等价于STORED
    "INVISIBLE",  # 列不出现在SELECT *，不影响类型/长度/约束
    "SEQUENCE",  # 新对象类型，影响主键生成方式
    "MINVALUE",  # 影响序列生成的数值范围
    "MAXVALUE",  # 影响序列生成的数值范围
    "JSON",  # 实际为LONGTEXT，最大4GB，支持JSON函数
]

# 所有新增关键字的合集（用于快速检查）
ALL_MARIADB_NEW_KEYWORDS: List[str] = (
    MARIADB_10_3_7_NEW_NON_RESERVED_KEYWORDS
    + MARIADB_10_3_7_NEW_RESERVED_KEYWORDS
    + MARIADB_10_3_7_NEW_FUNCTION_KEYWORDS
    + MARIADB_11_4_2_NEW_RESERVED_KEYWORDS
    + MARIADB_11_4_2_NEW_NON_RESERVED_KEYWORDS
    + ORACLE_COMPATIBILITY_RESERVED_KEYWORDS
    + ORACLE_COMPATIBILITY_DATA_TYPE_KEYWORDS
)

# 需要特别注意的保留关键字（使用时必须用反引号包裹）
CRITICAL_RESERVED_KEYWORDS: List[str] = (
    MARIADB_10_3_7_NEW_RESERVED_KEYWORDS
    + MARIADB_11_4_2_NEW_RESERVED_KEYWORDS
    + ORACLE_COMPATIBILITY_RESERVED_KEYWORDS
)


def is_mariadb_keyword(word: str) -> bool:
    """
    检查给定的单词是否为MariaDB新增的关键字

    Args:
        word: 要检查的单词

    Returns:
        bool: 如果是MariaDB新增关键字返回True，否则返回False
    """
    return word.upper() in [kw.upper() for kw in ALL_MARIADB_NEW_KEYWORDS]


def is_reserved_keyword(word: str) -> bool:
    """
    检查给定的单词是否为保留关键字（使用时需要反引号包裹）

    Args:
        word: 要检查的单词

    Returns:
        bool: 如果是保留关键字返回True，否则返回False
    """
    return word.upper() in [kw.upper() for kw in CRITICAL_RESERVED_KEYWORDS]


def escape_keyword_if_needed(word: str) -> str:
    """
    如果单词是保留关键字，则用反引号包裹

    Args:
        word: 要检查和转义的单词

    Returns:
        str: 转义后的单词（如果需要的话）
    """
    if is_reserved_keyword(word):
        return f"`{word}`"
    return word
