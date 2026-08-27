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
import logging
import os
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components.sql_import.client import SQLSimulationApi
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_report.models import MysqlDbTableSize, MysqlSqlExecDuration
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ

logger = logging.getLogger("root")


def syntax_check_sql_impl(sqls: list, cluster_type: str, versions: list = None) -> dict:
    """
    Check SQL syntax against multiple MySQL versions.

    This function calls the DBM syntax_check_sql interface to validate SQL syntax
    against specified MySQL versions. If versions is not provided, it defaults to
    checking against 5.5, 5.6, 5.7, and 8.0.

    Args:
        sqls: List of SQL statements to check
        cluster_type: Cluster type for the SQL check
        versions: List of MySQL versions to check against. Defaults to ["5.5", "5.6", "5.7", "8.0"]

    Returns:
        dict: Raw response data from the syntax_check_sql interface

    Raises:
        Exception: When the interface call fails
    """
    # Set default versions if not provided
    if versions is None or len(versions) == 0:
        versions = ["5.5", "5.6", "5.7", "8.0"]
        logger.info(_("No versions provided, using default versions: {}").format(versions))

    # Prepare request parameters
    request_params = {"cluster_type": cluster_type, "versions": versions, "sqls": sqls}

    logger.info(
        _("Starting SQL syntax check. Cluster type: {}, Versions: {}, Number of SQL statements: {}").format(
            cluster_type, versions, len(sqls)
        )
    )

    try:
        # Call the syntax_check_sql interface
        result = SQLSimulationApi.syntax_check_sql(params=request_params, headers={"platform": "mcp"})

        logger.info(_("SQL syntax check completed successfully for {} statements").format(len(sqls)))
        return result
    except Exception as e:
        logger.error(
            _("SQL syntax check failed. Cluster type: {}, Versions: {}, Error: {}").format(
                cluster_type, versions, str(e)
            )
        )
        raise


def check_sql_file_grammar(cluster_type: str, path: str, file_list: list, versions: list = None) -> dict:
    """
    Check SQL file grammar against multiple MySQL versions.

    **Prerequisite**: All SQL files in file_list MUST have been uploaded to BKRepo (蓝鲸制品库)
    before calling this function. This API does NOT upload files; it only reads files that
    already exist in BKRepo at the specified path.

    This function calls the DBM grammar_check interface to validate SQL syntax
    from files stored in BKRepo. The execute_objects parameter is automatically
    constructed based on the file_list.

    Args:
        cluster_type: Cluster type for the SQL check
        path: BKRepo directory path where SQL files are stored (e.g. '/bkdbm/sqlfiles/20240101/').
              Files must already be uploaded to BKRepo at this path before calling.
        file_list: List of SQL file names (filenames only, not full paths) to check.
                   Each file must exist in BKRepo under the given path.
        versions: List of MySQL versions to check against. Defaults to ["5.5", "5.6", "5.7", "8.0"]

    Returns:
        dict: Raw response data from the grammar_check interface

    Raises:
        Exception: When the interface call fails
    """
    # Set default versions if not provided
    if versions is None or len(versions) == 0:
        versions = ["5.5", "5.6", "5.7", "8.0"]
        logger.info(_("No versions provided, using default versions: {}").format(versions))

    # Automatically construct execute_objects based on file_list
    execute_objects = [
        {
            "line_id": 1,
            "sql_files": file_list,
            "ignore_dbnames": [],
            "dbnames": [],
        }
    ]

    # Prepare request parameters
    request_params = {
        "cluster_type": cluster_type,
        "path": path,
        "files": file_list,
        "execute_objects": execute_objects,
    }

    logger.info(
        _("Starting SQL file grammar check. Cluster type: {}, Path: {}, Files: {}, Versions: {}").format(
            cluster_type, path, file_list, versions
        )
    )

    try:
        # Call the grammar_check interface
        result = SQLSimulationApi.grammar_check(params=request_params, headers={"platform": "mcp"})

        logger.info(_("SQL file grammar check completed successfully for {} files").format(len(file_list)))
        return result
    except Exception as e:
        logger.error(
            _("SQL file grammar check failed. Cluster type: {}, Path: {}, Files: {}, Error: {}").format(
                cluster_type, path, file_list, str(e)
            )
        )
        raise


LARGE_TABLE_MIN_BYTES = 500 * 1024 * 1024
_SIZE_LOOKBACK_HOURS = 48
_GIB = 1024**3
_MIB = 1024**2

DDL_ALTER = "alter_tables"
DDL_DROP = "drop_tables"
DDL_TRUNCATE = "truncate_tables"

# tmysqlparse command 原样入库：truncate 为 "truncate"；兼容历史 truncate_table
DDL_TO_SQL_TYPES = {
    DDL_ALTER: ("alter_table",),
    DDL_DROP: ("drop_table",),
    DDL_TRUNCATE: ("truncate", "truncate_table"),
}
SIZE_ROLE_FALLBACKS = (InstanceInnerRole.SLAVE.value, InstanceInnerRole.ORPHAN.value)

# (cluster_id, cluster_domain, db_name, table_name, ddl_type)
LargeTableTarget = Tuple[int, str, str, str, str]


def parse_sql_file_statement_impl(
    path: str,
    file_list: list,
    include_sql_text: bool = False,
    cluster_ids: list = None,
    execute_objects: list = None,
) -> dict:
    """
    Parse SQL files in BKRepo for command counts; optionally identify large DDL tables.

    **Prerequisite**: All SQL files in file_list MUST have been uploaded to BKRepo
    before calling this function. This API does NOT upload files.

    Always sends include_sql_text to the Go API (default False). Omitting the field
    would make Go default to True and return ALTER sql_text.

    Go 返回的 alter/drop/truncate 列表仅作内部入参，MCP 对外不回传。
    """
    request_params = {
        "path": path,
        "files": file_list,
        "include_sql_text": include_sql_text,
    }

    logger.info(
        _("Starting SQL file statement parse. Path: {}, Files: {}, include_sql_text: {}").format(
            path, file_list, include_sql_text
        )
    )

    try:
        result = SQLSimulationApi.parse_file_statement(params=request_params, headers={"platform": "mcp"})
        logger.info(_("SQL file statement parse completed successfully for {} files").format(len(file_list)))
    except Exception as e:
        logger.error(
            _("SQL file statement parse failed. Path: {}, Files: {}, Error: {}").format(path, file_list, str(e))
        )
        raise

    large_tables: List[Dict[str, Any]] = []
    if cluster_ids:
        large_tables = _collect_large_tables(result or {}, cluster_ids, execute_objects or [])

    return {
        "command_counts": (result or {}).get("command_counts") or {},
        "file_command_counts": (result or {}).get("file_command_counts") or {},
        "large_tables": large_tables,
    }


def _format_capacity(size_bytes: int) -> str:
    """1024 进制；>=1GiB 用 G 否则 M；最多 1 位小数，整数去掉 .0。"""
    unit_size = _GIB if size_bytes >= _GIB else _MIB
    unit = "G" if size_bytes >= _GIB else "M"
    text = f"{size_bytes / unit_size:.1f}"
    if text.endswith(".0"):
        return f"{int(float(text))}{unit}"
    return f"{text}{unit}"


def _format_duration(duration_sec: float) -> str:
    text = f"{float(duration_sec):.1f}"
    if text.endswith(".0"):
        return f"{int(float(text))}s"
    return f"{text}s"


def _iter_ddl_refs(parse_result: dict) -> Iterable[Tuple[str, str, str, str]]:
    """yield (file_name, db_name, table_name, ddl_type)。"""
    for file_group in parse_result.get("alter_tables") or []:
        file_name = file_group.get("file_name") or ""
        for ref in file_group.get("alters") or []:
            table_name = ref.get("table_name") or ""
            if table_name:
                yield file_name, ref.get("db_name") or "", table_name, DDL_ALTER
    for ddl_type, group_key in ((DDL_DROP, "drop_tables"), (DDL_TRUNCATE, "truncate_tables")):
        for file_group in parse_result.get(group_key) or []:
            file_name = file_group.get("file_name") or ""
            for ref in file_group.get("tables") or []:
                table_name = ref.get("table_name") or ""
                if table_name:
                    yield file_name, ref.get("db_name") or "", table_name, ddl_type


def _execute_object_applies(execute_obj: dict, file_name: str) -> bool:
    sql_files = execute_obj.get("sql_files") or []
    if not sql_files:
        return True
    target = os.path.basename(file_name)
    return any(os.path.basename(name) == target for name in sql_files)


def _load_clusters(cluster_ids: List[int]) -> List[Any]:
    clusters = list(Cluster.objects.using(MYSQL_MCP_DB_READ).filter(id__in=cluster_ids))
    cluster_by_id = {cluster.id: cluster for cluster in clusters}
    return [cluster_by_id[cid] for cid in cluster_ids if cid in cluster_by_id]


def _expand_dbnames(cluster, dbnames: List[str], ignore_dbnames: List[str], cache: dict) -> List[str]:
    if not dbnames:
        return []
    cache_key = (cluster.id, tuple(dbnames), tuple(ignore_dbnames))
    if cache_key in cache:
        return cache[cache_key]
    try:
        databases = RemoteServiceHandler(bk_biz_id=cluster.bk_biz_id).show_database_with_pattern(
            cluster.id, list(dbnames), list(ignore_dbnames)
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("展开集群 {} 库名失败 dbnames={} ignore={}: {}").format(cluster.id, dbnames, ignore_dbnames, str(e)))
        databases = []
    cache[cache_key] = list(databases or [])
    return cache[cache_key]


def _collect_targets(parse_result: dict, clusters: List[Any], execute_objects: List[dict]) -> List[LargeTableTarget]:
    expand_cache: dict = {}
    seen = set()
    targets: List[LargeTableTarget] = []
    for file_name, db_name, table_name, ddl_type in _iter_ddl_refs(parse_result):
        for cluster in clusters:
            db_names = (
                [db_name] if db_name else _expand_dbs_for_file(cluster, file_name, execute_objects, expand_cache)
            )
            for real_db in db_names:
                if not real_db:
                    continue
                key = (cluster.id, real_db, table_name, ddl_type)
                if key in seen:
                    continue
                seen.add(key)
                targets.append((cluster.id, cluster.immute_domain, real_db, table_name, ddl_type))
    return targets


def _expand_dbs_for_file(cluster, file_name: str, execute_objects: List[dict], cache: dict) -> List[str]:
    if not execute_objects:
        return []
    databases = []
    seen = set()
    for execute_obj in execute_objects:
        if not _execute_object_applies(execute_obj, file_name):
            continue
        for db_name in _expand_dbnames(
            cluster, execute_obj.get("dbnames") or [], execute_obj.get("ignore_dbnames") or [], cache
        ):
            if db_name in seen:
                continue
            seen.add(db_name)
            databases.append(db_name)
    return databases


def _lookback_window():
    base_time = timezone.now()
    return base_time - timedelta(hours=_SIZE_LOOKBACK_HOURS), base_time


def _query_latest_table_sizes(targets: List[LargeTableTarget]) -> Dict[Tuple[str, str, str], int]:
    domains = sorted({item[1] for item in targets})
    db_names = sorted({item[2] for item in targets})
    table_names = sorted({item[3] for item in targets})
    if not domains or not db_names or not table_names:
        return {}
    start_time, base_time = _lookback_window()
    found: Dict[Tuple[str, str, str], int] = {}
    wanted = {(item[1], item[2], item[3]) for item in targets}
    try:
        for role in SIZE_ROLE_FALLBACKS:
            qs = (
                MysqlDbTableSize.objects.filter(
                    cluster_domain__in=domains,
                    instance_role=role,
                    dteventtimehour__gte=start_time,
                    dteventtimehour__lte=base_time,
                    database_name__in=db_names,
                    table_name__in=table_names,
                )
                .values("cluster_domain", "database_name", "table_name", "dteventtimehour")
                .annotate(table_size=Sum("table_size"))
                .order_by("cluster_domain", "database_name", "table_name", "-dteventtimehour")
            )
            for item in qs:
                key = (item["cluster_domain"], item["database_name"], item["table_name"])
                if key not in wanted or key in found:
                    continue
                if item.get("table_size") is None:
                    continue
                found[key] = int(item["table_size"])
            if len(found) == len(wanted):
                break
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("查询表容量失败: {}").format(str(e)))
        return {}
    return found


def _query_last_change_records(targets: List[LargeTableTarget]) -> Dict[Tuple[int, str, str, str], Any]:
    cluster_ids = sorted({item[0] for item in targets})
    db_names = sorted({item[2] for item in targets})
    table_names = sorted({item[3] for item in targets})
    sql_types = sorted({sql_type for item in targets for sql_type in DDL_TO_SQL_TYPES[item[4]]})
    if not cluster_ids:
        return {}
    try:
        rows = MysqlSqlExecDuration.objects.filter(
            cluster_id__in=cluster_ids,
            db_name__in=db_names,
            table_name__in=table_names,
            sql_type__in=sql_types,
        ).order_by("-created_at")
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(_("查询 SQL 执行耗时失败: {}").format(str(e)))
        return {}
    latest: Dict[Tuple[int, str, str, str], Any] = {}
    for row in rows:
        key = (row.cluster_id, row.db_name, row.table_name, row.sql_type)
        if key in latest:
            continue
        latest[key] = row
    return latest


def _pick_last_change(records, cluster_id: int, db_name: str, table_name: str, ddl_type: str):
    best = None
    for sql_type in DDL_TO_SQL_TYPES[ddl_type]:
        rec = records.get((cluster_id, db_name, table_name, sql_type))
        if rec is None:
            continue
        if best is None or rec.created_at > best.created_at:
            best = rec
    return best


def _build_last_change_info(rec) -> Optional[dict]:
    if rec is None:
        return None
    info = {}
    if rec.ticket_id:
        info["ticket_id"] = rec.ticket_id
    if rec.table_size is not None:
        info["table_size"] = _format_capacity(int(rec.table_size))
    if rec.duration_sec is not None:
        info["duration"] = _format_duration(rec.duration_sec)
    return info or None


def _build_large_table_item(table_name: str, size_bytes: int, last_rec) -> dict:
    item = {"name": table_name, "size": _format_capacity(size_bytes)}
    last_info = _build_last_change_info(last_rec)
    if last_info:
        item["last_change_info"] = last_info
    return item


def _nest_large_tables(targets: List[LargeTableTarget], sizes: dict, records: dict) -> List[dict]:
    clustered: Dict[int, dict] = {}
    db_order: Dict[int, List[str]] = {}
    for cluster_id, domain, db_name, table_name, ddl_type in targets:
        size = sizes.get((domain, db_name, table_name))
        if size is None or size < LARGE_TABLE_MIN_BYTES:
            continue
        cluster_payload = clustered.setdefault(
            cluster_id, {"cluster_id": cluster_id, "cluster_domain": domain, "databases": {}}
        )
        databases = cluster_payload["databases"]
        if db_name not in databases:
            databases[db_name] = {}
            db_order.setdefault(cluster_id, []).append(db_name)
        db_payload = databases[db_name]
        items = db_payload.setdefault(ddl_type, [])
        if any(item["name"] == table_name for item in items):
            continue
        items.append(
            _build_large_table_item(
                table_name,
                size,
                _pick_last_change(records, cluster_id, db_name, table_name, ddl_type),
            )
        )
    result = []
    for cluster_id in dict.fromkeys(item[0] for item in targets):
        if cluster_id not in clustered:
            continue
        payload = clustered[cluster_id]
        ordered_dbs = {}
        for db_name in db_order.get(cluster_id, []):
            ordered_dbs[db_name] = payload["databases"][db_name]
        payload["databases"] = ordered_dbs
        result.append(payload)
    return result


def _collect_large_tables(parse_result: dict, cluster_ids: List[int], execute_objects: List[dict]) -> List[dict]:
    clusters = _load_clusters(cluster_ids)
    if not clusters:
        logger.warning(_("未找到 cluster_ids={} 对应的集群，跳过大表识别").format(cluster_ids))
        return []
    targets = _collect_targets(parse_result, clusters, execute_objects)
    if not targets:
        return []
    sizes = _query_latest_table_sizes(targets)
    large_targets = [item for item in targets if sizes.get((item[1], item[2], item[3]), -1) >= LARGE_TABLE_MIN_BYTES]
    records = _query_last_change_records(large_targets) if large_targets else {}
    return _nest_large_tables(targets, sizes, records)
