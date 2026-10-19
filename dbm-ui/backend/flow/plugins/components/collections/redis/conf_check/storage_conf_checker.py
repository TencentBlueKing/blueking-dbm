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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from django.conf import settings
from django.utils.translation import gettext as _

from backend.components.dbconfig.constants import LevelName
from backend.db_meta.enums import ClusterType, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.db_report.enums import ReportStateType
from backend.db_services.redis.redis_modules.models import TbRedisModuleSupport
from backend.flow.utils.redis.redis_act_playload import query_cluster_dbconf_map
from backend.flow.utils.redis.redis_script_template import build_storage_conf_check_snippet

from .base import BaseConfChecker, CheckTarget, ConfCheckResult
from .registry import redis_conf_checker
from .storage_conf_parse import StorageHostData, compare_directives, parse_storage_host_block, resolve_expected_conf

logger = logging.getLogger("flow")

MAX_WORKERS = getattr(settings, "CONCURRENT_NUMBER", 10)
MAX_DRIFTS_IN_MSG = 20
CLUSTER_CTX_KEY = "cluster_ctx"

# meta instance_role -> redis INFO REPLICATION role
ROLE_NORMALIZE = {"redis_master": "master", "redis_slave": "slave"}

# replication there is driven by cluster state, not redis.conf
CLUSTER_ARCH_TYPES = frozenset(
    {ClusterType.TendisPredixyRedisCluster.value, ClusterType.TendisPredixyTendisplusCluster.value}
)
# {{cluster_enabled}} -> yes
CLUSTER_ENABLED_TYPES = frozenset(
    {
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisRedisCluster.value,
    }
)


@dataclass
class StorageClusterContext:
    cluster_type: str
    major_version: str
    dbconfig: Optional[Dict[str, str]] = None
    dbconfig_error: str = ""
    expected_modules: Set[str] = field(default_factory=set)
    unresolved_modules: List[str] = field(default_factory=list)


def _module_names(dbconfig: Dict[str, str]) -> List[str]:
    return [name.strip() for name in (dbconfig.get("loadmodule") or "").split(",") if name.strip()]


def _query_dbconfig(cluster: Cluster) -> StorageClusterContext:
    ctx = StorageClusterContext(cluster_type=cluster.cluster_type, major_version=cluster.major_version)
    try:
        ctx.dbconfig = query_cluster_dbconf_map(
            bk_biz_id=cluster.bk_biz_id,
            level_name=LevelName.CLUSTER,
            level_value=cluster.immute_domain,
            cluster_type=cluster.cluster_type,
            conf_file=cluster.major_version,
        )
    except Exception as e:  # pylint: disable=broad-except
        logger.error("storage_conf dbconfig query failed for cluster %s: %s", cluster.immute_domain, e)
        ctx.dbconfig_error = str(e)
    return ctx


def load_cluster_contexts(cluster_ids: Set[int]) -> Dict[int, StorageClusterContext]:
    """dbconfig (one DBConfigApi call per cluster) and expected module .so files for a batch."""
    clusters = list(Cluster.objects.filter(id__in=cluster_ids))
    if not clusters:
        return {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        contexts = dict(zip([c.id for c in clusters], executor.map(_query_dbconfig, clusters)))

    wanted = {
        (ctx.major_version, name) for ctx in contexts.values() if ctx.dbconfig for name in _module_names(ctx.dbconfig)
    }
    so_files: Dict[tuple, Set[str]] = {}
    if wanted:
        rows = TbRedisModuleSupport.objects.filter(
            major_version__in={version for version, _name in wanted},
            module_name__in={name for _version, name in wanted},
        ).values_list("major_version", "module_name", "so_file")
        for major_version, module_name, so_file in rows:
            so_files.setdefault((major_version, module_name), set()).add(so_file)
    for ctx in contexts.values():
        if not ctx.dbconfig:
            continue
        for name in _module_names(ctx.dbconfig):
            resolved = so_files.get((ctx.major_version, name))
            if resolved:
                ctx.expected_modules.update(resolved)
            else:
                ctx.unresolved_modules.append(name)
    return contexts


def _replication_address(value: str) -> str:
    """'1.1.1.1 30000' (slaveof/replicaof value) -> '1.1.1.1:30000'."""
    parts = value.split()
    return "{}:{}".format(parts[0], parts[1]) if len(parts) >= 2 else value


@redis_conf_checker
class StorageConfChecker(BaseConfChecker):
    """
    Per storage instance, compare db_meta / dbconfig / runtime memory / on-disk redis.conf:

    1. replication role and master (meta vs INFO REPLICATION vs slaveof/replicaof on disk),
    2. loadmodule .so files (dbconfig module names via TbRedisModuleSupport vs disk),
    3. every other dbconfig directive (after placeholder substitution and normalization).

    Disk and runtime state are collected on the host through redis-cmd.sh (no DRS, no
    password lookup); see ``build_storage_conf_check_snippet``.
    """

    name = "storage_conf"
    requires_host_script = True
    cluster_types = [
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisRedisInstance.value,
    ]

    def collect_targets(self, cluster) -> List[CheckTarget]:
        if "storageinstance_set" in getattr(cluster, "_prefetched_objects_cache", {}):
            storages = cluster.storageinstance_set.all()
        else:
            storages = cluster.storageinstance_set.select_related("machine").all()
        storages = [inst for inst in storages if inst.status == InstanceStatus.RUNNING]
        expected_masters = self._expected_masters(storages)
        return [
            CheckTarget(
                cluster_id=cluster.id,
                bk_cloud_id=cluster.bk_cloud_id,
                ip=inst.machine.ip,
                port=inst.port,
                extra={"meta_role": inst.instance_role, "expected_master": expected_masters.get(inst.id, "")},
            )
            for inst in storages
        ]

    @staticmethod
    def _expected_masters(storages) -> Dict[int, str]:
        masters: Dict[int, str] = {}
        not_prefetched = []
        for inst in storages:
            if "as_receiver" not in getattr(inst, "_prefetched_objects_cache", {}):
                not_prefetched.append(inst.id)
                continue
            for pair in inst.as_receiver.all():
                masters.setdefault(inst.id, "{}:{}".format(pair.ejector.machine.ip, pair.ejector.port))
        if not_prefetched:
            rows = StorageInstanceTuple.objects.filter(receiver_id__in=not_prefetched).values(
                "receiver_id", "ejector__machine__ip", "ejector__port"
            )
            for row in rows:
                masters.setdefault(
                    row["receiver_id"], "{}:{}".format(row["ejector__machine__ip"], row["ejector__port"])
                )
        return masters

    def host_script_snippet(self, targets_on_host: List[CheckTarget]) -> Optional[str]:
        return build_storage_conf_check_snippet([t.port for t in targets_on_host]) or None

    def prepare_evaluation(self, targets: List[CheckTarget]) -> None:
        contexts = load_cluster_contexts({t.cluster_id for t in targets})
        for target in targets:
            target.extra[CLUSTER_CTX_KEY] = contexts.get(target.cluster_id)

    def evaluate(
        self,
        target: CheckTarget,
        drs_result: Optional[str],
        host_block: Optional[Dict],
        checker_config: Optional[Dict] = None,
        drs_error: Optional[str] = None,
    ) -> List[ConfCheckResult]:
        data = parse_storage_host_block(host_block)
        ctx: Optional[StorageClusterContext] = target.extra.get(CLUSTER_CTX_KEY)

        if data.collection_error:
            findings = ["[collect] {}".format(_("主机采集失败({})").format(data.collection_error))]
        else:
            findings = (
                self._collect_findings(data)
                + self._role_findings(target, data, ctx)
                + self._module_findings(data, ctx)
                + self._conf_findings(target, data, ctx)
            )

        if findings:
            state = ReportStateType.ABNORMAL.value
            msg = _("存储实例 {} 配置异常: {}").format(target.address, "; ".join(findings))
        else:
            state = ReportStateType.NORMAL.value
            msg = _("存储实例 {} 配置一致: 角色/同步/module/dbconfig检查通过").format(target.address)
        return [ConfCheckResult(ip=target.ip, port=target.port, state=state, msg=msg)]

    @staticmethod
    def _collect_findings(data: StorageHostData) -> List[str]:
        findings = ["[collect] {}={}".format(section, err) for section, err in sorted(data.section_errors.items())]
        if len(data.conf_paths) > 1:
            findings.append("[collect] conf_paths_ambiguous={}".format(data.conf_paths))
        if data.disk is not None:
            findings.extend("[collect] {}".format(err) for err in data.disk.include_errors)
        return findings

    @staticmethod
    def _role_findings(target: CheckTarget, data: StorageHostData, ctx: Optional[StorageClusterContext]) -> List[str]:
        meta_role = target.extra.get("meta_role", "")
        expected_role = ROLE_NORMALIZE.get(meta_role, meta_role)
        expected_master = target.extra.get("expected_master", "")
        is_slave = expected_role == "slave"
        findings = []

        if is_slave and not expected_master:
            findings.append("[role] {}".format(_("meta中缺少主从关系(StorageInstanceTuple)")))

        if data.repl is not None:
            actual_role = data.repl.get("role", "")
            if actual_role != expected_role:
                findings.append("[role] meta={}, actual={}".format(meta_role, actual_role or "unknown"))
            elif is_slave and expected_master:
                actual_master = "{}:{}".format(data.repl.get("master_host", ""), data.repl.get("master_port", ""))
                if actual_master != expected_master:
                    findings.append(
                        "[role] expected_master={}, memory_master={}".format(expected_master, actual_master)
                    )
                link = data.repl.get("master_link_status", "")
                if link != "up":
                    findings.append("[role] master_link_status={}".format(link or "unknown"))
                bad_stores = [
                    "rocksdb{}_master={}(state={})".format(s.store_id, s.address, s.state or "unknown")
                    for s in data.store_masters
                    if s.address != expected_master or s.state != "online"
                ]
                if bad_stores:
                    findings.append("[role] {}".format(", ".join(bad_stores)))

        if data.disk is not None:
            disk_master = _replication_address(data.disk.replication_of) if data.disk.replication_of else ""
            if expected_role == "master" and disk_master:
                findings.append("[repl-disk] {}".format(_("master磁盘配置存在同步指令 slaveof {}").format(disk_master)))
            elif is_slave and expected_master and ctx is not None and ctx.cluster_type not in CLUSTER_ARCH_TYPES:
                if disk_master != expected_master:
                    findings.append(
                        "[repl-disk] expected_master={}, disk_master={}".format(
                            expected_master, disk_master or "<absent>"
                        )
                    )
        return findings

    @staticmethod
    def _module_findings(data: StorageHostData, ctx: Optional[StorageClusterContext]) -> List[str]:
        if ctx is None or ctx.dbconfig is None or data.disk is None:
            return []
        findings = []
        if ctx.unresolved_modules:
            findings.append("[module] unresolved_in_TbRedisModuleSupport={}".format(sorted(ctx.unresolved_modules)))
        disk_modules = set(data.disk.modules)
        missing = sorted(ctx.expected_modules - disk_modules)
        unexpected = sorted(disk_modules - ctx.expected_modules)
        if missing or unexpected:
            findings.append("[module] missing_on_disk={}, unexpected_on_disk={}".format(missing, unexpected))
        return findings

    @staticmethod
    def _conf_findings(target: CheckTarget, data: StorageHostData, ctx: Optional[StorageClusterContext]) -> List[str]:
        if ctx is None:
            return ["[conf] {}".format(_("集群上下文缺失, 无法比对dbconfig"))]
        if ctx.dbconfig is None:
            return ["[conf] {}".format(_("dbconfig查询失败({})").format(ctx.dbconfig_error or "unknown"))]
        if data.disk is None and data.mem is None:
            return []
        expected = resolve_expected_conf(
            ctx.dbconfig,
            ip=target.ip,
            port=target.port,
            cluster_enabled=ctx.cluster_type in CLUSTER_ENABLED_TYPES,
            check_databases=ctx.cluster_type == ClusterType.TendisRedisInstance.value,
        )
        drifts = compare_directives(expected, data.disk, data.mem)
        if not drifts:
            return []
        shown = ", ".join(d.render() for d in drifts[:MAX_DRIFTS_IN_MSG])
        if len(drifts) > MAX_DRIFTS_IN_MSG:
            shown += " ... and {} more".format(len(drifts) - MAX_DRIFTS_IN_MSG)
        return ["[conf] {}".format(shown)]
