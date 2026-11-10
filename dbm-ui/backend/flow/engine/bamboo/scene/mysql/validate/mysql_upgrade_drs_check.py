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
from django.utils.translation import gettext as _

from backend.flow.utils.mysql.mysql_version_parse import major_version_parse, mysql_version_parse

# 和 dbactuator CheckTableUpgrade 同一套版本门槛。
MYSQL_56 = mysql_version_parse("5.6.0")
MYSQL_57 = mysql_version_parse("5.7.0")
MYSQL_80 = mysql_version_parse("8.0.0")


def crosses_major_version(current_version, target_version) -> bool:
    """版本字符串按 5.6、5.7、8.0 比较。目标大版本更高才算跨大版本升级。"""
    current_major = major_version_parse(current_version)[0]
    target_major = major_version_parse(target_version)[0]
    if not current_major or not target_major:
        return False
    return target_major > current_major


_BASE_KEYWORDS = (
    "ACCESSIBLE",
    "LINEAR",
    "MASTER_SSL_VERIFY_SERVER_CERT",
    "RANGE",
    "READ_ONLY",
    "IGNORE_SERVER_IDS",
    "MASTER_HEARTBEAT_PERIOD",
    "MAXVALUE",
    "RESIGNAL",
    "SIGNAL",
    "SLOW",
)
_KEYWORDS_56 = ("GET", "IO_AFTER_GTIDS", "IO_BEFORE_GTIDS", "MASTER_BIND", "PARTITION")
_KEYWORDS_57 = ("GENERATED", "OPTIMIZER_COSTS", "STORED", "VIRTUAL", "PARTITION")
_KEYWORDS_80 = (
    "CUME_DIST",
    "DENSE_RANK",
    "EMPTY",
    "EXCEPT",
    "FIRST_VALUE",
    "GROUPING",
    "GROUPS",
    "JSON_TABLE",
    "LAG",
    "LAST_VALUE",
    "LATERAL",
    "LEAD",
    "NTH_VALUE",
    "NTILE",
    "OF",
    "OVER",
    "PERCENT_RANK",
    "RANK",
    "RECURSIVE",
    "ROW_NUMBER",
    "SYSTEM",
    "WINDOW",
)
_ROUTINE_BLACKLIST = (
    "ExtractValue",
    "FROM_BASE64",
    "GTID_SUBSET",
    "GTID_SUBTRACT",
    "INET6_ATON",
    "INET6_NTOA",
    "IS_IPV4_COMPAT",
    "IS_IPV4_MAPPED",
    "IS_IPV4",
    "IS_IPV6",
    "SQL_THREAD_WAIT_AFTER_GTIDS",
    "TO_BASE64",
    "TO_SECONDS",
    "UpdateXML",
    "UUID_SHORT",
    "VALIDATE_PASSWORD_STRENGTH",
    "WAIT_UNTIL_SQL_THREAD_AFTER_GTIDS",
    "WEIGHT_STRING",
)

_ALWAYS_ASCII = (
    (
        "ascii_table",
        _("库名或表名含非 ASCII 字符"),
        """
        select TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
        from information_schema.tables
        where TABLE_NAME <> convert(TABLE_NAME using ASCII)
            or TABLE_SCHEMA <> convert(TABLE_SCHEMA using ASCII)
        """,
    ),
    (
        "ascii_column",
        _("列名含非 ASCII 字符"),
        """
        select TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
        from information_schema.columns
        where COLUMN_NAME <> convert(COLUMN_NAME using ASCII)
        """,
    ),
    (
        "ascii_routine",
        _("存储过程名含非 ASCII 字符"),
        """
        select ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_TYPE
        from information_schema.routines
        where ROUTINE_NAME <> convert(ROUTINE_NAME using ASCII)
        """,
    ),
    (
        "ascii_trigger",
        _("触发器名或定义含非 ASCII 字符"),
        """
        select TRIGGER_SCHEMA, TRIGGER_NAME
        from information_schema.triggers
        where TRIGGER_NAME <> convert(TRIGGER_NAME using ASCII)
            or ACTION_STATEMENT <> convert(ACTION_STATEMENT using ASCII)
        """,
    ),
    (
        "ascii_view",
        _("视图名含非 ASCII 字符"),
        """
        select TABLE_SCHEMA, TABLE_NAME, DEFINER
        from information_schema.VIEWS
        where TABLE_NAME <> convert(TABLE_NAME using ASCII)
        """,
    ),
    (
        "udf",
        _("mysql.func 里有自定义函数"),
        "select dl from mysql.func",
    ),
)

_TO_80 = (
    (
        "partition_engine",
        _("分区表引擎不是 InnoDB 或 NDB"),
        """
        select TABLE_SCHEMA, TABLE_NAME
        from information_schema.TABLES
        where ENGINE NOT IN ('innodb', 'ndbcluster')
            and CREATE_OPTIONS like '%partitioned%'
        """,
    ),
    (
        "shared_tablespace",
        _("分区表留在 InnoDB 共享表空间"),
        """
        select distinct NAME, SPACE, SPACE_TYPE
        from information_schema.INNODB_SYS_TABLES
        where NAME like '%#P#%'
            and SPACE_TYPE not like 'Single'
        """,
    ),
    (
        "fk_name",
        _("外键名超过 64 字符"),
        """
        select TABLE_SCHEMA, TABLE_NAME
        from information_schema.TABLES
        where TABLE_NAME in (
            select left(
                substr(ID, instr(ID, '/') + 1),
                instr(substr(ID, instr(ID, '/') + 1), '_ibfk_') - 1
            )
            from information_schema.INNODB_SYS_FOREIGN
            where length(substr(ID, instr(ID, '/') + 1)) > 64
        )
        """,
    ),
    (
        "enum_set_length",
        _("ENUM 或 SET 定义过长"),
        """
        select concat(TABLE_SCHEMA, '.', TABLE_NAME, '.', COLUMN_NAME) as schema_table_column
        from information_schema.columns
        where length(COLUMN_TYPE) > 263
            and TABLE_SCHEMA not in ('INFORMATION_SCHEMA', 'SYS', 'PERFORMANCE_SCHEMA', 'MYSQL')
        """,
    ),
    (
        "view_column_length",
        _("视图列名达到 64 字符"),
        """
        select c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME
        from information_schema.COLUMNS c
        join information_schema.TABLES t
            on c.TABLE_NAME = t.TABLE_NAME and c.TABLE_SCHEMA = t.TABLE_SCHEMA
        where c.TABLE_SCHEMA not in ('INFORMATION_SCHEMA', 'SYS', 'PERFORMANCE_SCHEMA', 'MYSQL')
            and t.TABLE_COMMENT = 'VIEW'
            and length(c.COLUMN_NAME) >= 64
        """,
    ),
    (
        "dictionary_name",
        _("mysql 库有与 8.0 数据字典同名的表"),
        """
        select TABLE_SCHEMA, TABLE_NAME
        from information_schema.TABLES
        where lower(TABLE_SCHEMA) = 'mysql'
            and lower(TABLE_NAME) in (
                'catalogs', 'character_sets', 'check_constraints', 'collations',
                'column_statistics', 'column_type_elements', 'columns', 'dd_properties',
                'events', 'foreign_key_column_usage', 'foreign_keys', 'index_column_usage',
                'index_partitions', 'index_stats', 'indexes', 'parameter_type_elements',
                'parameters', 'resource_groups', 'routines', 'schemata',
                'st_spatial_reference_systems', 'table_partition_values', 'table_partitions',
                'table_stats', 'tables', 'tablespace_files', 'tablespaces', 'triggers',
                'view_routine_usage', 'view_table_usage'
            )
        """,
    ),
)

_TO_57 = (
    (
        "old_password",
        _("存在长度为 16 的旧密码哈希"),
        "select concat(user, '@', host) as account from mysql.user where length(password) = 16",
    ),
    (
        "partition_57",
        _("存在分区表，5.7 分区改动大，暂不支持升级"),
        """
        select TABLE_SCHEMA, TABLE_NAME, count(*)
        from information_schema.PARTITIONS
        where PARTITION_NAME is not null
        group by 1, 2
        """,
    ),
    (
        "year2",
        _("存在 YEAR(2) 列"),
        """
        select TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
        from information_schema.COLUMNS
        where COLUMN_TYPE = 'year(2)'
        group by 1, 2, 3
        """,
    ),
    (
        "tokudb",
        _("存在 TokuDB 表"),
        """
        select TABLE_SCHEMA, TABLE_NAME, ENGINE
        from information_schema.TABLES
        where ENGINE = 'TokuDB'
        """,
    ),
)

_TO_56 = (
    (
        "old_password",
        _("存在长度为 16 的旧密码哈希"),
        "select concat(user, '@', host) as account from mysql.user where length(password) = 16",
    ),
)


def _quoted(names):
    return ",".join("'{}'".format(name) for name in names)


def _keywords(current_version, target_version):
    if target_version >= MYSQL_80 and current_version < MYSQL_80:
        return _BASE_KEYWORDS + _KEYWORDS_80
    if target_version >= MYSQL_57 and current_version < MYSQL_57:
        return _BASE_KEYWORDS + _KEYWORDS_57
    if target_version >= MYSQL_56 and current_version < MYSQL_56:
        return _BASE_KEYWORDS + _KEYWORDS_56
    return _BASE_KEYWORDS


def _keyword_items(current_version, target_version):
    words = _quoted(_keywords(current_version, target_version))
    routine_words = _quoted(_keywords(current_version, target_version) + _ROUTINE_BLACKLIST)
    return (
        (
            "keyword_table",
            _("表名撞上目标版本保留字"),
            "select TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE from information_schema.tables "
            "where TABLE_NAME in ({})".format(words),
        ),
        (
            "keyword_column",
            _("列名撞上目标版本保留字"),
            "select TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME from information_schema.columns "
            "where COLUMN_NAME in ({})".format(words),
        ),
        (
            "keyword_routine",
            _("存储过程名撞上目标版本保留字"),
            "select ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_TYPE from information_schema.routines "
            "where ROUTINE_NAME in ({})".format(routine_words),
        ),
        (
            "keyword_event",
            _("event 名撞上目标版本保留字"),
            "select EVENT_SCHEMA, EVENT_NAME from information_schema.events " "where EVENT_NAME in ({})".format(words),
        ),
        (
            "keyword_trigger",
            _("trigger 名撞上目标版本保留字"),
            "select TRIGGER_SCHEMA, TRIGGER_NAME from information_schema.triggers "
            "where TRIGGER_NAME in ({})".format(words),
        ),
        (
            "keyword_view",
            _("视图名撞上目标版本保留字"),
            "select TABLE_SCHEMA, TABLE_NAME, DEFINER from information_schema.VIEWS "
            "where TABLE_NAME in ({})".format(words),
        ),
    )


def _extra_items(current_version, target_version):
    if target_version >= MYSQL_80 and current_version < MYSQL_80:
        return _TO_80
    if target_version >= MYSQL_57 and current_version < MYSQL_57:
        return _TO_57
    if target_version >= MYSQL_56 and current_version < MYSQL_56:
        return _TO_56
    return ()


def select_upgrade_checks(current_version, target_version):
    """按当前版本和目标版本选出检查 SQL。"""
    selected = []
    for code, title, sql in (
        _keyword_items(current_version, target_version) + _ALWAYS_ASCII + _extra_items(current_version, target_version)
    ):
        selected.append({"code": code, "title": title, "sql": " ".join(sql.split())})
    return selected


def _rows_of(cmd_result):
    table_data = cmd_result.get("table_data")
    if isinstance(table_data, list):
        return table_data
    return []


def failures_from_drs(items, response, address):
    """有返回行或 SQL 报错就记一条失败。空结果算通过。"""
    if not response:
        return [_("DRS 检查 {} 返回为空").format(address)]
    head = response[0]
    if head.get("error_msg"):
        return [_("DRS 检查 {} 失败: {}").format(address, head["error_msg"])]
    cmd_results = head.get("cmd_results") or []
    failures = []
    if len(cmd_results) < len(items):
        failures.append(
            _("DRS 检查 {} 只返回 {} 条结果，发出了 {} 条 SQL").format(address, len(cmd_results), len(items))
        )
    for item, cmd_result in zip(items, cmd_results):
        if cmd_result.get("error_msg"):
            failures.append(_("{} {} 执行失败: {}").format(address, item["title"], cmd_result["error_msg"]))
            continue
        rows = _rows_of(cmd_result)
        if rows:
            preview = "; ".join(str(row) for row in rows[:5])
            failures.append(_("{} {}，例如 {}").format(address, item["title"], preview))
    return failures


def check_instance_upgrade(address, bk_cloud_id, target_version, rpc):
    """连 DRS 读实例版本。只有跨大版本才继续跑检查 SQL。target_version 是 8.0.30 这种字符串。"""
    version_resp = rpc(
        {
            "addresses": [address],
            "cmds": ["select version() as version"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if not version_resp or version_resp[0].get("error_msg"):
        detail = version_resp[0].get("error_msg") if version_resp else _("返回为空")
        return [_("无法读取 {} 的版本: {}").format(address, detail)]
    version_rows = _rows_of((version_resp[0].get("cmd_results") or [{}])[0])
    if not version_rows:
        return [_("无法读取 {} 的版本").format(address)]
    version_text = version_rows[0].get("version") or version_rows[0].get("VERSION") or ""
    current_version = mysql_version_parse(version_text)
    target_num = mysql_version_parse(target_version)
    if not current_version or not target_num:
        return [_("{} 的版本无法比较，当前 {}，目标 {}").format(address, version_text, target_version)]
    if not crosses_major_version(version_text, target_version):
        return []
    items = select_upgrade_checks(current_version, target_num)
    check_resp = rpc(
        {
            "addresses": [address],
            "cmds": [item["sql"] for item in items],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    return failures_from_drs(items, check_resp, address)
