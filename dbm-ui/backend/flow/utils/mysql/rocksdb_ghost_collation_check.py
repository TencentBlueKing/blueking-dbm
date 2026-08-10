# -*- coding: utf-8 -*-
import logging
import re
from collections import defaultdict
from dataclasses import dataclass

from django.utils.translation import gettext as _

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.utils.mysql.mysql_bk_config import get_cluster_config, get_engine_from_bk_mysql_config

GHOST_TMP_TABLE_PROBES = ("_ghost_probe_ghc", "_ghost_probe_gho")
SUGGESTED_EXCEPTION_PATTERN = r"^_.*_gh[co]$"
ROCKSDB_COLLATION_VARS_CMD = "SHOW GLOBAL VARIABLES LIKE 'rocksdb_strict_collation%';"
DRS_ADDRESS_CHUNK_SIZE = 10

logger = logging.getLogger("flow")


@dataclass
class GhostCollationFinding:
    cluster_id: int
    cluster_domain: str
    shard_id: str | None
    role: str
    host: str
    port: int
    check_value: str
    exceptions_value: str
    reason: str


def exceptions_cover_ghost_tmp_tables(exceptions: str) -> bool:
    """检查逗号分隔的 exceptions 正则是否覆盖所有 gh-ost 临时表探针。"""
    patterns = [pattern.strip() for pattern in (exceptions or "").split(",") if pattern.strip()]
    for probe in GHOST_TMP_TABLE_PROBES:
        if not any(_regex_matches(pattern, probe) for pattern in patterns):
            return False
    return True


def _regex_matches(pattern: str, value: str) -> bool:
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


def _iter_running_remote_instances(cluster: Cluster):
    storage_sets = cluster.tendbclusterstorageset_set.select_related(
        "storage_instance_tuple__ejector__machine",
        "storage_instance_tuple__receiver__machine",
    )
    for storage_set in storage_sets:
        instance_tuple = storage_set.storage_instance_tuple
        instances = (
            (InstanceRole.REMOTE_MASTER.value, instance_tuple.ejector),
            (InstanceRole.REMOTE_SLAVE.value, instance_tuple.receiver),
        )
        for expected_role, instance in instances:
            if instance.status != InstanceStatus.RUNNING.value or instance.instance_role != expected_role:
                continue
            yield str(storage_set.shard_id), expected_role, instance


def _instance_address(instance) -> str:
    return f"{instance.machine.ip}{IP_PORT_DIVIDER}{instance.port}"


def _table_data_to_variables(table_data) -> dict[str, str]:
    variables = {}
    for row in table_data or []:
        name = row.get("Variable_name")
        if name:
            variables[name] = str(row.get("Value", ""))
    return variables


def _mark_chunk_query_failed(chunk: list[str], errors_by_address: dict[str, str], error: str):
    for address in chunk:
        errors_by_address[address] = error


def _apply_drs_variable_response(chunk: list[str], resp, variables_by_address: dict, errors_by_address: dict):
    if not resp:
        _mark_chunk_query_failed(chunk, errors_by_address, _("DRS返回为空值"))
        return

    seen = set()
    for item in resp:
        address = item.get("address", "")
        seen.add(address)
        if item.get("error_msg") or not item.get("cmd_results"):
            errors_by_address[address] = item.get("error_msg") or _("DRS返回为空值")
            continue
        try:
            table_data = item["cmd_results"][0]["table_data"]
        except (KeyError, IndexError, TypeError):
            errors_by_address[address] = _("DRS返回格式异常")
            continue
        variables_by_address[address] = _table_data_to_variables(table_data)

    for address in chunk:
        if address not in seen:
            errors_by_address[address] = _("DRS未返回该地址")


def _query_collation_chunk(bk_cloud_id: int, chunk: list[str], variables_by_address: dict, errors_by_address: dict):
    try:
        resp = DRSApi.rpc(
            {
                "addresses": chunk,
                "cmds": [ROCKSDB_COLLATION_VARS_CMD],
                "force": True,
                "bk_cloud_id": bk_cloud_id,
            }
        )
    except Exception as err:
        logger.error(
            _("批量查询 RocksDB 字符集检查变量失败，云区域 {}，错误: {}").format(bk_cloud_id, str(err)),
            exc_info=True,
        )
        _mark_chunk_query_failed(chunk, errors_by_address, str(err))
        return
    _apply_drs_variable_response(chunk, resp, variables_by_address, errors_by_address)


def _query_collation_variables(targets) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    grouped = defaultdict(list)
    for target in targets:
        instance = target[2]
        address = _instance_address(instance)
        addresses = grouped[instance.machine.bk_cloud_id]
        if address not in addresses:
            addresses.append(address)

    variables_by_address = {}
    errors_by_address = {}
    chunk_size = DRS_ADDRESS_CHUNK_SIZE
    for bk_cloud_id, addresses in grouped.items():
        for start in range(0, len(addresses), chunk_size):
            _query_collation_chunk(
                bk_cloud_id,
                addresses[start : start + chunk_size],
                variables_by_address,
                errors_by_address,
            )
    return variables_by_address, errors_by_address


def _build_finding(
    cluster: Cluster,
    shard_id: str,
    role: str,
    instance,
    check_value: str,
    exceptions_value: str,
    reason: str,
) -> GhostCollationFinding:
    return GhostCollationFinding(
        cluster_id=cluster.id,
        cluster_domain=cluster.immute_domain,
        shard_id=shard_id,
        role=role,
        host=instance.machine.ip,
        port=instance.port,
        check_value=check_value,
        exceptions_value=exceptions_value,
        reason=reason,
    )


def check_rocksdb_ghost_collation(cluster: Cluster) -> list[GhostCollationFinding]:
    """只读检查 RocksDB 节点是否允许 gh-ost 临时表绕过严格字符集检查。"""
    mysql_config = get_cluster_config(
        cluster.immute_domain,
        cluster.major_version,
        cluster.db_module_id,
        cluster.cluster_type,
        cluster.bk_biz_id,
    )
    if get_engine_from_bk_mysql_config(mysql_config).strip().lower() != "rocksdb":
        return []

    targets = list(_iter_running_remote_instances(cluster))
    variables_by_address, errors_by_address = _query_collation_variables(targets)

    findings = []
    for shard_id, role, instance in targets:
        address = _instance_address(instance)
        error = errors_by_address.get(address)
        variables = variables_by_address.get(address)
        if error is not None or variables is None:
            logger.error(
                _("查询 RocksDB 字符集检查变量失败，节点 {}:{}，错误: {}").format(
                    instance.machine.ip, instance.port, error or _("DRS未返回该地址")
                )
            )
            findings.append(_build_finding(cluster, shard_id, role, instance, "", "", "query_failed"))
            continue

        check_value = str(variables.get("rocksdb_strict_collation_check", ""))
        exceptions_value = str(variables.get("rocksdb_strict_collation_exceptions", ""))
        if check_value.strip().lower() == "on" and not exceptions_cover_ghost_tmp_tables(exceptions_value):
            findings.append(
                _build_finding(
                    cluster,
                    shard_id,
                    role,
                    instance,
                    check_value,
                    exceptions_value,
                    "missing_exception",
                )
            )
    return findings


def format_ghost_collation_findings(findings: list[GhostCollationFinding]) -> str:
    """将检查发现格式化为面向用户的文本。"""
    if not findings:
        return ""

    reason_messages = {
        "missing_exception": _("未配置覆盖 gh-ost 临时表的 RocksDB 字符集检查例外"),
        "query_failed": _("查询失败"),
    }
    lines = [
        _("集群 {} 为 RocksDB，未配置 gh-ost 临时表 exceptions 时不能执行 Online DDL。").format(findings[0].cluster_domain),
        _("异常节点："),
    ]
    for finding in findings:
        reason = reason_messages.get(finding.reason, finding.reason)
        lines.append(
            _(
                "集群 {cluster} 分片 {shard} {role} 节点 {host}:{port}: {reason}（check={check}, exceptions={exceptions}）"
            ).format(
                cluster=finding.cluster_domain,
                shard=finding.shard_id,
                role=finding.role,
                host=finding.host,
                port=finding.port,
                reason=reason,
                check=finding.check_value,
                exceptions=finding.exceptions_value,
            )
        )
    lines.extend(
        [
            _("修复建议：将 gh-ost 临时表正则加入 rocksdb_strict_collation_exceptions："),
            _("SET GLOBAL rocksdb_strict_collation_exceptions='{}';").format(SUGGESTED_EXCEPTION_PATTERN),
            _("若 rocksdb_strict_collation_exceptions 已有配置，请追加上述正则而非覆盖现有值，" "并将最终配置持久化到 dbconfig。"),
        ]
    )
    return "\n".join(lines)
