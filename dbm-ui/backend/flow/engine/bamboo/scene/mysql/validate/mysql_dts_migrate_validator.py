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

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.consts import SYSTEM_DBS
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator, validator_log_format
from backend.flow.utils.mysql.dts.migrate_plan import build_migrate_plan, build_migrate_plans
from backend.flow.utils.mysql.dts.sync_scope_exist import scope_to_exist_query
from backend.flow.utils.mysql.mysql_bk_config import get_cluster_config, get_engine_from_bk_mysql_config

logger = logging.getLogger("root")

_COLLATION_SHOW_LIMIT = 10
_NON_TABLE_LIMIT = 11


class ClusterSqlError(Exception):
    pass


def _sql_quoted_list(names: list[str]) -> str:
    quoted = ["'{}'".format(name.replace("'", "''")) for name in names]
    return "(" + ",".join(quoted) + ")"


def _schema_scope_sql(column: str, databases: list[str]) -> str:
    return "{} IN {} AND {} NOT IN {}".format(
        column, _sql_quoted_list(databases), column, _sql_quoted_list(list(SYSTEM_DBS))
    )


def _optional_name_in_sql(column: str, names: list[str] | None) -> str:
    if not names:
        return ""
    return " AND {} IN {}".format(column, _sql_quoted_list(names))


def _row_value(row: dict, *keys):
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key.lower() in lowered:
            return lowered[key.lower()]
    return None


def _normalize_pair(charset, collation) -> tuple[str, str] | None:
    charset_text = ("" if charset is None else str(charset)).strip()
    collation_text = ("" if collation is None else str(collation)).strip()
    if not charset_text or not collation_text:
        return None
    return charset_text, collation_text


def _pair_key(charset: str, collation: str) -> tuple[str, str]:
    return charset.lower(), collation.lower()


def missing_charset_collation_pairs(source_rows, target_rows) -> list[tuple[str, str, str]]:
    target_keys = set()
    for item in target_rows or []:
        pair = _normalize_pair(item[0], item[1])
        if pair:
            target_keys.add(_pair_key(pair[0], pair[1]))
    missing = []
    seen = set()
    for row in source_rows or []:
        pair = _normalize_pair(row[0], row[1])
        if pair is None:
            continue
        key = _pair_key(pair[0], pair[1])
        if key in target_keys or key in seen:
            continue
        seen.add(key)
        sample = "" if len(row) < 3 or row[2] is None else str(row[2])
        missing.append((pair[0], pair[1], sample))
    return missing


def _format_missing_collation(target_cluster_id: int, missing: list[tuple[str, str, str]]) -> str:
    parts = [
        _("{}/{}（样例: {}）").format(charset, collation, sample)
        for charset, collation, sample in missing[:_COLLATION_SHOW_LIMIT]
    ]
    return _("目标集群 {} 不支持源端使用的字符集/排序规则: {}").format(target_cluster_id, "; ".join(parts))


def _non_table_label(object_type: str) -> str:
    labels = {
        "VIEW": _("视图"),
        "PROCEDURE": _("存储过程"),
        "FUNCTION": _("函数"),
        "TRIGGER": _("触发器"),
        "EVENT": _("事件"),
    }
    return labels.get(object_type, object_type)


def _format_non_table_objects(cluster_id: int, rows: list[tuple[str, str]]) -> str:
    parts = [
        _("{} {}").format(_non_table_label(object_type), sample) for object_type, sample in rows[:_NON_TABLE_LIMIT]
    ]
    return _("源集群 {} 同步范围内存在 DTS 不会迁移的对象: {}。确认不需要后可将 check_non_table_object 设为 false").format(
        cluster_id, "; ".join(parts)
    )


def rpc_cluster_sql(cluster_id: int, bk_biz_id: int, sql: str) -> list[dict]:
    handler = RemoteServiceHandler(bk_biz_id)
    cluster_handler, address = handler._get_cluster_address({}, cluster_id)
    rpc_results = DRSApi.rpc(
        {"bk_cloud_id": cluster_handler.cluster.bk_cloud_id, "addresses": [address], "cmds": [sql]}
    )
    if not rpc_results or rpc_results[0].get("error_msg"):
        detail = ""
        if rpc_results:
            detail = rpc_results[0].get("error_msg") or ""
        raise ClusterSqlError(_("查询集群 {} 失败: {}").format(cluster_id, detail))
    cmd_results = rpc_results[0].get("cmd_results") or [{}]
    return cmd_results[0].get("table_data") or []


def expand_source_scope(cluster_id: int, sync_scope, bk_biz_id: int) -> tuple[list[str], list[str] | None]:
    query = scope_to_exist_query(sync_scope)
    remote_handler = RemoteServiceHandler(bk_biz_id)
    keep_test = ["test"] if "test" in query.dbs else []
    databases = remote_handler.show_database_with_pattern(
        cluster_id, query.dbs, query.ignore_dbs, keep_system_dbs=keep_test
    )
    tables = None
    if databases and query.need_check_tables:
        tables = remote_handler.show_table_with_pattern(cluster_id, databases, query.tables, query.ignore_tables)
    return databases, tables


def _source_collation_sql(databases: list[str], tables: list[str] | None) -> str:
    schema_filter = _schema_scope_sql("t.TABLE_SCHEMA", databases)
    table_filter = _optional_name_in_sql("t.TABLE_NAME", tables)
    column_schema_filter = _schema_scope_sql("col.TABLE_SCHEMA", databases)
    column_table_filter = _optional_name_in_sql("col.TABLE_NAME", tables)
    return (
        "SELECT CHARACTER_SET_NAME, COLLATION_NAME, MIN(sample) AS sample FROM ("
        "SELECT c.CHARACTER_SET_NAME, t.TABLE_COLLATION AS COLLATION_NAME, "
        "CONCAT(t.TABLE_SCHEMA, '.', t.TABLE_NAME) AS sample "
        "FROM information_schema.TABLES t "
        "JOIN information_schema.COLLATION_CHARACTER_SET_APPLICABILITY c "
        "ON c.COLLATION_NAME = t.TABLE_COLLATION "
        "WHERE t.TABLE_TYPE = 'BASE TABLE' AND {schema_filter}{table_filter} "
        "UNION ALL "
        "SELECT col.CHARACTER_SET_NAME, col.COLLATION_NAME, "
        "CONCAT(col.TABLE_SCHEMA, '.', col.TABLE_NAME) AS sample "
        "FROM information_schema.COLUMNS col "
        "JOIN information_schema.TABLES t "
        "ON t.TABLE_SCHEMA = col.TABLE_SCHEMA AND t.TABLE_NAME = col.TABLE_NAME "
        "WHERE t.TABLE_TYPE = 'BASE TABLE' AND {column_schema_filter}{column_table_filter} "
        "AND col.CHARACTER_SET_NAME IS NOT NULL AND col.COLLATION_NAME IS NOT NULL"
        ") x GROUP BY CHARACTER_SET_NAME, COLLATION_NAME"
    ).format(
        schema_filter=schema_filter,
        table_filter=table_filter,
        column_schema_filter=column_schema_filter,
        column_table_filter=column_table_filter,
    )


def _parse_collation_rows(rows) -> list[tuple[str, str, str]]:
    parsed = []
    for row in rows or []:
        pair = _normalize_pair(
            _row_value(row, "CHARACTER_SET_NAME", "charset_name"),
            _row_value(row, "COLLATION_NAME", "collation_name"),
        )
        if pair is None:
            continue
        sample = _row_value(row, "sample") or ""
        parsed.append((pair[0], pair[1], str(sample)))
    return parsed


def query_source_charset_collations(cluster_id: int, sync_scope, bk_biz_id: int) -> list[tuple[str, str, str]]:
    databases, tables = expand_source_scope(cluster_id, sync_scope, bk_biz_id)
    if not databases:
        return []
    rows = rpc_cluster_sql(cluster_id, bk_biz_id, _source_collation_sql(databases, tables))
    return _parse_collation_rows(rows)


def query_target_collations(cluster_id: int, bk_biz_id: int) -> list[tuple[str, str]]:
    sql = "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLLATIONS"
    parsed = _parse_collation_rows(rpc_cluster_sql(cluster_id, bk_biz_id, sql))
    return [(row[0], row[1]) for row in parsed]


def _non_table_sql(databases: list[str]) -> str:
    view_filter = _schema_scope_sql("TABLE_SCHEMA", databases)
    routine_filter = _schema_scope_sql("ROUTINE_SCHEMA", databases)
    trigger_filter = _schema_scope_sql("TRIGGER_SCHEMA", databases)
    event_filter = _schema_scope_sql("EVENT_SCHEMA", databases)
    return (
        "SELECT object_type, sample FROM ("
        "SELECT 'VIEW' AS object_type, CONCAT(TABLE_SCHEMA, '.', TABLE_NAME) AS sample "
        "FROM information_schema.TABLES WHERE TABLE_TYPE = 'VIEW' AND {view_filter} "
        "UNION ALL "
        "SELECT ROUTINE_TYPE AS object_type, CONCAT(ROUTINE_SCHEMA, '.', ROUTINE_NAME) AS sample "
        "FROM information_schema.ROUTINES "
        "WHERE {routine_filter} AND ROUTINE_TYPE IN ('PROCEDURE', 'FUNCTION') "
        "UNION ALL "
        "SELECT 'TRIGGER' AS object_type, CONCAT(TRIGGER_SCHEMA, '.', TRIGGER_NAME) AS sample "
        "FROM information_schema.TRIGGERS WHERE {trigger_filter} "
        "UNION ALL "
        "SELECT 'EVENT' AS object_type, CONCAT(EVENT_SCHEMA, '.', EVENT_NAME) AS sample "
        "FROM information_schema.EVENTS WHERE {event_filter}"
        ") x LIMIT {limit}"
    ).format(
        view_filter=view_filter,
        routine_filter=routine_filter,
        trigger_filter=trigger_filter,
        event_filter=event_filter,
        limit=_NON_TABLE_LIMIT,
    )


def _parse_non_table_rows(rows) -> list[tuple[str, str]]:
    parsed = []
    for row in rows or []:
        object_type = _row_value(row, "object_type")
        sample = _row_value(row, "sample")
        if object_type is None or sample is None:
            continue
        object_text = str(object_type).strip().upper()
        sample_text = str(sample).strip()
        if not object_text or not sample_text:
            continue
        parsed.append((object_text, sample_text))
    return parsed


def query_non_table_objects(cluster_id: int, sync_scope, bk_biz_id: int) -> list[tuple[str, str]]:
    # 单表迁移也要看到该库里的过程、函数、触发器和事件，所以只按库过滤。
    databases = expand_source_scope(cluster_id, sync_scope, bk_biz_id)[0]
    if not databases:
        return []
    return _parse_non_table_rows(rpc_cluster_sql(cluster_id, bk_biz_id, _non_table_sql(databases)))


def read_cluster_default_engine(cluster) -> str:
    config = get_cluster_config(
        cluster.immute_domain,
        cluster.major_version,
        cluster.db_module_id,
        cluster.cluster_type,
        cluster.bk_biz_id,
    )
    return get_engine_from_bk_mysql_config(config)


def _plans_from_details(details: dict):
    if details.get("infos"):
        return build_migrate_plans(details, require_task_name=False)
    return [build_migrate_plan(details, require_task_name=False)]


def _iter_sources(plans):
    for index, plan in enumerate(plans):
        for spec in plan.task_specs:
            for source in spec.sources:
                yield index, spec, source


def _collect_cluster_ids(plans) -> set[int]:
    cluster_ids: set[int] = set()
    for plan in plans:
        for spec in plan.task_specs:
            cluster_ids.add(spec.target_cluster_id)
            for source in spec.sources:
                cluster_ids.add(source.cluster_id)
    return cluster_ids


def _load_clusters(cluster_ids: set[int]) -> dict:
    if not cluster_ids:
        return {}
    return {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}


def _missing_cluster_message(clusters: dict, source_id: int, target_id: int) -> str:
    if clusters.get(source_id) is None:
        return _("集群 {} 不存在").format(source_id)
    return _("集群 {} 不存在").format(target_id)


def _engine_pair_message(clusters: dict, cache: dict, source_id: int, target_id: int) -> str:
    if clusters.get(source_id) is None or clusters.get(target_id) is None:
        return _missing_cluster_message(clusters, source_id, target_id)
    try:
        source_engine = _cached_engine(cache, clusters[source_id])
        target_engine = _cached_engine(cache, clusters[target_id])
    except Exception as exc:
        logger.exception(_("读取集群默认存储引擎失败"))
        return _("读取集群 {} 与 {} 的默认存储引擎失败: {}").format(source_id, target_id, exc)
    if source_engine.strip().lower() == target_engine.strip().lower():
        return ""
    return _("源集群 {} 默认存储引擎 {} 与目标集群 {} 默认存储引擎 {} 不同").format(source_id, source_engine, target_id, target_engine)


def _cached_engine(cache: dict, cluster) -> str:
    if cluster.id not in cache:
        cache[cluster.id] = read_cluster_default_engine(cluster)
    return cache[cluster.id]


class MysqlDtsMigrateFlowValidator(MysqlBaseValidator):
    @validator_log_format
    def _emit_error(self, message: str):
        return message

    def _row_error(self, index: int, message: str) -> dict:
        row_key = ""
        infos = self.data.get("infos") or []
        if index < len(infos) and isinstance(infos[index], dict):
            row_key = infos[index].get("row_key") or ""
        return self._emit_error(message, **self.create_log_tag(field="cluster_id", index=index, row_key=row_key))

    def _charset_errors(self, plans, clusters: dict) -> list:
        errors = []
        target_cache: dict[int, list] = {}
        for index, spec, source in _iter_sources(plans):
            message = self._charset_source_message(clusters, target_cache, spec, source)
            if message:
                errors.append(self._row_error(index, message))
        return errors

    def _charset_source_message(self, clusters, target_cache, spec, source) -> str:
        source_cluster = clusters.get(source.cluster_id)
        target_cluster = clusters.get(spec.target_cluster_id)
        if source_cluster is None or target_cluster is None:
            return _missing_cluster_message(clusters, source.cluster_id, spec.target_cluster_id)
        try:
            source_rows = query_source_charset_collations(
                source.cluster_id, source.sync_scope, source_cluster.bk_biz_id
            )
            if spec.target_cluster_id not in target_cache:
                target_cache[spec.target_cluster_id] = query_target_collations(
                    spec.target_cluster_id, target_cluster.bk_biz_id
                )
        except Exception as exc:
            logger.exception(_("查询集群 {} 字符集/排序规则失败").format(source.cluster_id))
            return _("查询集群 {} 字符集/排序规则失败: {}").format(source.cluster_id, exc)
        missing = missing_charset_collation_pairs(source_rows, target_cache[spec.target_cluster_id])
        if not missing:
            return ""
        return _format_missing_collation(spec.target_cluster_id, missing)

    def _engine_errors(self, plans, clusters: dict) -> list:
        errors = []
        seen_pairs: set[tuple[int, int]] = set()
        cache: dict = {}
        for index, spec, source in _iter_sources(plans):
            pair = (source.cluster_id, spec.target_cluster_id)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            message = _engine_pair_message(clusters, cache, pair[0], pair[1])
            if message:
                errors.append(self._row_error(index, message))
        return errors

    def _non_table_errors(self, plans, clusters: dict) -> list:
        errors = []
        for index, plan in enumerate(plans):
            for spec in plan.task_specs:
                for source in spec.sources:
                    message = self._non_table_source_message(clusters, source)
                    if message:
                        errors.append(self._row_error(index, message))
        return errors

    def _non_table_source_message(self, clusters, source) -> str:
        source_cluster = clusters.get(source.cluster_id)
        if source_cluster is None:
            return _("集群 {} 不存在").format(source.cluster_id)
        try:
            rows = query_non_table_objects(source.cluster_id, source.sync_scope, source_cluster.bk_biz_id)
        except Exception as exc:
            logger.exception(_("查询集群 {} 的视图、存储过程、函数、触发器和事件失败").format(source.cluster_id))
            return _("查询集群 {} 的视图、存储过程、函数、触发器和事件失败: {}").format(source.cluster_id, exc)
        if not rows:
            return ""
        return _format_non_table_objects(source.cluster_id, rows)

    def __call__(self):
        plans = _plans_from_details(self.data)
        clusters = _load_clusters(_collect_cluster_ids(plans))
        errors = []
        errors.extend(self._charset_errors(plans, clusters))
        errors.extend(self._engine_errors(plans, clusters))
        if self.data.get("check_non_table_object", True):
            errors.extend(self._non_table_errors(plans, clusters))
        return errors or None
