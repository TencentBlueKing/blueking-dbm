# -*- coding: utf-8 -*-
import logging
import re
from dataclasses import dataclass

from django.utils.translation import gettext as _

from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.utils.mysql.mysql_bk_config import get_cluster_config, get_engine_from_bk_mysql_config
from backend.flow.utils.mysql.mysql_commom_query import query_mysql_variables

GHOST_TMP_TABLE_PROBES = ("_ghost_probe_ghc", "_ghost_probe_gho")
SUGGESTED_EXCEPTION_PATTERN = r"^_.*_gh[co]$"

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
    for storage_set in cluster.tendbclusterstorageset_set.all():
        instance_tuple = storage_set.storage_instance_tuple
        instances = (
            (InstanceRole.REMOTE_MASTER.value, instance_tuple.ejector),
            (InstanceRole.REMOTE_SLAVE.value, instance_tuple.receiver),
        )
        for expected_role, instance in instances:
            if instance.status != InstanceStatus.RUNNING.value or instance.instance_role != expected_role:
                continue
            yield str(storage_set.shard_id), expected_role, instance


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

    findings = []
    for shard_id, role, instance in _iter_running_remote_instances(cluster):
        try:
            variables = query_mysql_variables(instance.machine.ip, instance.port, instance.machine.bk_cloud_id)
        except Exception as err:
            logger.error(
                _("查询 RocksDB 字符集检查变量失败，节点 {}:{}，错误: {}").format(instance.machine.ip, instance.port, str(err)),
                exc_info=True,
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
