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
from typing import Any, Dict, List, Optional

from django.core.exceptions import ObjectDoesNotExist

from backend.components.dbconfig.constants import LevelName
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum
from backend.flow.utils.mongodb.mongodb_conf_file import (
    FROM_M,
    FROM_MM,
    _conf_items_from_content,
    cluster_dbconf_level_value_search_order,
    cluster_has_legacy_dbconf_level_value,
    list_cluster_owned_conf_files,
    migrate_mongodb_cluster_level_value,
    migrate_mongodb_cluster_to_role,
    mongodb_conf_file_candidates,
    mongodb_role_conf_files,
    mongodb_versioned_conf_file_candidates,
    probe_mongodb_conf_files,
    query_mongodb_dbconf_content,
    query_mongodb_owned_content_at_level_values,
    resolve_cluster_dbconf_level_value,
    resolve_mongodb_versioned_conf_file,
)
from backend.flow.utils.mongodb.version_utils import (
    apply_mongodb_metadata_versions_to_cluster,
    extract_mongodb_major_minor,
    get_cluster_live_instance_version,
    is_mongodb_major_minor_only,
    lookup_mongodb_package,
    normalize_mongodb_full_version,
    resolve_mongodb_metadata_versions,
)

MIGRATE_STATUS_PENDING = "pending"
MIGRATE_STATUS_DONE = "done"
MIGRATE_FROM_MM = FROM_MM
MIGRATE_FROM_M = FROM_M

_MONGODB_CLUSTER_TYPES = {
    ClusterType.MongoReplicaSet.value,
    ClusterType.MongoShardedCluster.value,
}


class MongoClusterConfToolError(Exception):
    pass


def get_mongodb_cluster_by_domain(cluster_domain: str) -> Cluster:
    """Look up Cluster by immute_domain and validate MongoDB cluster type."""
    try:
        cluster = Cluster.objects.get(immute_domain=cluster_domain)
    except ObjectDoesNotExist as err:
        raise MongoClusterConfToolError("cluster not found for domain: {}".format(cluster_domain)) from err

    if cluster.cluster_type not in _MONGODB_CLUSTER_TYPES:
        raise MongoClusterConfToolError(
            "cluster {} is not MongoDB (type={})".format(cluster_domain, cluster.cluster_type)
        )
    return cluster


def iter_mongodb_clusters(*, bk_biz_id: Optional[int] = None) -> List[Cluster]:
    """Return MongoDB clusters ordered by id ascending."""
    qs = Cluster.objects.filter(cluster_type__in=_MONGODB_CLUSTER_TYPES)
    if bk_biz_id is not None:
        qs = qs.filter(bk_biz_id=bk_biz_id)
    return list(qs.order_by("id"))


def _is_versioned_mongodb_conf_file(conf_file: str) -> bool:
    """True for legacy/versioned conf_file names (mongodb-* / Mongodb-*)."""
    if not conf_file:
        return False
    return conf_file.startswith("mongodb-") or conf_file.startswith("Mongodb-")


def cluster_owns_versioned_dbconf(cluster: Cluster) -> bool:
    """True when CLUSTER still owns any versioned mongodb-* / Mongodb-* conf_file."""
    level_value = resolve_cluster_dbconf_level_value(cluster)
    owned = list_cluster_owned_conf_files(
        bk_biz_id=cluster.bk_biz_id,
        namespace=cluster.cluster_type,
        level_value=level_value,
        conf_type=ConfigTypeEnum.DBConf.value,
    )
    return any(_is_versioned_mongodb_conf_file(name) for name in owned)


def is_mongodb_cluster_conf_migrate_pending(cluster: Cluster) -> bool:
    """
    True when CLUSTER dbconf still needs --to-role migration:
    versioned conf_file ownership and/or legacy level_value keys.
    Does not use cluster.major_version.
    """
    if cluster_has_legacy_dbconf_level_value(cluster):
        return True
    try:
        return cluster_owns_versioned_dbconf(cluster)
    except Exception:
        return False


def is_mongodb_cluster_conf_migrate_done(cluster: Cluster) -> bool:
    """True when neither versioned CLUSTER conf nor legacy level_value remains."""
    if cluster_has_legacy_dbconf_level_value(cluster):
        return False
    try:
        return not cluster_owns_versioned_dbconf(cluster)
    except Exception:
        return False


def _domain_list_entry(cluster: Cluster) -> Dict[str, Any]:
    return {
        "id": cluster.id,
        "immute_domain": cluster.immute_domain,
        "name": cluster.name,
        "major_version": cluster.major_version or "",
        "bk_biz_id": cluster.bk_biz_id,
        "cluster_type": cluster.cluster_type,
    }


def list_mongodb_cluster_conf_migrate_domains(
    *,
    status: str,
    bk_biz_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    List MongoDB clusters by dbconf migrate status.
    pending: versioned CLUSTER conf and/or legacy level_value remain.
    done: neither remains.
    """
    if status == MIGRATE_STATUS_PENDING:
        predicate = is_mongodb_cluster_conf_migrate_pending
    elif status == MIGRATE_STATUS_DONE:
        predicate = is_mongodb_cluster_conf_migrate_done
    else:
        raise MongoClusterConfToolError("invalid status: {} (use pending|done)".format(status))

    return [
        _domain_list_entry(cluster) for cluster in iter_mongodb_clusters(bk_biz_id=bk_biz_id) if predicate(cluster)
    ]


def migrate_mongodb_cluster_conf_pending_batch(
    *,
    limit: int,
    from_kind: str,
    bk_biz_id: Optional[int] = None,
    dry_run: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    """Take the first ``limit`` pending domains (id asc) and run --to-role --from migrate for each."""
    if limit < 1:
        raise MongoClusterConfToolError("limit must be >= 1")
    from_kind = _normalize_from_kind(from_kind)

    pending = list_mongodb_cluster_conf_migrate_domains(status=MIGRATE_STATUS_PENDING, bk_biz_id=bk_biz_id)
    selected = pending[:limit]
    reports = []
    for entry in selected:
        domain = entry["immute_domain"]
        try:
            report = migrate_mongodb_cluster_conf_by_domain(
                cluster_domain=domain,
                dry_run=dry_run,
                to_role=True,
                from_kind=from_kind,
                force=force,
            )
            reports.append(report)
        except Exception as err:
            reports.append(
                {
                    "cluster": entry,
                    "to_role": True,
                    "from_kind": from_kind,
                    "dry_run": dry_run,
                    "force": force,
                    "migrated": False,
                    "skipped": True,
                    "reason": "batch migrate failed: {}".format(err),
                    "error": str(err),
                    "level_value": None,
                    "source_version": None,
                    "target_version": None,
                    "source_conf_file": None,
                    "target_conf_file": None,
                    "preview_content": None,
                    "preview_conf_items": None,
                    "deleted_conf_file": None,
                    "level_value_meta": None,
                    "version_meta": None,
                }
            )

    return {
        "dry_run": dry_run,
        "force": force,
        "from_kind": from_kind,
        "limit": limit,
        "bk_biz_id": bk_biz_id,
        "pending_total": len(pending),
        "selected_count": len(selected),
        "selected": selected,
        "reports": reports,
    }


def format_list_domains_report(entries: List[Dict[str, Any]], *, status: str) -> str:
    """Render pending/done domain list as human-readable text."""
    lines = ["{}: {} cluster(s)".format(status, len(entries))]
    for entry in entries:
        lines.append(
            "  {}  id={}  major_version={}  bk_biz_id={}  type={}".format(
                entry["immute_domain"],
                entry["id"],
                entry["major_version"] or "(empty)",
                entry["bk_biz_id"],
                entry["cluster_type"],
            )
        )
    return "\n".join(lines)


def format_batch_migrate_report(batch: Dict[str, Any]) -> str:
    """Render pending-batch migrate result as human-readable text."""
    lines = [
        "migrate --limit {}: dry_run={} force={} from={} bk_biz_id={}".format(
            batch["limit"],
            batch["dry_run"],
            batch["force"],
            batch.get("from_kind") or "(unset)",
            batch.get("bk_biz_id") if batch.get("bk_biz_id") is not None else "(all)",
        ),
        "  pending_total: {}".format(batch["pending_total"]),
        "  selected: {}".format(batch["selected_count"]),
        "",
    ]
    for report in batch.get("reports") or []:
        lines.append(format_migrate_report(report))
        lines.append("")
    return "\n".join(lines).rstrip()


def _cluster_meta(cluster: Cluster) -> Dict[str, Any]:
    return {
        "id": cluster.id,
        "name": cluster.name,
        "immute_domain": cluster.immute_domain,
        "bk_biz_id": cluster.bk_biz_id,
        "cluster_type": cluster.cluster_type,
        "major_version": cluster.major_version or "",
        "level_value": resolve_cluster_dbconf_level_value(cluster),
    }


def _validate_version(version: str, field_name: str) -> str:
    if not version:
        raise MongoClusterConfToolError("{} is required".format(field_name))
    try:
        extract_mongodb_major_minor(version)
    except ValueError as err:
        raise MongoClusterConfToolError("invalid {}: {}".format(field_name, version)) from err
    return version


def _normalize_from_kind(from_kind: Optional[str]) -> str:
    if not from_kind:
        raise MongoClusterConfToolError("--from is required with --to-role (mm|M)")
    # Accept common aliases; canonical values are mm and M.
    normalized = from_kind.strip()
    if normalized.lower() == "mm":
        return FROM_MM
    if normalized == "M" or normalized.lower() == "m":
        return FROM_M
    raise MongoClusterConfToolError("invalid --from={!r} (use mm|M)".format(from_kind))


def _effective_conf_source(probes: List[Dict[str, Any]]) -> Optional[str]:
    for probe in probes:
        if probe.get("found"):
            return probe["conf_file"]
    return None


def _cluster_owned_conf_source(probes: List[Dict[str, Any]]) -> Optional[str]:
    for probe in probes:
        if probe.get("owned"):
            return probe["conf_file"]
    return None


def _format_probe_content(content: dict) -> str:
    """Render conf values with source level, e.g. key_file=dba-rs@cluster."""
    parts = []
    for name, item in (content or {}).items():
        if isinstance(item, dict) and "conf_value" in item:
            value = item.get("conf_value")
            level = item.get("level_name") or ""
            if level:
                parts.append("{}={}@{}".format(name, value, level))
            else:
                parts.append("{}={}".format(name, value))
        else:
            parts.append("{}={}".format(name, item))
    return ", ".join(parts)


def inspect_mongodb_cluster_conf(cluster: Cluster, version: Optional[str] = None) -> Dict[str, Any]:
    """Return structured diagnostics for CLUSTER-level MongoDB dbconf."""
    version_used = _validate_version(version or cluster.major_version or "", "version")
    level_value = resolve_cluster_dbconf_level_value(cluster)
    level_info = {"module": str(DEFAULT_DB_MODULE_ID)}
    namespace = cluster.cluster_type
    candidates = mongodb_conf_file_candidates(version_used, namespace=namespace)

    probes = probe_mongodb_conf_files(
        bk_biz_id=str(cluster.bk_biz_id),
        level_name=LevelName.CLUSTER.value,
        level_value=level_value,
        namespace=namespace,
        version=version_used,
        conf_type=ConfigTypeEnum.DBConf.value,
        level_info=level_info,
        conf_files=candidates,
    )

    plat_probes = probe_mongodb_conf_files(
        bk_biz_id="0",
        level_name=LevelName.PLAT.value,
        level_value="0",
        namespace=namespace,
        version=version_used,
        conf_type=ConfigTypeEnum.DBConf.value,
        level_info=None,
        conf_files=candidates,
    )
    plat_found = any(probe.get("found") for probe in plat_probes)
    cluster_owned = _cluster_owned_conf_source(probes)
    cluster_readable = _effective_conf_source(probes)

    effective = None
    effective_error = None
    if cluster_readable:
        for probe in probes:
            if probe.get("found"):
                effective = probe.get("content")
                break
    elif plat_found:
        for probe in plat_probes:
            if probe.get("found"):
                effective = probe.get("content")
                break
    else:
        effective_error = "no readable CLUSTER or PLAT dbconf"

    plat_used = effective is not None and cluster_owned is None and plat_found
    if cluster_readable:
        effective_via = cluster_readable
    elif plat_used:
        effective_via = "plat"
    else:
        effective_via = None

    return {
        "cluster": _cluster_meta(cluster),
        "version_used": version_used,
        "conf_file_candidates": candidates,
        "probes": probes,
        "effective": effective,
        "effective_error": effective_error,
        "effective_via": effective_via,
        "effective_owned_via": cluster_owned,
        "plat_probes": plat_probes,
        "plat_used": plat_used,
    }


def migrate_mongodb_cluster_metadata_versions(cluster: Cluster, *, dry_run: bool = True) -> Dict[str, Any]:
    """
    Ensure cluster.major_version (and instance versions) are mongodb-x.y.z.
    Prefer min live instance full version; else resolve patch from package when major_version is M.m/legacy.
    """
    result = {
        "dry_run": dry_run,
        "migrated": False,
        "skipped": False,
        "reason": "",
        "source_major_version": cluster.major_version or "",
        "target_cluster_version": None,
        "target_instance_version": None,
        "storage_count": 0,
        "proxy_count": 0,
        "storage_updates": [],
        "proxy_updates": [],
    }
    raw = (cluster.major_version or "").strip()
    live = get_cluster_live_instance_version(cluster)

    def _resolve_full(candidate: str) -> Optional[str]:
        if not candidate:
            return None
        hint = candidate
        if hint.startswith("Mongodb-"):
            hint = "mongodb-{}.0".format(hint.split("-", 1)[1])
        if is_mongodb_major_minor_only(hint):
            package = lookup_mongodb_package(hint)
            if package is None:
                return None
            return resolve_mongodb_metadata_versions(hint, package=package)["cluster"]
        try:
            return normalize_mongodb_full_version(hint)
        except ValueError:
            return None

    full_version = None
    if live and not is_mongodb_major_minor_only(live):
        full_version = _resolve_full(live)
    if full_version is None:
        full_version = _resolve_full(raw)
    if not full_version:
        result["skipped"] = True
        result["reason"] = "cannot resolve mongodb-x.y.z from major_version={!r} / live={!r}".format(raw, live)
        return result

    result["target_instance_version"] = full_version
    result["target_cluster_version"] = full_version

    storages = list(cluster.storageinstance_set.all())
    proxies = list(cluster.proxyinstance_set.all())
    result["storage_count"] = len(storages)
    result["proxy_count"] = len(proxies)
    result["storage_updates"] = [{"id": inst.id, "from": inst.version or "", "to": full_version} for inst in storages]
    result["proxy_updates"] = [{"id": inst.id, "from": inst.version or "", "to": full_version} for inst in proxies]

    already = cluster.major_version == full_version and all(
        (inst.version or "") == full_version for inst in storages + proxies
    )
    if already:
        result["skipped"] = True
        result["reason"] = "already full version: {}".format(full_version)
        return result

    if dry_run:
        result["reason"] = "dry-run only; pass --apply to write cluster/instance versions as {}".format(full_version)
        return result

    apply_mongodb_metadata_versions_to_cluster(cluster, full_version)
    cluster.major_version = full_version
    result["migrated"] = True
    result["reason"] = "updated cluster.major_version and instances to {}".format(full_version)
    return result


def _owned_conf_files_across_levels(cluster: Cluster) -> set:
    """Union of owned conf_files at immute_domain and legacy level_value keys."""
    owned: set = set()
    for level_value in cluster_dbconf_level_value_search_order(cluster):
        owned |= list_cluster_owned_conf_files(
            bk_biz_id=cluster.bk_biz_id,
            namespace=cluster.cluster_type,
            level_value=level_value,
            conf_type=ConfigTypeEnum.DBConf.value,
        )
    return owned


def _role_overwrite_blocked(cluster: Cluster, *, force: bool) -> Optional[str]:
    """Return skip reason when role conf_files already exist alongside versioned source."""
    if force:
        return None
    owned = _owned_conf_files_across_levels(cluster)
    role_files = set(mongodb_role_conf_files(cluster.cluster_type))
    conflict = sorted(owned & role_files)
    versioned = sorted(name for name in owned if _is_versioned_mongodb_conf_file(name))
    if conflict and versioned:
        return "target already owns role conf_files {}; pass --force to overwrite".format(",".join(conflict))
    return None


def _cluster_has_versioned_dbconf_anywhere(cluster: Cluster) -> bool:
    return any(_is_versioned_mongodb_conf_file(name) for name in _owned_conf_files_across_levels(cluster))


def migrate_mongodb_cluster_conf_by_domain(
    cluster_domain: str,
    target_version: Optional[str] = None,
    source_version: Optional[str] = None,
    dry_run: bool = True,
    to_role: bool = False,
    from_kind: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Migrate CLUSTER dbconf.

    Always runs level_value migration first (legacy keys -> immute_domain, same conf_file name).
    With to_role: copy versioned conf (--from=mm -> mongodb-M.m, --from=M -> Mongodb-M)
    into role conf_files; fill cluster/instance metadata to mongodb-x.y.z only when conf migrate succeeds.
    Without to_role: diagnostic version-hop preview; apply still writes role files (auto source).
    """
    cluster = get_mongodb_cluster_by_domain(cluster_domain)
    level_value = resolve_cluster_dbconf_level_value(cluster)
    namespace = cluster.cluster_type
    level_info = {"module": str(DEFAULT_DB_MODULE_ID)}
    role_targets = mongodb_role_conf_files(namespace)
    level_search_order = cluster_dbconf_level_value_search_order(cluster)

    resolved_from = None
    if to_role:
        resolved_from = _normalize_from_kind(from_kind)
        version = _validate_version(target_version or cluster.major_version or "", "version")
        source_version = version
        target_version = version
        source_conf_file = resolve_mongodb_versioned_conf_file(version, resolved_from)
        target_conf_file = ",".join(role_targets)
    else:
        target_version = _validate_version(target_version or "", "target_version")
        source_version = _validate_version(source_version or cluster.major_version or "", "source_version")
        source_conf_file = "/".join(mongodb_versioned_conf_file_candidates(source_version))
        target_conf_file = ",".join(role_targets)

    result = {
        "cluster": _cluster_meta(cluster),
        "to_role": to_role,
        "from_kind": resolved_from,
        "source_version": source_version,
        "target_version": target_version,
        "source_conf_file": source_conf_file,
        "target_conf_file": target_conf_file,
        "level_value": level_value,
        "source_level_value": None,
        "dry_run": dry_run,
        "force": force,
        "migrated": False,
        "skipped": False,
        "reason": "",
        "preview_content": None,
        "preview_conf_items": None,
        "deleted_conf_file": None,
        "deleted_conf_files": None,
        "level_value_meta": None,
        "version_meta": None,
    }

    # 1) level_value: legacy name keys -> immute_domain (same conf_file only)
    result["level_value_meta"] = migrate_mongodb_cluster_level_value(
        cluster=cluster,
        dry_run=dry_run,
        force=force,
    )

    def _finish(*, conf_ok: bool) -> Dict[str, Any]:
        # version_meta only after conf migrate succeeds (or dry-run would succeed).
        if to_role and conf_ok:
            result["version_meta"] = migrate_mongodb_cluster_metadata_versions(cluster, dry_run=dry_run)
        result["cluster"] = _cluster_meta(cluster)
        return result

    # 2) Resolve versioned source from domain then legacy (dry-run mirrors apply after level relocate).
    try:
        if to_role:
            content, source_level_value = query_mongodb_owned_content_at_level_values(
                bk_biz_id=str(cluster.bk_biz_id),
                namespace=namespace,
                conf_file=source_conf_file,
                level_values=level_search_order,
                level_info=level_info,
            )
            result["source_level_value"] = source_level_value
        else:
            content = None
            last_err = None
            for candidate_lv in level_search_order:
                try:
                    content = query_mongodb_dbconf_content(
                        bk_biz_id=str(cluster.bk_biz_id),
                        level_name=LevelName.CLUSTER.value,
                        level_value=candidate_lv,
                        namespace=namespace,
                        version=source_version,
                        level_info=level_info,
                        plat_fallback=False,
                    )
                    result["source_level_value"] = candidate_lv
                    break
                except Exception as err:
                    last_err = err
                    continue
            if content is None:
                raise last_err or ValueError("source conf not found")
    except Exception as err:
        # --to-role with no versioned source left: level_value-only / already-role is conf OK.
        if to_role and not _cluster_has_versioned_dbconf_anywhere(cluster):
            result["skipped"] = True
            result["reason"] = "no versioned CLUSTER conf_file left; level_value step only"
            return _finish(conf_ok=True)
        result["skipped"] = True
        if to_role:
            result["reason"] = "source conf_file {} not found at CLUSTER level (tried {}): {}".format(
                source_conf_file, ",".join(level_search_order), err
            )
        else:
            result["reason"] = "source conf not found at CLUSTER level: {}".format(err)
        return _finish(conf_ok=False)

    conf_items = _conf_items_from_content(content, namespace)
    if not conf_items:
        result["skipped"] = True
        result["reason"] = "source conf has no migratable items"
        return _finish(conf_ok=False)

    result["preview_content"] = content
    result["preview_conf_items"] = conf_items

    blocked = _role_overwrite_blocked(cluster, force=force)
    if blocked:
        result["skipped"] = True
        result["reason"] = blocked
        return _finish(conf_ok=False)

    if dry_run:
        result["reason"] = "dry-run only; pass --apply to copy {} -> {}".format(source_conf_file, target_conf_file)
        return _finish(conf_ok=True)

    migration = migrate_mongodb_cluster_to_role(
        bk_biz_id=cluster.bk_biz_id,
        namespace=namespace,
        level_value=level_value,
        version=source_version,
        from_kind=resolved_from,
        force=force,
    )
    result["migrated"] = migration["migrated"]
    result["deleted_conf_file"] = migration.get("deleted_conf_file")
    result["deleted_conf_files"] = migration.get("deleted_conf_files")
    if migration.get("already_role"):
        result["skipped"] = True
        result["reason"] = migration.get("reason") or "already owns role conf_files only"
        return _finish(conf_ok=True)
    if not migration["migrated"]:
        result["skipped"] = True
        result["reason"] = migration.get("reason") or "migrate to role conf_files returned False"
        return _finish(conf_ok=False)
    return _finish(conf_ok=True)


def format_inspect_report(report: Dict[str, Any]) -> str:
    """Render inspect result as human-readable text."""
    cluster = report["cluster"]
    lines = [
        "Cluster: {} (id={}, bk_biz_id={})".format(cluster["immute_domain"], cluster["id"], cluster["bk_biz_id"]),
        "  type: {}".format(cluster["cluster_type"]),
        "  major_version: {}".format(cluster["major_version"] or "(empty)"),
        "  level_value: {}".format(cluster["level_value"]),
        "  version_used: {}".format(report["version_used"]),
        "  conf_file candidates: {}".format(", ".join(report["conf_file_candidates"])),
        "",
        "  CLUSTER probes:",
    ]
    for probe in report["probes"]:
        status = probe.get("status", "NOT_FOUND")
        if status == "NOT_FOUND":
            lines.append("    {}: NOT FOUND  {}".format(probe["conf_file"], probe.get("error", "")))
            continue
        summary = _format_probe_content(probe.get("content") or {})
        if status == "INHERITED":
            lines.append("    {}: INHERITED (merged from parent)  {}".format(probe["conf_file"], summary))
        elif status == "OWNED":
            lines.append("    {}: OWNED  {}".format(probe["conf_file"], summary))
        else:
            lines.append("    {}: {}  {}".format(probe["conf_file"], status, summary))

    lines.append("")
    if report.get("effective") is not None:
        via = report.get("effective_via") or "unknown"
        owned_via = report.get("effective_owned_via")
        summary = _format_probe_content(report["effective"])
        lines.append("  effective (get_conf path): {}  [via {}]".format(summary, via))
        if owned_via:
            lines.append("  cluster-owned conf_file: {}".format(owned_via))
        elif via:
            lines.append("  cluster-owned conf_file: (none, using merged/inherited or plat fallback)")
    else:
        lines.append("  effective (get_conf path): NOT FOUND  {}".format(report.get("effective_error", "")))

    for probe in report.get("plat_probes", []):
        if probe.get("found"):
            lines.append("")
            lines.append("  PLAT probe (reference):")
            lines.append(
                "    {}: {}  {}".format(
                    probe["conf_file"],
                    probe.get("status", "FOUND"),
                    _format_probe_content(probe.get("content") or {}),
                )
            )
            break

    lines.append("")
    lines.append("  plat fallback: {}".format("USED" if report.get("plat_used") else "NOT USED"))
    return "\n".join(lines)


def format_migrate_report(report: Dict[str, Any]) -> str:
    """Render migrate result as human-readable text."""
    cluster = report["cluster"]
    lines = [
        "Cluster: {} (id={})".format(cluster["immute_domain"], cluster["id"]),
        "  mode: {}".format(
            "to_role --from={}".format(report.get("from_kind")) if report.get("to_role") else "version_migrate"
        ),
        "  level_value: {}".format(report["level_value"]),
        "  source: {} -> {}".format(report["source_version"], report["source_conf_file"]),
        "  target: {} -> {}".format(report["target_version"], report["target_conf_file"]),
        "  dry_run: {}".format(report["dry_run"]),
    ]
    if report.get("source_level_value"):
        lines.append("  source_level_value: {}".format(report["source_level_value"]))
    if report.get("preview_content"):
        summary = ", ".join("{}={}".format(k, v) for k, v in report["preview_content"].items())
        lines.append("  preview_content: {}".format(summary))
    if report["migrated"]:
        lines.append("  result: MIGRATED")
        if report.get("deleted_conf_file"):
            lines.append("  deleted_source_conf_file: {}".format(report["deleted_conf_file"]))
    elif report["skipped"]:
        lines.append("  result: SKIPPED ({})".format(report["reason"]))
    elif report["dry_run"]:
        lines.append("  result: DRY-RUN OK ({})".format(report["reason"]))
    else:
        lines.append("  result: {}".format(report["reason"] or "unknown"))

    level_value_meta = report.get("level_value_meta")
    if level_value_meta:
        lines.append("")
        lines.append("  level_value_meta:")
        lines.append("    target_level_value: {}".format(level_value_meta.get("target_level_value")))
        lines.append(
            "    would_migrate/migrated: {}  skipped: {}".format(
                level_value_meta.get("migrated_count", 0),
                level_value_meta.get("skipped_count", 0),
            )
        )
        migrations = level_value_meta.get("migrations") or []
        if not migrations:
            lines.append("    (no legacy OWNED rows)")
        for entry in migrations:
            reason = " ({})".format(entry["reason"]) if entry.get("reason") else ""
            lines.append(
                "    {} {} -> {}: {}{}".format(
                    entry["conf_file"],
                    entry["source_level_value"],
                    entry["target_level_value"],
                    entry["status"],
                    reason,
                )
            )

    version_meta = report.get("version_meta")
    if version_meta:
        lines.append("")
        lines.append("  version_meta:")
        lines.append("    source_major_version: {}".format(version_meta.get("source_major_version") or "(empty)"))
        if version_meta.get("target_instance_version"):
            lines.append(
                "    target: cluster {} <- instances {}".format(
                    version_meta.get("target_cluster_version"),
                    version_meta.get("target_instance_version"),
                )
            )
        lines.append(
            "    storage/proxy: {}/{}".format(
                version_meta.get("storage_count", 0),
                version_meta.get("proxy_count", 0),
            )
        )
        if version_meta.get("migrated"):
            lines.append("    result: MIGRATED ({})".format(version_meta.get("reason") or ""))
        elif version_meta.get("skipped"):
            lines.append("    result: SKIPPED ({})".format(version_meta.get("reason") or ""))
        elif version_meta.get("dry_run"):
            lines.append("    result: DRY-RUN OK ({})".format(version_meta.get("reason") or ""))
        else:
            lines.append("    result: {}".format(version_meta.get("reason") or "unknown"))
    return "\n".join(lines)
