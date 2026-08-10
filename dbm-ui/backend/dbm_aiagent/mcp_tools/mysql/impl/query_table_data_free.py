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
from typing import Dict, List, Optional, Tuple

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.helpers.get_slave_address_and_dbname import get_cloud_slave_address_and_dbname
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_string_literal

# 仅返回 data_free 大于 10GB 的表（单分片维度）；汇聚后再次按逻辑表总空洞过滤
MIN_DATA_FREE_BYTES = 10 * 1024 * 1024 * 1024
_GB = 1024 * 1024 * 1024

_QUERY_TABLE_DATA_FREE_SQL = """
SELECT
    table_schema,
    table_name,
    engine,
    table_rows,
    data_length,
    index_length,
    data_free
FROM information_schema.tables
WHERE table_schema NOT IN (
        'mysql',
        'information_schema',
        'performance_schema',
        'sys'
    )
  AND data_free > {min_data_free}
{extra_where}
ORDER BY data_free DESC
""".strip()


def _build_extra_where(schema_name: str, table_names: Optional[List[str]]) -> str:
    clauses = []
    if schema_name:
        clauses.append(f"AND table_schema = {quote_string_literal(schema_name)}")
    if table_names:
        in_tables = ",".join(quote_string_literal(name) for name in table_names)
        clauses.append(f"AND table_name IN ({in_tables})")
    return "\n".join(clauses)


def _build_query_sql(schema_name: str, table_names: Optional[List[str]]) -> str:
    return _QUERY_TABLE_DATA_FREE_SQL.format(
        min_data_free=MIN_DATA_FREE_BYTES,
        extra_where=_build_extra_where(schema_name, table_names),
    )


def _to_int(value) -> int:
    if value is None or value == "":
        return 0
    return int(value) if not isinstance(value, int) else value


def _shard_schema_name(logical_dbname: str, shard_id: int) -> str:
    return f"{logical_dbname}_{shard_id}"


def _logical_schema_from_shard_db(table_schema: str, shard_id: Optional[int]) -> str:
    if shard_id is not None and table_schema.endswith(f"_{shard_id}"):
        return table_schema[: -(len(str(shard_id)) + 1)]
    return table_schema


def _parse_raw_row(row: Dict, shard_id: Optional[int] = None) -> Dict:
    return {
        "table_schema": row.get("table_schema", ""),
        "table_name": row.get("table_name", ""),
        "engine": row.get("engine", ""),
        "table_rows": _to_int(row.get("table_rows")),
        "data_length": _to_int(row.get("data_length")),
        "index_length": _to_int(row.get("index_length")),
        "data_free": _to_int(row.get("data_free")),
        "shard_id": shard_id,
    }


def _format_output_row(row: Dict, logical_dbname: str) -> Dict:
    data_length = row["data_length"]
    index_length = row["index_length"]
    data_free = row["data_free"]
    total_bytes = data_length + index_length + data_free
    logical_schema = logical_dbname or _logical_schema_from_shard_db(row["table_schema"], row.get("shard_id"))
    return {
        "table_schema": logical_schema,
        "table_name": row["table_name"],
        "engine": row["engine"],
        "table_rows": row["table_rows"],
        "data_size_gb": round(data_length / _GB, 2),
        "index_size_gb": round(index_length / _GB, 2),
        "data_free_gb": round(data_free / _GB, 2),
        "data_free_ratio_pct": round(data_free / total_bytes * 100, 2) if total_bytes else 0.0,
    }


def _aggregate_shard_rows(rows: List[Dict], logical_dbname: str) -> List[Dict]:
    """按逻辑库名 + 表名汇聚各 remote slave 分片结果。"""
    merged: Dict[Tuple[str, str], Dict] = {}
    for row in rows:
        logical_schema = logical_dbname or _logical_schema_from_shard_db(row["table_schema"], row.get("shard_id"))
        key = (logical_schema, row["table_name"])
        if key not in merged:
            merged[key] = {
                "table_schema": logical_schema,
                "table_name": row["table_name"],
                "engine": row.get("engine", ""),
                "table_rows": 0,
                "data_length": 0,
                "index_length": 0,
                "data_free": 0,
            }
        acc = merged[key]
        acc["table_rows"] += row["table_rows"]
        acc["data_length"] += row["data_length"]
        acc["index_length"] += row["index_length"]
        acc["data_free"] += row["data_free"]
        if not acc["engine"] and row.get("engine"):
            acc["engine"] = row["engine"]

    result = []
    for acc in merged.values():
        if acc["data_free"] <= MIN_DATA_FREE_BYTES:
            continue
        result.append(_format_output_row(acc, logical_dbname))

    result.sort(key=lambda item: item["data_free_gb"], reverse=True)
    return result


def _execute_query_on_addresses(
    bk_cloud_id: int, addresses: List[str], query_sql: str
) -> List[Tuple[str, List[Dict]]]:
    """在指定实例上执行查询，返回 [(address, table_data), ...]。"""
    if not addresses:
        return []

    drs_raw_res = DRSApi.v2_webconsole_rpc(
        {
            "addresses": addresses,
            "cmds": [query_sql],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
            "query_timeout": 60,
        }
    )

    results = []
    for address, address_res in zip(addresses, drs_raw_res):
        if address_res["error_msg"]:
            raise DBMMcpBaseException(msg=address_res["error_msg"])
        cmd_res = address_res["cmd_results"][0]
        if cmd_res["error_msg"]:
            raise DBMMcpBaseException(msg=f"{address}: {cmd_res['error_msg']}")
        results.append((address, cmd_res.get("table_data") or []))
    return results


def _get_tendbcluster_shard_slaves(cluster_obj: Cluster) -> List[Dict]:
    shards = cluster_obj.tendbclusterstorageset_set.select_related(
        "storage_instance_tuple__receiver__machine",
    ).order_by("shard_id")
    targets = [
        {
            "address": shard.storage_instance_tuple.receiver.ip_port,
            "shard_id": shard.shard_id,
        }
        for shard in shards
    ]
    if not targets:
        raise DBMMcpBaseException(msg="TenDBCluster has no remote slave shards")
    return targets


def _query_tendbcluster_table_data_free(
    cluster_obj: Cluster,
    dbname: str,
    table_names: Optional[List[str]],
) -> Tuple[List[Dict], str]:
    """分别查询各 remote slave 分片，再按逻辑库表汇聚。"""
    shard_targets = _get_tendbcluster_shard_slaves(cluster_obj)
    bk_cloud_id = cluster_obj.bk_cloud_id
    raw_rows: List[Dict] = []
    queried_addresses: List[str] = []

    if dbname:
        for target in shard_targets:
            schema_name = _shard_schema_name(dbname, target["shard_id"])
            query_sql = _build_query_sql(schema_name, table_names)
            for address, table_data in _execute_query_on_addresses(bk_cloud_id, [target["address"]], query_sql):
                queried_addresses.append(address)
                for row in table_data:
                    raw_rows.append(_parse_raw_row(row, shard_id=target["shard_id"]))
    else:
        query_sql = _build_query_sql("", table_names)
        address_to_shard = {target["address"]: target["shard_id"] for target in shard_targets}
        addresses = list(address_to_shard.keys())
        for address, table_data in _execute_query_on_addresses(bk_cloud_id, addresses, query_sql):
            queried_addresses.append(address)
            for row in table_data:
                raw_rows.append(_parse_raw_row(row, shard_id=address_to_shard[address]))

    tables = _aggregate_shard_rows(raw_rows, dbname)
    return tables, ",".join(queried_addresses)


def _query_single_cluster_table_data_free(
    cluster_obj: Cluster,
    dbname: str,
    table_names: Optional[List[str]],
) -> Tuple[List[Dict], str]:
    bk_cloud_id, address, resolved_dbname = get_cloud_slave_address_and_dbname(
        cluster_type=cluster_obj.cluster_type,
        cluster_domain=cluster_obj.immute_domain,
        dbname=dbname,
    )
    query_sql = _build_query_sql(resolved_dbname or dbname, table_names)
    _, table_data = _execute_query_on_addresses(bk_cloud_id, [address], query_sql)[0]
    tables = [_format_output_row(_parse_raw_row(row), dbname) for row in table_data]
    return tables, address


def query_table_data_free(cluster_id: int, dbname: str = "", table_names: Optional[List[str]] = None) -> Dict:
    """查询 MySQL 表空洞碎片（information_schema.tables.data_free）。"""
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(id=cluster_id)
    cluster_domain = cluster_obj.immute_domain

    dbname = (dbname or "").strip("`").strip()
    table_names = [name.strip("`").strip() for name in (table_names or []) if name]

    if cluster_obj.cluster_type == ClusterType.TenDBCluster:
        tables, address = _query_tendbcluster_table_data_free(cluster_obj, dbname, table_names)
    else:
        tables, address = _query_single_cluster_table_data_free(cluster_obj, dbname, table_names)

    return {
        "cluster_id": cluster_id,
        "cluster_domain": cluster_domain,
        "cluster_type": str(cluster_obj.cluster_type),
        "address": address,
        "dbname": dbname,
        "tables": tables,
    }
