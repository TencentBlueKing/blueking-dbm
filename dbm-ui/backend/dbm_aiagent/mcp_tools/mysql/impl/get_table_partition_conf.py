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
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.db_services.partition.constants import Query_Tables_info_SQL
from backend.db_services.partition.handlers import PartitionHandler
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.helpers.get_slave_address_and_dbname import get_cloud_slave_address_and_dbname
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_ident, quote_string_literal

_PARTITION_PHASE_ONLINE = "online"
_EMPTY_EXECUTE_TIME = "0001-01-01T00:00:00Z"


def get_table_partition_conf(cluster_domain: str, db_name: str, table_name: str) -> Dict[str, Any]:
    cluster = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)
    db_name = db_name.strip("`")
    table_name = table_name.strip("`")

    return {
        "cluster": {
            "cluster_domain": cluster.immute_domain,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
        },
        "target": {"db_name": db_name, "table_name": table_name},
        "partition_conf": _query_partition_conf(cluster, db_name, table_name),
        "table_fact": _query_table_fact(cluster, db_name, table_name),
    }


def _query_partition_conf(cluster: Cluster, db_name: str, table_name: str) -> Optional[Dict[str, Any]]:
    query_params = {
        "bk_biz_id": cluster.bk_biz_id,
        "cluster_type": cluster.cluster_type,
        "immute_domains": [cluster.immute_domain],
        "dblikes": [db_name],
        "tblikes": [table_name],
        "limit": 100,
        "offset": 0,
    }
    result = PartitionHandler.query_conf_v2(query_params=query_params)
    results = result.get("results", [])
    if not results:
        return None
    return _format_partition_conf(results[0])


def _format_partition_conf(item: Dict[str, Any]) -> Dict[str, Any]:
    execute_time = item.get("execute_time")
    if isinstance(execute_time, datetime):
        execute_time = execute_time.isoformat()

    last_execute_time = None
    if execute_time and str(execute_time) != _EMPTY_EXECUTE_TIME:
        last_execute_time = str(execute_time)

    status = item.get("status") or None
    if status == "NO_EXECUTION_RECORD":
        status = None

    return {
        "config_id": item.get("id"),
        "partition_column": item.get("partition_column"),
        "partition_column_type": item.get("partition_column_type"),
        "partition_time_interval": item.get("partition_time_interval"),
        "expire_time": item.get("expire_time"),
        "dblikes": [item["dblike"]] if item.get("dblike") else [],
        "tblikes": [item["tblike"]] if item.get("tblike") else [],
        "disabled": item.get("phase", _PARTITION_PHASE_ONLINE) != _PARTITION_PHASE_ONLINE,
        "last_execute_status": status,
        "last_execute_time": last_execute_time,
    }


_FUZZY_TABLE_FACT_MSG = "库表名包含通配符 %，暂不支持模糊查询表结构"


def _query_table_fact(cluster: Cluster, db_name: str, table_name: str) -> Dict[str, Any]:
    empty_fact = {
        "exists": False,
        "is_partitioned": False,
        "create_sql": "",
        "partition_defs": [],
        "message": None,
    }

    if "%" in db_name or "%" in table_name:
        empty_fact["message"] = _FUZZY_TABLE_FACT_MSG
        return empty_fact

    # 从库查询表结构；tendbcluster 仅查 shard0，需另实现
    bk_cloud_id, address, resolved_db = get_cloud_slave_address_and_dbname(
        cluster_type=cluster.cluster_type,
        cluster_domain=cluster.immute_domain,
        dbname=db_name,
    )
    condition_sts = (
        f"TABLE_SCHEMA = {quote_string_literal(resolved_db)} " f"AND TABLE_NAME = {quote_string_literal(table_name)}"
    )
    table_info_sql = Query_Tables_info_SQL.format(condition_sts=condition_sts)
    table_rows = _drs_query_table_data(address, bk_cloud_id, table_info_sql)
    if not table_rows:
        return empty_fact

    create_options = (table_rows[0].get("CREATE_OPTIONS") or "").lower()
    is_partitioned = "partitioned" in create_options

    create_sql = _query_create_sql(address, bk_cloud_id, resolved_db, table_name)

    partition_defs: List[Dict[str, Any]] = []
    if is_partitioned:
        partition_sql = (
            "SELECT PARTITION_NAME, PARTITION_DESCRIPTION "
            "FROM information_schema.partitions "
            f"WHERE TABLE_SCHEMA = {quote_string_literal(resolved_db)} "
            f"AND TABLE_NAME = {quote_string_literal(table_name)} "
            "AND PARTITION_NAME IS NOT NULL "
            "ORDER BY PARTITION_DESCRIPTION ASC"
        )
        partition_rows = _drs_query_table_data(address, bk_cloud_id, partition_sql)
        partition_defs = [
            {
                "partition_name": row.get("PARTITION_NAME"),
                "partition_description": row.get("PARTITION_DESCRIPTION"),
            }
            for row in partition_rows
            if row.get("PARTITION_NAME")
        ]

    return {
        "exists": True,
        "is_partitioned": is_partitioned,
        "create_sql": create_sql,
        "partition_defs": partition_defs,
        "message": None,
    }


def _query_create_sql(address: str, bk_cloud_id: int, db_name: str, table_name: str) -> str:
    rows = _drs_query_table_data(
        address,
        bk_cloud_id,
        f"SHOW CREATE TABLE {quote_ident(db_name)}.{quote_ident(table_name)}",
    )
    if not rows:
        return ""

    row = rows[0]
    return row.get("Create Table") or row.get("Create View") or ""


def _drs_query_table_data(address: str, bk_cloud_id: int, sql: str) -> List[Dict[str, Any]]:
    try:
        res = DRSApi.short_rpc(
            {
                "addresses": [address],
                "cmds": [sql],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
    except Exception as e:
        raise DBMMcpBaseException(msg=str(e)) from e

    if res[0].get("error_msg"):
        raise DBMMcpBaseException(msg=res[0]["error_msg"])

    cmd_results = res[0].get("cmd_results")
    if not cmd_results:
        return []

    cmd_result = cmd_results[0]
    if cmd_result.get("error_msg"):
        raise DBMMcpBaseException(msg=cmd_result["error_msg"])

    return cmd_result.get("table_data") or []
