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
import importlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

from django.db import IntegrityError
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.enums import MysqlConfigConsistencySubType, ReportStateType
from backend.db_report.models import MysqlConfigConsistencyReport
from backend.flow.utils.mysql.cluster_variables.collector import collect_cluster_runtime_variables
from backend.flow.utils.mysql.cluster_variables.diff import (
    build_tendbcluster_variable_diff,
    build_tendbha_variable_diff,
)

_config_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.config")
BOOL_NORMALIZE_VARS = _config_mod.BOOL_NORMALIZE_VARS
SPIDER_HIGH_IMPACT_VARS = _config_mod.SPIDER_HIGH_IMPACT_VARS
STORAGE_HIGH_IMPACT_VARS = _config_mod.STORAGE_HIGH_IMPACT_VARS
MysqlConfigConsistencyConfig = _config_mod.MysqlConfigConsistencyConfig

logger = logging.getLogger("root")

SUPPORTED_CLUSTER_TYPES = (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value)
TEMP_CLUSTER_DOMAIN_RE = re.compile(r"^.*-tmp[0-9]{8}-[0-9]{7}.*$")
# 周频巡检连续失败天数回溯窗口（覆盖上一周 7 天 + 1 天余量）
WEEKLY_FAILED_DAYS_LOOKBACK = 8
MAX_MSG_LENGTH = 4000


@dataclass
class CheckEvaluation:
    state: str
    diff_count: int = 0
    high_impact_count: int = 0
    diff_variables: List[str] = field(default_factory=list)
    msg: str = ""
    diff_detail: Dict[str, Any] = field(default_factory=dict)


def _make_whitelist_skip_fn(allowed_vars: Sequence[str]) -> Callable[[str], bool]:
    allowed = frozenset(str(v).lower() for v in allowed_vars if v)

    def _should_skip(name: str) -> bool:
        return (name or "").lower() not in allowed

    return _should_skip


def _truncate_msg(text: str) -> str:
    if len(text) <= MAX_MSG_LENGTH:
        return text
    return text[: MAX_MSG_LENGTH - 3] + "..."


def _format_errors_summary(addr_errors: Dict[str, str]) -> str:
    if not addr_errors:
        return ""
    parts = [f"{addr}({err})" for addr, err in sorted(addr_errors.items())]
    return _("采集失败实例: {}").format("; ".join(parts))


def _collect_mismatch_stats(mismatches: List[Dict], var_severity: Dict[str, str]) -> None:
    for item in mismatches:
        vname = item["variable_name"]
        sev = item.get("severity", "warn")
        if vname not in var_severity or sev == "high":
            var_severity[vname] = sev


def _finalize_evaluation(
    var_severity: Dict[str, str],
    msg_parts: List[str],
    addr_errors: Dict[str, str],
    diff_detail: Dict[str, Any],
) -> CheckEvaluation:
    if addr_errors:
        msg_parts.append(_format_errors_summary(addr_errors))

    diff_variables = sorted(var_severity.keys())
    high_impact_count = sum(1 for sev in var_severity.values() if sev == "high")
    diff_count = len(diff_variables)

    if addr_errors or high_impact_count > 0:
        state = ReportStateType.ABNORMAL.value
    elif diff_count > 0:
        state = ReportStateType.WARNING.value
    else:
        state = ReportStateType.NORMAL.value

    msg = _truncate_msg("; ".join(msg_parts)) if msg_parts else _("配置一致")
    return CheckEvaluation(
        state=state,
        diff_count=diff_count,
        high_impact_count=high_impact_count,
        diff_variables=diff_variables,
        msg=msg,
        diff_detail=diff_detail,
    )


def _format_pair_mismatches(mismatches: List[Dict]) -> str:
    items = [
        f"[{m.get('severity', 'warn')}] {m['variable_name']}({m.get('master_value')} != {m.get('slave_value')})"
        for m in mismatches
    ]
    return ", ".join(items)


def evaluate_tendbha_diff(diff_res: Dict[str, Any], addr_errors: Optional[Dict[str, str]] = None) -> CheckEvaluation:
    """将 TenDBHA 主从对比结果转换为可落库的巡检评估结果。"""
    errors = addr_errors or {}
    pairs = diff_res.get("replication_pairs") or []
    var_severity: Dict[str, str] = {}
    msg_parts: List[str] = []

    for pair in pairs:
        mismatches = pair.get("mismatches") or []
        _collect_mismatch_stats(mismatches, var_severity)
        master_addr = pair.get("master") or ""
        if pair.get("scope") == "replica_group":
            slaves_str = ",".join(pair.get("affected_slaves") or [])
            prefix = f"{master_addr} vs [{slaves_str}]"
        else:
            prefix = f"{master_addr} vs {pair.get('slave') or ''}"
        msg_parts.append(f"{prefix}: {_format_pair_mismatches(mismatches)}")

    detail = {
        "replication_pairs": pairs,
        "errors": errors,
    }
    return _finalize_evaluation(var_severity, msg_parts, errors, detail)


def evaluate_tendbcluster_spider_diff(
    diff_res: Dict[str, Any],
    spider_errors: Optional[Dict[str, str]] = None,
    *,
    check_version: bool = True,
) -> CheckEvaluation:
    """评估 TenDBCluster Spider Master 间配置及版本一致性；版本不一致时跳过参数对比。"""
    errors = spider_errors or {}
    spider_groups = diff_res.get("spider_groups") or []
    spider_version = diff_res.get("spider_version") or {"consistent": True, "by_version": {}}

    var_severity: Dict[str, str] = {}
    msg_parts: List[str] = []

    version_mismatch = check_version and not spider_version.get("consistent", True)
    if version_mismatch:
        var_severity["version"] = "high"
        by_ver = spider_version.get("by_version") or {}
        ver_desc = " vs ".join(f"{ver}=[{','.join(addrs)}]" for ver, addrs in by_ver.items())
        msg_parts.append(_("[high] version: {}（版本不一致，已跳过参数一致性对比）").format(ver_desc))
        detail = {
            "spider_version": spider_version,
            "spider_groups": [],
            "skipped_param_diff": True,
            "errors": errors,
        }
        return _finalize_evaluation(var_severity, msg_parts, errors, detail)

    for group in spider_groups:
        mismatches = group.get("mismatches") or []
        _collect_mismatch_stats(mismatches, var_severity)
        for item in mismatches:
            by_val = item.get("by_value") or {}
            val_desc = " vs ".join(f"{val}=[{','.join(addrs)}]" for val, addrs in by_val.items())
            msg_parts.append(f"[{item.get('severity', 'warn')}] {item['variable_name']}: {val_desc}")

    detail = {
        "spider_version": spider_version,
        "spider_groups": spider_groups,
        "skipped_param_diff": False,
        "errors": errors,
    }
    return _finalize_evaluation(var_severity, msg_parts, errors, detail)


def evaluate_tendbcluster_shard_diff(
    diff_res: Dict[str, Any],
    shard_errors: Optional[Dict[str, str]] = None,
) -> CheckEvaluation:
    """评估 TenDBCluster 存储分片配置一致性（单分片主从 + 跨分片 remote_master 间）。"""
    errors = shard_errors or {}
    shard_pairs = diff_res.get("shard_pairs") or []
    remote_master_mismatches = diff_res.get("remote_master_mismatches") or []
    var_severity: Dict[str, str] = {}
    msg_parts: List[str] = []

    for pair in shard_pairs:
        mismatches = pair.get("mismatches") or []
        _collect_mismatch_stats(mismatches, var_severity)
        master_addr = pair.get("master") or ""
        slave_addr = pair.get("slave") or ""
        if pair.get("scope") == "shard_group":
            shards_str = ",".join(str(sid) for sid in (pair.get("affected_shards") or []))
            prefix = _("[分片内主从] 分片[{}](示例 {} vs {})").format(shards_str, master_addr, slave_addr)
        else:
            prefix = _("[分片内主从] 分片[{}]({} vs {})").format(pair.get("shard_id"), master_addr, slave_addr)
        msg_parts.append(f"{prefix}: {_format_pair_mismatches(mismatches)}")

    if remote_master_mismatches:
        _collect_mismatch_stats(remote_master_mismatches, var_severity)
        for item in remote_master_mismatches:
            by_val = item.get("by_value") or {}
            val_desc = " vs ".join(f"{val}=[{','.join(addrs)}]" for val, addrs in by_val.items())
            msg_parts.append(
                _("[跨分片主节点] [{}] {}: {}").format(item.get("severity", "warn"), item["variable_name"], val_desc)
            )

    detail = {
        "shard_pairs": shard_pairs,
        "remote_master_mismatches": remote_master_mismatches,
        "errors": errors,
    }
    return _finalize_evaluation(var_severity, msg_parts, errors, detail)


def calculate_failed_days(
    last_record: Optional[MysqlConfigConsistencyReport],
    current_state: str,
    current_time: datetime,
) -> int:
    """适配周频巡检的连续失败天数计算：恢复归零，同日重跑不虚增，跨日按自然天数累加，超回溯窗口重置为 1。"""
    if current_state == ReportStateType.NORMAL.value:
        return 0
    if not last_record or last_record.state == ReportStateType.NORMAL.value:
        return 1

    elapsed_days = (current_time - last_record.create_at).days
    if elapsed_days > WEEKLY_FAILED_DAYS_LOOKBACK:
        return 1
    if elapsed_days < 1:
        return max(1, last_record.failed_days)
    return last_record.failed_days + elapsed_days


def _apply_report_fields(
    record: MysqlConfigConsistencyReport,
    cluster: Cluster,
    evaluation: CheckEvaluation,
    *,
    is_normal: bool,
    failed_days: int,
    creator: str,
    now: datetime,
) -> MysqlConfigConsistencyReport:
    record.bk_biz_id = cluster.bk_biz_id
    record.bk_cloud_id = cluster.bk_cloud_id
    record.cluster = cluster.immute_domain
    record.cluster_type = cluster.cluster_type
    record.state = evaluation.state
    record.status = is_normal
    record.failed_days = failed_days
    record.diff_count = evaluation.diff_count
    record.high_impact_count = evaluation.high_impact_count
    record.diff_variables = evaluation.diff_variables
    record.diff_detail = evaluation.diff_detail
    record.msg = evaluation.msg
    record.updater = creator
    record.create_at = now
    record.update_at = now
    record.save(
        update_fields=[
            "bk_biz_id",
            "bk_cloud_id",
            "cluster",
            "cluster_type",
            "state",
            "status",
            "failed_days",
            "diff_count",
            "high_impact_count",
            "diff_variables",
            "diff_detail",
            "msg",
            "updater",
            "create_at",
            "update_at",
        ]
    )
    return record


def save_consistency_report(
    cluster: Cluster,
    subtype: str,
    evaluation: CheckEvaluation,
    creator: str = "system",
) -> MysqlConfigConsistencyReport:
    """按 (cluster_id, subtype) 原地覆盖最新巡检结果（对齐 AffinityCheckReport），不存在时新建。"""
    now = timezone.now()
    last_record = (
        MysqlConfigConsistencyReport.objects.filter(
            cluster_id=cluster.id,
            subtype=subtype,
        )
        .order_by("-update_at", "-id")
        .first()
    )
    failed_days = calculate_failed_days(last_record, evaluation.state, now)
    is_normal = evaluation.state == ReportStateType.NORMAL.value

    if last_record is not None:
        return _apply_report_fields(
            last_record,
            cluster,
            evaluation,
            is_normal=is_normal,
            failed_days=failed_days,
            creator=creator,
            now=now,
        )

    try:
        return MysqlConfigConsistencyReport.objects.create(
            bk_biz_id=cluster.bk_biz_id,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_id=cluster.id,
            cluster=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            subtype=subtype,
            state=evaluation.state,
            status=is_normal,
            failed_days=failed_days,
            diff_count=evaluation.diff_count,
            high_impact_count=evaluation.high_impact_count,
            diff_variables=evaluation.diff_variables,
            diff_detail=evaluation.diff_detail,
            msg=evaluation.msg,
            creator=creator,
            updater=creator,
            create_at=now,
            update_at=now,
        )
    except IntegrityError:
        existing = MysqlConfigConsistencyReport.objects.get(cluster_id=cluster.id, subtype=subtype)
        failed_days = calculate_failed_days(existing, evaluation.state, now)
        return _apply_report_fields(
            existing,
            cluster,
            evaluation,
            is_normal=is_normal,
            failed_days=failed_days,
            creator=creator,
            now=now,
        )


def delete_old_consistency_reports(days: int = 90) -> int:
    """清理超过指定天数未更新的历史配置一致性巡检报告。"""
    cutoff = timezone.now() - timedelta(days=days)
    deleted_count, unused_details = MysqlConfigConsistencyReport.objects.filter(create_at__lt=cutoff).delete()
    logger.info(_("配置一致性巡检: 清理 {} 条超过 {} 天的历史记录").format(deleted_count, days))
    return deleted_count


def delete_cluster_consistency_reports(cluster_ids: Sequence[int]) -> int:
    """按 cluster_id 批量删除配置一致性巡检记录（用于已下线/已销毁集群）。"""
    ids = list(dict.fromkeys(cid for cid in (cluster_ids or []) if cid is not None))
    if not ids:
        return 0
    total_deleted = 0
    batch_size = 500
    for start in range(0, len(ids), batch_size):
        batch = ids[start : start + batch_size]
        deleted_count, unused_details = MysqlConfigConsistencyReport.objects.filter(cluster_id__in=batch).delete()
        total_deleted += deleted_count
    if total_deleted:
        logger.info(_("配置一致性巡检: 清理非在线/已销毁集群的 {} 条巡检记录（涉及 {} 个集群）").format(total_deleted, len(ids)))
    return total_deleted


def delete_inactive_cluster_reports() -> int:
    """清理巡检表中已下线（phase != online）或已销毁集群的历史巡检记录。"""
    report_cluster_ids = set(MysqlConfigConsistencyReport.objects.values_list("cluster_id", flat=True).distinct())
    if not report_cluster_ids:
        return 0

    active_cluster_ids = set(
        Cluster.objects.filter(
            id__in=report_cluster_ids,
            cluster_type__in=SUPPORTED_CLUSTER_TYPES,
            phase=ClusterPhase.ONLINE.value,
        ).values_list("id", flat=True)
    )
    inactive_ids = sorted(report_cluster_ids - active_cluster_ids)
    return delete_cluster_consistency_reports(inactive_ids)


def _extract_tendbha_relevant_addresses(runtime_data: Dict[str, Any]) -> Set[str]:
    addrs: Set[str] = set()
    master = runtime_data.get("master")
    if isinstance(master, dict) and master.get("address"):
        addrs.add(master["address"])
    for slave in runtime_data.get("slaves") or []:
        if isinstance(slave, dict) and slave.get("is_stand_by") and slave.get("address"):
            addrs.add(slave["address"])
    return addrs


def _split_tendbcluster_errors(
    runtime_data: Dict[str, Any],
    all_errors: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str]]:
    spider_addrs = {
        node["address"]
        for node in (runtime_data.get("spiders") or [])
        if isinstance(node, dict) and node.get("address")
    }
    shard_addrs: Set[str] = set()
    for shard in (runtime_data.get("shards") or {}).values():
        if not isinstance(shard, dict):
            continue
        for role_key in ("master", "slave"):
            node = shard.get(role_key)
            if isinstance(node, dict) and node.get("address"):
                shard_addrs.add(node["address"])

    spider_errors = {addr: err for addr, err in all_errors.items() if addr in spider_addrs}
    shard_errors = {addr: err for addr, err in all_errors.items() if addr in shard_addrs}
    return spider_errors, shard_errors


def should_skip_cluster(cluster: Cluster, config: MysqlConfigConsistencyConfig) -> bool:
    """判断集群是否应跳过巡检（不支持类型、非 ONLINE、临时集群或配置忽略）。"""
    if cluster.cluster_type not in SUPPORTED_CLUSTER_TYPES:
        return True
    if cluster.phase != ClusterPhase.ONLINE.value:
        return True
    if cluster.bk_biz_id in (config.bizs_ignored or []):
        return True
    if cluster.id in (config.clusters_ignored or []):
        return True
    if TEMP_CLUSTER_DOMAIN_RE.match((cluster.immute_domain or "").lower()):
        return True
    return False


def _check_tendbha_cluster(
    cluster: Cluster,
    config: MysqlConfigConsistencyConfig,
    *,
    rpc_func=None,
) -> List[MysqlConfigConsistencyReport]:
    runtime_data = collect_cluster_runtime_variables(
        cluster,
        variable_names=config.storage_whitelist,
        fail_fast=False,
        extract_datadir=False,
        only_standby_slaves=True,
        rpc_func=rpc_func,
    )
    relevant_addrs = _extract_tendbha_relevant_addresses(runtime_data)
    all_errors = runtime_data.get("errors") or {}
    ha_errors = {addr: err for addr, err in all_errors.items() if addr in relevant_addrs}

    diff_res = build_tendbha_variable_diff(
        runtime_data,
        cluster_domain=cluster.immute_domain or "",
        should_skip=_make_whitelist_skip_fn(config.storage_whitelist),
        high_impact_keys=STORAGE_HIGH_IMPACT_VARS,
        bool_keys=BOOL_NORMALIZE_VARS,
        check_absent_keys=config.storage_whitelist,
        semantic_normalize=True,
    )
    evaluation = evaluate_tendbha_diff(diff_res, addr_errors=ha_errors)
    report = save_consistency_report(cluster, MysqlConfigConsistencySubType.MASTER_SLAVE.value, evaluation)
    return [report]


def _check_tendbcluster_cluster(
    cluster: Cluster,
    config: MysqlConfigConsistencyConfig,
    *,
    rpc_func=None,
) -> List[MysqlConfigConsistencyReport]:
    runtime_data = collect_cluster_runtime_variables(
        cluster,
        variable_names=config.tendbcluster_query_variables,
        fail_fast=False,
        extract_datadir=False,
        rpc_func=rpc_func,
    )
    all_errors = runtime_data.get("errors") or {}
    spider_errors, shard_errors = _split_tendbcluster_errors(runtime_data, all_errors)

    diff_res = build_tendbcluster_variable_diff(
        runtime_data,
        cluster_domain=cluster.immute_domain or "",
        spider_should_skip=_make_whitelist_skip_fn(config.spider_whitelist),
        shard_should_skip=_make_whitelist_skip_fn(config.storage_whitelist),
        spider_high_impact_keys=SPIDER_HIGH_IMPACT_VARS,
        shard_high_impact_keys=STORAGE_HIGH_IMPACT_VARS,
        bool_keys=BOOL_NORMALIZE_VARS,
        spider_check_absent_keys=config.spider_whitelist,
        shard_check_absent_keys=config.storage_whitelist,
        include_remote_master_group=True,
        prefer_runtime_spider_version=True,
        semantic_normalize=True,
    )

    spider_eval = evaluate_tendbcluster_spider_diff(
        diff_res,
        spider_errors=spider_errors,
        check_version=config.check_spider_version,
    )
    shard_eval = evaluate_tendbcluster_shard_diff(
        diff_res,
        shard_errors=shard_errors,
    )

    spider_report = save_consistency_report(cluster, MysqlConfigConsistencySubType.SPIDER_CONFIG.value, spider_eval)
    shard_report = save_consistency_report(cluster, MysqlConfigConsistencySubType.STORAGE_SHARD.value, shard_eval)
    return [spider_report, shard_report]


def check_single_cluster_config_consistency(
    cluster_id: int,
    config: Optional[MysqlConfigConsistencyConfig] = None,
    *,
    rpc_func=None,
) -> List[MysqlConfigConsistencyReport]:
    """执行单个 MySQL / TenDBCluster 集群的关键配置一致性巡检并落库。"""
    cfg = config or MysqlConfigConsistencyConfig.from_settings()
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        delete_cluster_consistency_reports([cluster_id])
        logger.warning(_("配置一致性巡检: 集群 id={} 不存在，已清理旧巡检记录并跳过").format(cluster_id))
        return []

    if cluster.phase != ClusterPhase.ONLINE.value:
        delete_cluster_consistency_reports([cluster.id])
        logger.info(
            _("配置一致性巡检: 集群 id={} domain={} 非在线状态(phase={})，已清理旧巡检记录").format(
                cluster.id, cluster.immute_domain, cluster.phase
            )
        )
        return []

    if should_skip_cluster(cluster, cfg):
        logger.info(_("配置一致性巡检: 跳过集群 id={} domain={}").format(cluster.id, cluster.immute_domain))
        return []

    if cluster.cluster_type == ClusterType.TenDBHA.value:
        return _check_tendbha_cluster(cluster, cfg, rpc_func=rpc_func)
    return _check_tendbcluster_cluster(cluster, cfg, rpc_func=rpc_func)
