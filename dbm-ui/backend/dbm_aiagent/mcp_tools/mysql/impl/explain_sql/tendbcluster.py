# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster EXPLAIN 分片路由流程（7 步）：

1. sanitize_select_sql          安全校验 + DML→SELECT（不改库名）
2. parse_route_context          库表、JOIN 关系、WHERE/JOIN ON 条件
3. show_create_table (Spider)   去重后查 DDL，解析 shard_key / 分片算式
4. match shard_key_values       从 where_eq / joins[].on_literal_eq 找 shard_key 值
5. calc shard_id                有值则 crc32(首个 value) % N，否则 0
6. rewrite_sql_for_shard        改写 dbname→dbname_{shard_id}，生成 remote_explain_sql
7. explain_on_remote_slave      连对应 remote slave 执行 EXPLAIN

入口 ``explain_tendbcluster`` 接收已由 ``sanitize_select_sql`` 处理过的 SQL（step 1 在 pkg 入口完成）。
"""
import logging
import re
import zlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import sqlglot
from sqlglot import exp

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import TenDBClusterStorageSet
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_ident
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.drs import run_explain

logger = logging.getLogger("root")

# 系统库白名单：这些库名不做 Spider 分片改写（与 sql_safety 一致）
_REWRITE_SKIP_DBS = frozenset(
    {
        "mysql",
        "sys",
        "information_schema",
        "performance_schema",
        "test",
        "infodba_schema",
    }
)

WhereEqValues = List[Union[str, int, float, bool, None]]
TableEqPair = Tuple[str, str]


@dataclass
class TableRef:
    """单表引用；ref_key 为 SQL 中的别名或表名，用于 JOIN 关系关联。"""

    table_name: str
    dbname: Optional[str] = None
    alias: Optional[str] = None

    @property
    def ref_key(self) -> str:
        return self.alias or self.table_name

    @property
    def physical_key(self) -> Tuple[Optional[str], str]:
        return self.dbname, self.table_name


@dataclass
class TableCreateInfo:
    """Step 3：Spider 上 SHOW CREATE TABLE 及分片元数据。"""

    dbname: str
    table_name: str
    create_sql: str
    shard_key: Optional[str] = None
    shard_expr: Optional[str] = None
    shard_count: Optional[int] = None


@dataclass
class ShardKeyMatch:
    """Step 4：某张分片表 shard_key 在 SQL 条件里匹配到的字面量。"""

    dbname: str
    table_name: str
    shard_key: str
    condition_key: Optional[str]
    values: WhereEqValues = field(default_factory=list)
    shard_id: int = 0


@dataclass
class JoinEdge:
    """单次 JOIN：右侧新引入的表，及其与左侧已有表的关系。"""

    join_kind: str
    right: TableRef
    left_ref_keys: List[str]
    on_literal_eq: Dict[str, WhereEqValues] = field(default_factory=dict)
    on_table_eq: List[TableEqPair] = field(default_factory=list)


@dataclass
class ExplainSqlRouteContext:
    """Step 2 产出。"""

    default_dbname: Optional[str]
    tables: List[TableRef] = field(default_factory=list)
    joins: List[JoinEdge] = field(default_factory=list)
    where_eq: Dict[str, WhereEqValues] = field(default_factory=dict)
    where_table_eq: List[TableEqPair] = field(default_factory=list)
    table_creates: List[TableCreateInfo] = field(default_factory=list)
    shard_key_matches: List[ShardKeyMatch] = field(default_factory=list)
    explained_sql: str = ""
    was_rewritten: bool = False
    remote_explain_sql: str = ""
    route_physical_dbname: Optional[str] = None
    explain_result: Optional[List[Any]] = None

    def physical_tables(self) -> List[TableRef]:
        """按 (dbname, table_name) 去重，Step 3 show create 只查这些，不重复、不笛卡尔。"""
        seen: set[Tuple[Optional[str], str]] = set()
        out: List[TableRef] = []
        for t in self.tables:
            if t.physical_key in seen:
                continue
            seen.add(t.physical_key)
            out.append(t)
        return out


def explain_tendbcluster(
    cluster_domain: str,
    dbname: str,
    explained_sql: str,
    was_rewritten: bool,
) -> Dict:
    """TenDBCluster EXPLAIN（step 2–7）。step 1 sanitize 由 pkg 入口统一完成。"""
    # Step 2: 库表、JOIN 关系、WHERE/JOIN ON 条件
    ctx = _parse_route_context(explained_sql, dbname)
    ctx.explained_sql = explained_sql
    ctx.was_rewritten = was_rewritten

    logger.info(
        "explain_sql tendbcluster parse: cluster=%s tables=%d joins=%d",
        cluster_domain,
        len(ctx.tables),
        len(ctx.joins),
    )

    # Step 3: Spider 上对 physical_tables 逐个 SHOW CREATE TABLE
    ctx.table_creates = _fetch_spider_table_creates(cluster_domain, ctx.physical_tables())

    # Step 4: 从 where_eq + joins[].on_literal_eq 匹配 shard_key 字面量
    ctx.shard_key_matches = _match_shard_key_values(ctx)

    # Step 5: 有 shard_key 字面量则 crc32(首个 value) % N，否则 shard_id=0
    _apply_shard_ids(ctx)

    shard_id = _route_shard_id(ctx)
    driving = ctx.tables[0] if ctx.tables else None
    logger.info(
        "explain_sql tendbcluster route: cluster=%s driving_table=%s shard_id=%d matches=%d",
        cluster_domain,
        f"{driving.dbname}.{driving.table_name}" if driving else "",
        shard_id,
        len(ctx.shard_key_matches),
    )

    # Step 6: 改写库名 dbname → dbname_{shard_id}
    _rewrite_sql_for_shard(ctx)

    logger.info(
        "explain_sql tendbcluster rewrite: cluster=%s physical_db=%s remote_sql_len=%d",
        cluster_domain,
        ctx.route_physical_dbname or "",
        len(ctx.remote_explain_sql),
    )

    # Step 7: 连 remote slave 执行 EXPLAIN
    ctx.explain_result = _explain_on_remote_slave(cluster_domain, ctx)

    return {
        "explain_result": ctx.explain_result,
        "rewritten": ctx.was_rewritten,
    }


def _get_tendbcluster(cluster_domain: str) -> Cluster:
    try:
        return Cluster.objects.using(MYSQL_MCP_DB_READ).get(
            immute_domain=cluster_domain, cluster_type=ClusterType.TenDBCluster
        )
    except Cluster.DoesNotExist as e:
        raise DBMMcpBaseException(msg=f"TenDBCluster not found: {cluster_domain}") from e


def _pick_running_spider_master(cluster_obj: Cluster):
    spider = (
        cluster_obj.proxyinstance_set.select_related("tendbclusterspiderext")
        .filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
            status=InstanceStatus.RUNNING,
        )
        .first()
    )
    if spider is None:
        raise DBMMcpBaseException(msg=f"no running spider_master in cluster: {cluster_obj.immute_domain}")
    return spider


def _show_create_table_on_spider(bk_cloud_id: int, spider_address: str, dbname: str, table_name: str) -> str:
    quoted_db = quote_ident(dbname.strip("`"))
    quoted_tbl = quote_ident(table_name.strip("`"))

    drs_raw_res = DRSApi.v2_webconsole_rpc(
        {
            "addresses": [spider_address],
            "cmds": [f"USE {quoted_db}", f"SHOW CREATE TABLE {quoted_tbl}"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
            "query_timeout": 10,
        }
    )

    address_res = drs_raw_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    use_db_res = address_res["cmd_results"][0]
    if use_db_res["error_msg"]:
        raise DBMMcpBaseException(msg=f"change db to {dbname} failed: {use_db_res['error_msg']}")

    show_create_res = address_res["cmd_results"][1]
    if show_create_res["error_msg"]:
        raise DBMMcpBaseException(
            msg=f"show create table {dbname}.{table_name} on spider failed: {show_create_res['error_msg']}"
        )

    return list(show_create_res["table_data"][0].values())[0]


def _parse_shard_key_from_comment(create_sql: str) -> Optional[str]:
    """从 COMMENT 解析 shard_key，对齐 spider.go ParseGetShardKeyForSpider。"""
    match = re.search(r'shard_key\s+"([^"]+)"', create_sql, re.IGNORECASE)
    return match.group(1) if match else None


def _parse_shard_key_from_expr(shard_expr: Optional[str]) -> Optional[str]:
    """从分片算式解析 shard_key，如 crc32(`id`) MOD 6 → id。

    COMMENT 未带 shard_key 时（部分集群 SHOW CREATE 如此），用 PARTITION 表达式兜底。
    """
    if not shard_expr:
        return None
    match = re.search(r"crc32\s*\(\s*`?(\w+)`?\s*\)", shard_expr, re.IGNORECASE)
    return match.group(1) if match else None


def _parse_partition_list_expr(create_sql: str) -> Optional[str]:
    """提取 PARTITION BY LIST (...) 括号内的分片算式，如 crc32(`col`) MOD 4。"""
    marker = "PARTITION BY LIST ("
    pos = create_sql.upper().find(marker)
    if pos == -1:
        return None

    start = pos + len(marker)
    depth = 1
    idx = start
    while idx < len(create_sql) and depth > 0:
        ch = create_sql[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        idx += 1

    if depth != 0:
        return None
    return create_sql[start : idx - 1].strip()


def _parse_shard_count_from_expr(shard_expr: str) -> Optional[int]:
    match = re.search(r"MOD\s+(\d+)\s*$", shard_expr, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _parse_spider_shard_meta(create_sql: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    shard_expr = _parse_partition_list_expr(create_sql)
    shard_key = _parse_shard_key_from_comment(create_sql) or _parse_shard_key_from_expr(shard_expr)
    shard_count = _parse_shard_count_from_expr(shard_expr) if shard_expr else None
    return shard_key, shard_expr, shard_count


def _fetch_spider_table_creates(cluster_domain: str, tables: List[TableRef]) -> List[TableCreateInfo]:
    cluster_obj = _get_tendbcluster(cluster_domain)
    spider = _pick_running_spider_master(cluster_obj)
    bk_cloud_id = cluster_obj.bk_cloud_id
    address = spider.ip_port

    creates: List[TableCreateInfo] = []
    for t in tables:
        dbname = t.dbname or ""
        create_sql = _show_create_table_on_spider(bk_cloud_id, address, dbname, t.table_name)
        shard_key, shard_expr, shard_count = _parse_spider_shard_meta(create_sql)
        creates.append(
            TableCreateInfo(
                dbname=dbname,
                table_name=t.table_name,
                create_sql=create_sql,
                shard_key=shard_key,
                shard_expr=shard_expr,
                shard_count=shard_count,
            )
        )
    return creates


def _collect_literal_eq(ctx: ExplainSqlRouteContext) -> Dict[str, WhereEqValues]:
    """合并 WHERE 与各 JOIN ON 中的 col = 字面量 / IN 列表。"""
    merged: Dict[str, WhereEqValues] = {}
    for key, values in ctx.where_eq.items():
        merged.setdefault(key, []).extend(values)
    for join in ctx.joins:
        for key, values in join.on_literal_eq.items():
            merged.setdefault(key, []).extend(values)
    return merged


def _ref_keys_by_physical(tables: List[TableRef]) -> Dict[Tuple[str, str], List[str]]:
    mapping: Dict[Tuple[str, str], List[str]] = {}
    for t in tables:
        key = (t.dbname or "", t.table_name)
        if t.ref_key not in mapping.setdefault(key, []):
            mapping[key].append(t.ref_key)
    return mapping


def _candidate_condition_keys(ref_keys: List[str], table_name: str, shard_key: str) -> List[str]:
    """按 alias.col → table.col → col 优先级生成候选条件键。"""
    keys: List[str] = []
    for ref in ref_keys:
        keys.append(f"{ref}.{shard_key}")
    keys.append(f"{table_name}.{shard_key}")
    if len(ref_keys) == 1:
        keys.append(shard_key)
    return keys


def _match_shard_key_values(ctx: ExplainSqlRouteContext) -> List[ShardKeyMatch]:
    literal_eq = _collect_literal_eq(ctx)
    ref_keys_map = _ref_keys_by_physical(ctx.tables)
    table_eqs = list(ctx.where_table_eq)
    for join in ctx.joins:
        table_eqs.extend(join.on_table_eq)

    matches: List[ShardKeyMatch] = []
    for tc in ctx.table_creates:
        if not tc.shard_key:
            continue

        physical = (tc.dbname, tc.table_name)
        ref_keys = ref_keys_map.get(physical, [])
        condition_key, values = _find_shard_key_values(
            shard_key=tc.shard_key,
            ref_keys=ref_keys,
            table_name=tc.table_name,
            literal_eq=literal_eq,
            table_eqs=table_eqs,
        )
        matches.append(
            ShardKeyMatch(
                dbname=tc.dbname,
                table_name=tc.table_name,
                shard_key=tc.shard_key,
                condition_key=condition_key,
                values=values,
            )
        )
    return matches


def _table_create_by_physical(table_creates: List[TableCreateInfo]) -> Dict[Tuple[str, str], TableCreateInfo]:
    return {(tc.dbname, tc.table_name): tc for tc in table_creates}


def _crc32_shard_id(shard_value: Any, shard_count: int) -> int:
    raw = "" if shard_value is None else str(shard_value)
    return (zlib.crc32(raw.encode()) & 0xFFFFFFFF) % shard_count


def _calc_shard_id_for_match(match: ShardKeyMatch, tc: Optional[TableCreateInfo]) -> int:
    if not match.values or not tc or not tc.shard_count:
        return 0
    return _crc32_shard_id(match.values[0], tc.shard_count)


def _apply_shard_ids(ctx: ExplainSqlRouteContext) -> None:
    creates = _table_create_by_physical(ctx.table_creates)
    for m in ctx.shard_key_matches:
        tc = creates.get((m.dbname, m.table_name))
        m.shard_id = _calc_shard_id_for_match(m, tc)


def _route_shard_id(ctx: ExplainSqlRouteContext) -> int:
    """Step 6/7 用 FROM 第一张表的 shard_id。"""
    if not ctx.tables:
        return 0
    driving = ctx.tables[0]
    driving_key = (driving.dbname or "", driving.table_name)
    for m in ctx.shard_key_matches:
        if (m.dbname, m.table_name) == driving_key:
            return m.shard_id
    return 0


def _physical_dbname(logical_dbname: str, shard_id: int) -> str:
    return f"{logical_dbname.strip('`')}_{shard_id}"


def _driving_logical_dbname(ctx: ExplainSqlRouteContext) -> Optional[str]:
    if ctx.tables and ctx.tables[0].dbname:
        return ctx.tables[0].dbname
    return ctx.default_dbname


def _rewrite_dbnames_for_shard(explained_sql: str, shard_id: int) -> str:
    """将 SQL 中 db.table / db.col 的逻辑库名改写为 db_{shard_id}（系统库除外）。"""
    try:
        statements = sqlglot.parse(explained_sql, read="mysql")
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        raise DBMMcpBaseException(msg=f"sql parse failed for db rewrite: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise DBMMcpBaseException(msg=f"must be exactly one statement, got {len(statements)}")

    root = statements[0]
    suffix = f"_{shard_id}"
    for table in root.find_all(exp.Table):
        db = table.args.get("db")
        if db and isinstance(db, exp.Identifier):
            original_name = db.this
            if original_name.lower() not in _REWRITE_SKIP_DBS:
                db.set("this", f"{original_name}{suffix}")

    for col in root.find_all(exp.Column):
        db = col.args.get("db")
        if db and isinstance(db, exp.Identifier):
            original_name = db.this
            if original_name.lower() not in _REWRITE_SKIP_DBS:
                db.set("this", f"{original_name}{suffix}")

    return root.sql(dialect="mysql")


def _get_remote_slave_address(cluster_obj: Cluster, shard_id: int) -> str:
    try:
        storage_set = TenDBClusterStorageSet.objects.using(MYSQL_MCP_DB_READ).get(
            cluster=cluster_obj, shard_id=shard_id
        )
    except TenDBClusterStorageSet.DoesNotExist as e:
        raise DBMMcpBaseException(msg=f"shard_id {shard_id} not found in cluster {cluster_obj.immute_domain}") from e
    return storage_set.storage_instance_tuple.receiver.ip_port


def _rewrite_sql_for_shard(ctx: ExplainSqlRouteContext) -> None:
    """Step 6: 按路由 shard_id 生成 remote 侧 EXPLAIN SQL。"""
    shard_id = _route_shard_id(ctx)
    ctx.remote_explain_sql = _rewrite_dbnames_for_shard(ctx.explained_sql, shard_id)

    logical_db = _driving_logical_dbname(ctx)
    ctx.route_physical_dbname = _physical_dbname(logical_db, shard_id) if logical_db else None


def _explain_on_remote_slave(cluster_domain: str, ctx: ExplainSqlRouteContext) -> List[Any]:
    """Step 7: 连对应 remote slave 执行 EXPLAIN。"""
    cluster_obj = _get_tendbcluster(cluster_domain)
    shard_id = _route_shard_id(ctx)
    address = _get_remote_slave_address(cluster_obj, shard_id)

    logger.info(
        "explain_sql tendbcluster explain: cluster=%s shard_id=%d address=%s use_db=%s",
        cluster_domain,
        shard_id,
        address,
        ctx.route_physical_dbname or "",
    )

    return run_explain(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        address=address,
        sql=ctx.remote_explain_sql,
        use_db=ctx.route_physical_dbname,
    )


def _find_shard_key_values(
    *,
    shard_key: str,
    ref_keys: List[str],
    table_name: str,
    literal_eq: Dict[str, WhereEqValues],
    table_eqs: List[TableEqPair],
) -> Tuple[Optional[str], WhereEqValues]:
    for key in _candidate_condition_keys(ref_keys, table_name, shard_key):
        if key in literal_eq and literal_eq[key]:
            return key, list(literal_eq[key])

    propagated = _propagate_shard_key_via_table_eq(
        shard_key=shard_key,
        ref_keys=ref_keys,
        literal_eq=literal_eq,
        table_eqs=table_eqs,
    )
    if propagated:
        return propagated
    return None, []


def _propagate_shard_key_via_table_eq(
    *,
    shard_key: str,
    ref_keys: List[str],
    literal_eq: Dict[str, WhereEqValues],
    table_eqs: List[TableEqPair],
) -> Optional[Tuple[str, WhereEqValues]]:
    """JOIN/WHERE 表间等值传递：a.id = b.id 且已知 a.id = 1 时，补 b.id。"""
    own_cols = {f"{ref}.{shard_key}" for ref in ref_keys}
    if len(ref_keys) == 1:
        own_cols.add(shard_key)

    for left, right in table_eqs:
        for own_col, partner_col in ((left, right), (right, left)):
            if own_col not in own_cols:
                continue
            partner_values = literal_eq.get(partner_col)
            if partner_values:
                return partner_col, list(partner_values)
    return None


def _parse_route_context(explained_sql: str, dbname_param: str) -> ExplainSqlRouteContext:
    """Step 2: 解析路由上下文（含 JOIN 顺序与 ON 关系）。"""
    try:
        statements = sqlglot.parse(explained_sql, read="mysql")
    except (sqlglot.errors.ParseError, sqlglot.errors.TokenError) as e:
        raise DBMMcpBaseException(msg=f"sql parse failed: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise DBMMcpBaseException(msg=f"must be exactly one statement, got {len(statements)}")

    root = statements[0]
    select_root = _unwrap_to_select(root)
    tables, joins = _extract_tables_and_joins(select_root)
    tables.extend(_extract_subquery_tables(select_root))
    if not tables:
        raise DBMMcpBaseException(msg="cannot resolve any table from sql (subquery in FROM not supported yet)")

    default_dbname = _normalize_dbname(dbname_param)
    tables = _apply_default_dbname(tables, default_dbname)
    joins = _apply_default_dbname_on_joins(joins, default_dbname)
    if any(t.dbname is None for t in tables):
        raise DBMMcpBaseException(
            msg="dbname is required for tables without db prefix: provide db_name or use db.table in sql"
        )

    where_eq, where_table_eq = _collect_where_conditions(select_root)

    return ExplainSqlRouteContext(
        default_dbname=default_dbname,
        tables=tables,
        joins=joins,
        where_eq=where_eq,
        where_table_eq=where_table_eq,
    )


def _unwrap_to_select(root: exp.Expression) -> exp.Select:
    if isinstance(root, exp.Select):
        return root
    if isinstance(root, exp.SetOperation):
        left = root.left
        if isinstance(left, exp.Select):
            return left
    raise DBMMcpBaseException(msg=f"unsupported statement for route parsing: {type(root).__name__}")


def _select_from(select: exp.Select) -> Optional[exp.Expression]:
    """sqlglot 用 from_ 存 FROM 子句（from 为保留字）。"""
    return select.args.get("from_") or select.args.get("from")


def _extract_tables_and_joins(select: exp.Select) -> Tuple[List[TableRef], List[JoinEdge]]:
    tables: List[TableRef] = []
    joins: List[JoinEdge] = []
    in_scope_keys: List[str] = []

    from_ = _select_from(select)
    if from_ is not None:
        base = _table_ref(from_.this if isinstance(from_, exp.From) else from_)
        if base:
            tables.append(base)
            in_scope_keys.append(base.ref_key)

    for join in select.args.get("joins") or []:
        if not isinstance(join, exp.Join):
            continue
        right = _table_ref(join.this)
        if not right:
            continue
        on = join.args.get("on")
        on_literal, on_table = _collect_on_conditions(on)
        joins.append(
            JoinEdge(
                join_kind=_join_kind(join),
                right=right,
                left_ref_keys=list(in_scope_keys),
                on_literal_eq=on_literal,
                on_table_eq=on_table,
            )
        )
        tables.append(right)
        in_scope_keys.append(right.ref_key)

    return tables, joins


def _join_kind(join: exp.Join) -> str:
    kind = join.args.get("kind") or join.kind
    kind_str = str(kind).replace("TokenType.", "").strip() if kind is not None else ""
    if not kind_str:
        return "CROSS" if join.args.get("on") is None else "INNER"
    return kind_str.upper()


def _extract_subquery_tables(root: exp.Expression) -> List[TableRef]:
    """从 IN/EXISTS 等子查询中提取基表，供 physical_tables 去重后 show create。"""
    refs: List[TableRef] = []
    for node in root.walk():
        if not isinstance(node, exp.Subquery):
            continue
        inner = node.this
        if not isinstance(inner, exp.Select):
            continue
        inner_tables, _ = _extract_tables_and_joins(inner)
        refs.extend(inner_tables)
        refs.extend(_extract_subquery_tables(inner))
    return refs


def _table_ref(table_expr: exp.Expression) -> Optional[TableRef]:
    if not isinstance(table_expr, exp.Table):
        return None
    table_name = _identifier_name(table_expr.this)
    if not table_name:
        return None
    return TableRef(
        table_name=table_name,
        dbname=_identifier_name(table_expr.args.get("db")),
        alias=_identifier_name(table_expr.args.get("alias")),
    )


def _normalize_dbname(dbname_param: str) -> Optional[str]:
    dbname = (dbname_param or "").strip("`").strip()
    return dbname or None


def _apply_default_dbname(tables: List[TableRef], default_dbname: Optional[str]) -> List[TableRef]:
    if not default_dbname:
        return tables
    return [
        TableRef(
            table_name=t.table_name,
            dbname=t.dbname or default_dbname,
            alias=t.alias,
        )
        for t in tables
    ]


def _apply_default_dbname_on_joins(joins: List[JoinEdge], default_dbname: Optional[str]) -> List[JoinEdge]:
    if not default_dbname:
        return joins
    return [
        JoinEdge(
            join_kind=j.join_kind,
            right=TableRef(
                table_name=j.right.table_name,
                dbname=j.right.dbname or default_dbname,
                alias=j.right.alias,
            ),
            left_ref_keys=j.left_ref_keys,
            on_literal_eq=j.on_literal_eq,
            on_table_eq=j.on_table_eq,
        )
        for j in joins
    ]


def _collect_where_conditions(select: exp.Select) -> Tuple[Dict[str, WhereEqValues], List[TableEqPair]]:
    where = select.args.get("where")
    if where is None:
        return {}, []
    expr = where.this if isinstance(where, exp.Where) else where
    return _collect_eq_from_expr(expr, skip_subqueries=True)


def _collect_on_conditions(on: Optional[exp.Expression]) -> Tuple[Dict[str, WhereEqValues], List[TableEqPair]]:
    if on is None:
        return {}, []
    return _collect_eq_from_expr(on, skip_subqueries=False)


def _collect_eq_from_expr(
    expr: exp.Expression, *, skip_subqueries: bool
) -> Tuple[Dict[str, WhereEqValues], List[TableEqPair]]:
    literal_eq: Dict[str, WhereEqValues] = {}
    table_eq: List[TableEqPair] = []
    for node in _walk_expr(expr, skip_subqueries=skip_subqueries):
        if isinstance(node, exp.EQ):
            col_col = _parse_table_eq(node)
            if col_col:
                table_eq.append(col_col)
                continue
            col_name, value = _parse_literal_eq(node)
            if col_name and value is not None:
                literal_eq.setdefault(col_name, []).append(value)
        elif isinstance(node, exp.In):
            col_name, values = _parse_in(node)
            if col_name and values:
                literal_eq.setdefault(col_name, []).extend(values)
    return literal_eq, table_eq


def _walk_expr(expr: exp.Expression, *, skip_subqueries: bool):
    """遍历表达式树；skip_subqueries 时不下钻 Subquery（外层 WHERE 不与子查询内条件混淆）。"""
    stack = [expr]
    while stack:
        node = stack.pop()
        yield node
        if skip_subqueries and isinstance(node, exp.Subquery):
            continue
        for child in reversed(list(node.iter_expressions())):
            stack.append(child)


def _parse_literal_eq(node: exp.EQ) -> tuple[Optional[str], Any]:
    left, right = node.left, node.right
    if isinstance(left, exp.Column) and not isinstance(right, exp.Column):
        return _qualified_column_name(left), _literal_value(right)
    if isinstance(right, exp.Column) and not isinstance(left, exp.Column):
        return _qualified_column_name(right), _literal_value(left)
    return None, None


def _parse_table_eq(node: exp.EQ) -> Optional[TableEqPair]:
    if isinstance(node.left, exp.Column) and isinstance(node.right, exp.Column):
        left = _qualified_column_name(node.left)
        right = _qualified_column_name(node.right)
        if left and right:
            return left, right
    return None


def _identifier_name(node: Optional[exp.Expression]) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, exp.Identifier):
        return node.this
    if isinstance(node, exp.Table):
        return _identifier_name(node.this)
    if hasattr(node, "name") and node.name:
        return node.name
    return str(node)


def _parse_in(node: exp.In) -> tuple[Optional[str], WhereEqValues]:
    col = node.this
    if not isinstance(col, exp.Column):
        return None, []

    values: WhereEqValues = []
    for item in node.args.get("expressions") or []:
        val = _literal_value(item)
        if val is not None:
            values.append(val)
    return _qualified_column_name(col), values


def _qualified_column_name(col: exp.Column) -> Optional[str]:
    col_part = _column_name(col)
    if not col_part:
        return None
    table_part = col.table
    if table_part:
        return f"{table_part}.{col_part}"
    return col_part


def _column_name(col: exp.Column) -> Optional[str]:
    name = col.name or (col.this if isinstance(col.this, str) else None)
    if isinstance(col.this, exp.Identifier):
        name = col.this.this
    return name


def _literal_value(node: exp.Expression) -> Any:
    if isinstance(node, exp.Literal):
        if node.is_string:
            return node.this
        try:
            if "." in node.this:
                return float(node.this)
            return int(node.this)
        except ValueError:
            return node.this
    if isinstance(node, exp.Boolean):
        return node.this
    if isinstance(node, exp.Null):
        return None
    return None
