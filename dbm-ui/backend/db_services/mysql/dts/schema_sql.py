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
import re

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.mysql.constants import QUERY_SCHEMA_TABLES_SQL
from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler

_SHOW_CREATE_BATCH = 50
_SOURCE_CLUSTER_TYPES = {ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value}
_PK_RE = re.compile(r"PRIMARY\s+KEY\s*\(\s*`([A-Za-z0-9_]+)`\s*\)", re.IGNORECASE)
_ENGINE_RE = re.compile(r"\bENGINE\s*=\s*\w+", re.IGNORECASE)
_TABLE_COMMENT_RE = re.compile(r"\bCOMMENT\s*=\s*'((?:\\'|[^'])*)'", re.IGNORECASE)
_SHARD_IN_COMMENT_RE = re.compile(r"""shard_key\s+["']""", re.IGNORECASE)


def _split_column_and_options(create_sql: str):
    """按第一层右括号切开列定义和表选项，避免改到列注释里的 ENGINE/COMMENT。"""
    start = create_sql.find("(")
    if start < 0:
        return create_sql, ""
    depth = 0
    in_quote = False
    escaped = False
    for index in range(start, len(create_sql)):
        char = create_sql[index]
        if in_quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "'":
                in_quote = False
            continue
        if char == "'":
            in_quote = True
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return create_sql[: index + 1], create_sql[index + 1 :]
    return create_sql, ""


def to_tspider_create(create_sql: str):
    """
    把源库 SHOW CREATE TABLE 改成 TSpider 语句。
    单列主键写入表注释 shard_key；复合主键或没有主键则不填，交给提单页拦截。
    """
    column_sql, options = _split_column_and_options(create_sql.strip().rstrip(";"))
    match = _PK_RE.search(column_sql)
    shard_key = match.group(1) if match else ""
    if _ENGINE_RE.search(options):
        options = _ENGINE_RE.sub("ENGINE=SPIDER", options, count=1)
    else:
        options = "{} ENGINE=SPIDER".format(options.rstrip())
    if shard_key and not _SHARD_IN_COMMENT_RE.search(options):
        shard_text = 'shard_key "{}"'.format(shard_key)
        comment_match = _TABLE_COMMENT_RE.search(options)
        if comment_match:
            merged = "{} {}".format(comment_match.group(1), shard_text).strip()
            options = options[: comment_match.start(1)] + merged + options[comment_match.end(1) :]
        else:
            options = "{} COMMENT='{}'".format(options.rstrip(), shard_text)
    statement = "{}{};".format(column_sql, options).strip()
    if not statement.endswith(";"):
        statement = "{};".format(statement)
    return statement, shard_key


def render_schema_sql(meta: dict, statements: list) -> str:
    """拼整份 SQL。顶部 -- 注释只作说明，按行首 CREATE TABLE 切表时不会被算进去。"""
    lines = [
        "-- source_cluster_id: {}".format(meta["cluster_id"]),
        "-- target_cluster_id: {}".format(meta["target_cluster_id"]),
        "-- db_patterns: {}".format(",".join(meta["db_patterns"])),
        "-- ignore_dbs: {}".format(",".join(meta.get("ignore_dbs") or [])),
        "-- table_patterns: {}".format(",".join(meta["table_patterns"])),
        "-- ignore_tables: {}".format(",".join(meta.get("ignore_tables") or [])),
        _("-- 分片键写在表注释 COMMENT='shard_key \"列名\"'，提交前需逐表确认"),
        "",
    ]
    current_db = None
    for item in statements:
        if item["db"] != current_db:
            lines.append("USE {};".format(_quote_ident(item["db"])))
            current_db = item["db"]
        lines.append(item["sql"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _cell(row: dict, name: str):
    if not row:
        return None
    if name in row:
        return row[name]
    for key, value in row.items():
        if str(key).lower() == name.lower():
            return value
    return None


def _quote_ident(name: str) -> str:
    if not name or "`" in name:
        raise RemoteServiceBaseException(_("库表名不支持反引号: {}").format(name))
    return "`{}`".format(name)


def _endpoint(remote: RemoteServiceHandler, cluster_id: int):
    cluster_handler, address = remote._get_cluster_address({}, cluster_id)
    return cluster_handler.cluster.bk_cloud_id, address


def _rpc_query(bk_cloud_id: int, address: str, cmds: list) -> dict:
    rpc_results = DRSApi.rpc({"bk_cloud_id": bk_cloud_id, "addresses": [address], "cmds": cmds})
    if not rpc_results or rpc_results[0].get("error_msg"):
        message = rpc_results[0].get("error_msg") if rpc_results else "empty rpc result"
        raise RemoteServiceBaseException(_("查询源集群失败: {}").format(message))
    by_cmd = {}
    for item in rpc_results[0].get("cmd_results") or []:
        if item.get("error_msg"):
            raise RemoteServiceBaseException(_("查询源集群失败: {}").format(item["error_msg"]))
        by_cmd[item["cmd"]] = item.get("table_data") or []
    return by_cmd


def _list_schema_tables(
    remote: RemoteServiceHandler, cluster_id: int, databases: list, tables: list, ignore_tables: list
):
    bk_cloud_id, address = _endpoint(remote, cluster_id)
    remote._check_sql_literals(databases + tables + ignore_tables)
    db_list = "({})".format(",".join("'{}'".format(db) for db in databases))
    include_sql = QUERY_SCHEMA_TABLES_SQL.format(
        db_list=db_list, table_sts=remote._get_db_tb_sts(tables, "TABLE_NAME", 1)
    )
    ignore_sql = QUERY_SCHEMA_TABLES_SQL.format(
        db_list=db_list, table_sts=remote._get_db_tb_sts(ignore_tables, "TABLE_NAME", 0)
    )
    queried = _rpc_query(bk_cloud_id, address, [include_sql, ignore_sql])
    included = {_schema_table(row) for row in queried.get(include_sql, [])}
    ignored = {_schema_table(row) for row in queried.get(ignore_sql, [])}
    return sorted(included - ignored)


def _schema_table(row: dict):
    db_name = _cell(row, "TABLE_SCHEMA")
    table_name = _cell(row, "TABLE_NAME")
    if not db_name or not table_name:
        raise RemoteServiceBaseException(_("查询源集群失败: 库表结果缺少表名"))
    return db_name, table_name


def _show_create_tables(remote: RemoteServiceHandler, cluster_id: int, pairs: list) -> list:
    bk_cloud_id, address = _endpoint(remote, cluster_id)
    statements = []
    for offset in range(0, len(pairs), _SHOW_CREATE_BATCH):
        batch = pairs[offset : offset + _SHOW_CREATE_BATCH]
        cmds = ["SHOW CREATE TABLE {}.{}".format(_quote_ident(db), _quote_ident(table)) for db, table in batch]
        queried = _rpc_query(bk_cloud_id, address, cmds)
        for (db, table), cmd in zip(batch, cmds):
            rows = queried.get(cmd) or []
            create_sql = _cell(rows[0], "Create Table") if rows else None
            if not create_sql:
                raise RemoteServiceBaseException(_("获取 {}.{} 的建表语句失败").format(db, table))
            sql, shard_key = to_tspider_create(create_sql)
            statements.append({"db": db, "table": table, "sql": sql, "shard_key": shard_key})
    return statements


def _load_cluster(bk_biz_id: int, cluster_id: int, cluster_types: set, role: str) -> Cluster:
    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    except Cluster.DoesNotExist as exc:
        raise RemoteServiceBaseException(_("{}集群 {} 不存在或不属于当前业务").format(role, cluster_id)) from exc
    if cluster.cluster_type not in cluster_types:
        raise RemoteServiceBaseException(_("{}集群 {} 类型是 {}，不符合要求").format(role, cluster_id, cluster.cluster_type))
    return cluster


def build_hetero_schema_sql(bk_biz_id: int, data: dict) -> dict:
    """展开源集群库表通配符，返回一整份 TSpider 建表 SQL。任一表失败则整次失败。"""
    _load_cluster(bk_biz_id, data["cluster_id"], _SOURCE_CLUSTER_TYPES, _("源"))
    _load_cluster(bk_biz_id, data["target_cluster_id"], {ClusterType.TenDBCluster.value}, _("目标"))
    remote = RemoteServiceHandler(bk_biz_id)
    databases = remote.show_database_with_pattern(
        data["cluster_id"],
        data["db_patterns"],
        ignore_dbs=data.get("ignore_dbs") or [],
        keep_system_dbs=["test"],
    )
    if not databases:
        raise RemoteServiceBaseException(_("未匹配到可迁移的库"))
    pairs = _list_schema_tables(
        remote,
        data["cluster_id"],
        databases,
        data["table_patterns"],
        data.get("ignore_tables") or [],
    )
    if not pairs:
        raise RemoteServiceBaseException(_("未匹配到可迁移的表"))
    statements = _show_create_tables(remote, data["cluster_id"], pairs)
    return {
        "sql": render_schema_sql(data, statements),
        "tables": [{"db": item["db"], "table": item["table"], "shard_key": item["shard_key"]} for item in statements],
    }
