# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MongoDB 介质版本选择规则见同目录 VERSION_SELECTION.md。
"""
import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("flow")

_MAJOR_MINOR_RE = re.compile(r"^\d+\.\d+$")
_FULL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")
_MONGODB_PREFIX = "mongodb-"


def get_mongodb_package_v2_release(pkg_type: str, series: str = "latest"):
    """
    Fetch Mongo medium via Package V2 release API (Distribution/VersionSeries/DBVersion).
    Raises PackageNotExistException when no enabled Linux release package is found.
    See VERSION_SELECTION.md for series / selection rules.
    """
    from backend.configuration.constants import DBType
    from backend.db_meta.enums.version_phase import PkgSeries
    from backend.db_package.exceptions import PackageNotExistException
    from backend.db_package.models import Package

    series = series or PkgSeries.LATEST.value
    pkg = Package.get_latest_package_v2_release(
        pkg_type=pkg_type,
        series=series,
        db_type=DBType.MongoDB.value,
    )
    if not pkg:
        raise PackageNotExistException(version=series, pkg_type=pkg_type, db_type=DBType.MongoDB)
    return pkg


def _strip_mongodb_prefix(version: str) -> str:
    version = version.strip()
    if version.lower().startswith(_MONGODB_PREFIX):
        return version[len(_MONGODB_PREFIX) :]
    return version


def is_mongodb_major_minor_only(version: str) -> bool:
    """Return True when version is major.minor only (e.g. mongodb-7.0 or 7.0)."""
    if not version:
        return False
    raw = _strip_mongodb_prefix(version)
    return bool(_MAJOR_MINOR_RE.match(raw))


def extract_mongodb_version_tuple(version: str) -> Tuple[int, int, Optional[int]]:
    """
    Parse version into (major, minor, patch).
    patch is None when input is major.minor only (e.g. mongodb-7.0).
    """
    if not version:
        raise ValueError("version is empty")
    raw = _strip_mongodb_prefix(version)
    if _MAJOR_MINOR_RE.match(raw):
        major, minor = raw.split(".", 1)
        return int(major), int(minor), None
    numeric = raw.split("-", 1)[0]
    parts = numeric.split(".")
    if len(parts) < 3:
        raise ValueError("invalid version: {}".format(version))
    return int(parts[0]), int(parts[1]), int(parts[2])


def normalize_mongodb_full_version(version: str) -> str:
    """Normalize to mongodb-<full_version> and validate format."""
    if not version:
        raise ValueError("version is empty")
    version = version.strip()
    # Cluster metadata may store "MongoDB-5.0.4"; strip prefix case-insensitively.
    if version.lower().startswith(_MONGODB_PREFIX):
        raw = version[len(_MONGODB_PREFIX) :]
    else:
        # Reject prefixed-but-not-mongodb values (e.g. percona-5.0.14), while
        # still allowing legal suffix forms like 5.0.14-rc1.
        _, has_sep, _ = version.partition("-")
        if has_sep and not _FULL_VERSION_RE.match(version):
            raise ValueError("invalid version prefix: {}".format(version))
        raw = version
    if _MAJOR_MINOR_RE.match(raw):
        raw = "{}.0".format(raw)
    if not _FULL_VERSION_RE.match(raw):
        raise ValueError("invalid full version: {}".format(version))
    return "mongodb-{}".format(raw)


def compare_mongodb_versions(left: str, right: str) -> int:
    """
    Compare two MongoDB versions by (major, minor, patch).
    Returns negative if left < right, zero if equal, positive if left > right.
    When exactly one side is major.minor-only, treat it as patch 0 for ordering
    (cluster-level M.m vs instance-level M.m.p). Rejects when both sides are major.minor-only.
    """
    left_tuple = extract_mongodb_version_tuple(left)
    right_tuple = extract_mongodb_version_tuple(right)
    if left_tuple[2] is None and right_tuple[2] is None:
        raise ValueError(
            "cannot compare major.minor-only versions without package context: left={} right={}".format(left, right)
        )
    left_patch = 0 if left_tuple[2] is None else left_tuple[2]
    right_patch = 0 if right_tuple[2] is None else right_tuple[2]
    left_key = (left_tuple[0], left_tuple[1], left_patch)
    right_key = (right_tuple[0], right_tuple[1], right_patch)
    if left_key < right_key:
        return -1
    if left_key > right_key:
        return 1
    return 0


def extract_mongodb_major_minor(version: str) -> str:
    """Return major.minor string (e.g. 6.0) from any MongoDB version input."""
    if not version:
        raise ValueError("version is empty")
    major, minor, _ = extract_mongodb_version_tuple(version)
    return "{}.{}".format(major, minor)


def normalize_mongodb_cluster_version(version: str, *, package=None) -> str:
    """
    Normalize cluster.major_version to mongodb-M.m.p.
    major.minor-only inputs require package (no synthetic M.m.0).
    """
    return normalize_mongodb_instance_version(version, package=package)


def normalize_mongodb_instance_version(version: str, *, package=None) -> str:
    """
    Normalize storage/proxy instance.version to mongodb-M.m.p.
    major.minor-only inputs require package.version (no synthetic M.m.0).
    """
    return resolve_mongodb_persist_version(version, package=package)


def resolve_mongodb_metadata_versions(version: str, *, package=None) -> Dict[str, str]:
    """
    Resolve version strings for cluster vs instance metadata persistence.
    Both cluster.major_version and instance.version are mongodb-M.m.p.
    """
    full_version = normalize_mongodb_instance_version(version, package=package)
    return {"cluster": full_version, "instance": full_version}


def _instance_version_tuple(version: str) -> Tuple[int, int, int]:
    major, minor, patch = extract_mongodb_version_tuple(version)
    if patch is None:
        normalized = normalize_mongodb_full_version(version)
        numeric = normalized.removeprefix("mongodb-").split("-", 1)[0]
        parts = numeric.split(".")
        return int(parts[0]), int(parts[1]), int(parts[2])
    return major, minor, patch


def _as_django_cluster(cluster):
    """Resolve flow-layer MongoDBCluster to db_meta Cluster when needed."""
    if hasattr(cluster, "storageinstance_set"):
        return cluster
    # Flow-layer MongoDBCluster uses cluster_id; plain id-only stand-ins fall back as-is.
    cluster_id = getattr(cluster, "cluster_id", None)
    if not cluster_id:
        return cluster
    from backend.db_meta.models import Cluster

    try:
        return Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        return cluster


def _fallback_cluster_major_version(cluster) -> Optional[str]:
    live = getattr(cluster, "major_version", None) or ""
    if not live:
        return None
    try:
        if is_mongodb_major_minor_only(live):
            return live
        return normalize_mongodb_instance_version(live)
    except ValueError:
        return live


def get_cluster_live_instance_version(cluster) -> Optional[str]:
    """
    Return the minimum patch version among cluster storage/proxy instances.
    Falls back to cluster.major_version when no instance carries a version.
    """
    cluster = _as_django_cluster(cluster)
    storage_set = getattr(cluster, "storageinstance_set", None)
    proxy_set = getattr(cluster, "proxyinstance_set", None)
    if storage_set is None and proxy_set is None:
        return _fallback_cluster_major_version(cluster)

    versions: List[str] = []
    if storage_set is not None:
        for inst in storage_set.all():
            ver = getattr(inst, "version", None)
            if not ver:
                continue
            try:
                _instance_version_tuple(ver)
            except ValueError:
                continue
            versions.append(ver)
    if proxy_set is not None:
        for inst in proxy_set.all():
            ver = getattr(inst, "version", None)
            if not ver:
                continue
            try:
                _instance_version_tuple(ver)
            except ValueError:
                continue
            versions.append(ver)
    if not versions:
        return _fallback_cluster_major_version(cluster)
    return min(versions, key=_instance_version_tuple)


def resolve_mongodb_flow_db_version(cluster) -> str:
    """
    Resolve MongoDB version for cutoff/scale install and media dispatch.
    Prefer live instance min patch; fall back to cluster.major_version with package lookup.
    """
    live = get_cluster_live_instance_version(cluster)
    candidate = live or getattr(cluster, "major_version", None) or ""
    if not candidate:
        raise ValueError("cluster {} has no version metadata".format(getattr(cluster, "id", cluster)))
    if not is_mongodb_major_minor_only(candidate):
        try:
            return normalize_mongodb_instance_version(candidate)
        except ValueError:
            return candidate
    package = lookup_mongodb_package(candidate)
    if package:
        return resolve_mongodb_persist_version(candidate, package=package)
    raise ValueError(
        "cluster {} cannot resolve full version from major.minor {}: no mongodb package found".format(
            getattr(cluster, "id", cluster), candidate
        )
    )


def resolve_replaced_instance_version(cluster, old_instance) -> str:
    """Version to persist on replacement target instance (storage or proxy)."""
    if getattr(old_instance, "version", None):
        try:
            return normalize_mongodb_instance_version(old_instance.version)
        except ValueError:
            pass
    return normalize_mongodb_instance_version(resolve_mongodb_flow_db_version(cluster))


def apply_replaced_instance_version(cluster, new_instance, old_instance) -> None:
    version = resolve_replaced_instance_version(cluster, old_instance)
    if new_instance.version != version:
        new_instance.version = version
        new_instance.save(update_fields=["version"])


def check_cluster_instance_mm_consistency(cluster) -> Optional[str]:
    """
    Return warning message when instance major.minor disagrees with cluster.major_version.
    None when consistent or not enough data.
    """
    cluster_mm = None
    try:
        if cluster.major_version:
            cluster_mm = extract_mongodb_major_minor(cluster.major_version)
    except ValueError:
        return "cluster major_version invalid: {}".format(cluster.major_version)

    instance_mms = set()
    for inst in list(cluster.storageinstance_set.all()) + list(cluster.proxyinstance_set.all()):
        if not inst.version:
            continue
        try:
            instance_mms.add(extract_mongodb_major_minor(inst.version))
        except ValueError:
            continue
    if not instance_mms or cluster_mm is None:
        return None
    if len(instance_mms) > 1 or cluster_mm not in instance_mms:
        return "cluster major.minor {} inconsistent with instance versions {}".format(cluster_mm, sorted(instance_mms))
    return None


def _package_version_sort_key(package) -> Tuple[int, int, int]:
    """Sort key from resolved full version; unparsable packages sort last."""
    try:
        return _instance_version_tuple(_resolve_package_full_version(package))
    except ValueError:
        return (0, 0, -1)


def _pick_highest_patch_mongodb_package(packages) -> Optional[object]:
    best = None
    best_key = None
    for package in packages:
        key = _package_version_sort_key(package)
        if best is None or key > best_key:
            best = package
            best_key = key
    return best


def _mongodb_mongodb_package_queryset():
    from backend.configuration.constants import DBType
    from backend.db_package.models import Package
    from backend.flow.consts import MediumEnum

    return Package.objects.filter(pkg_type=MediumEnum.MongoDB, db_type=DBType.MongoDB).select_related("db_version")


def _major_minor_version_filter(raw_version: str):
    from django.db.models import Q

    stripped = raw_version.strip()
    if stripped.lower().startswith(_MONGODB_PREFIX):
        stripped = stripped.split("-", 1)[1]
    major_minor = ".".join(stripped.split(".")[:2])
    return (
        Q(version__startswith="{}.".format(major_minor))
        | Q(version__istartswith="mongodb-{}.".format(major_minor))
        | Q(version__iexact=raw_version)
        | Q(version__iexact="mongodb-{}".format(major_minor))
        | Q(version__iexact=major_minor)
    )


def _lookup_mongodb_package_major_minor(raw_version: str) -> Optional[object]:
    """mongodb-x.y: among enable=True packages, pick highest patch (z)."""
    candidates = _mongodb_mongodb_package_queryset().filter(_major_minor_version_filter(raw_version), enable=True)
    return _pick_highest_patch_mongodb_package(candidates)


def _lookup_mongodb_package_exact(normalized: str) -> Optional[object]:
    """mongodb-x.y.z: exact full version match; enable is not considered."""
    from django.db.models import Q

    raw = normalized.removeprefix("mongodb-")
    major_minor = ".".join(raw.split(".", 2)[:2])
    candidates = _mongodb_mongodb_package_queryset().filter(
        Q(version=normalized)
        | Q(version=raw)
        | Q(version__startswith="{}.".format(major_minor))
        | Q(version__istartswith="mongodb-{}.".format(major_minor))
        | Q(version__iexact="mongodb-{}".format(major_minor))
    )
    for package in candidates:
        try:
            if _resolve_package_full_version(package) == normalized:
                return package
        except ValueError:
            continue
    return None


def lookup_mongodb_package(raw_version: str, package=None):
    """
    Find MongoDB main medium package.

    - mongodb-x.y (major.minor): enable=True only, highest patch z.
    - mongodb-x.y.z (full): exact match on full version, ignore enable.

    Full rules: VERSION_SELECTION.md
    """
    if package is not None:
        return package

    if not raw_version:
        return None
    if is_mongodb_major_minor_only(raw_version):
        return _lookup_mongodb_package_major_minor(raw_version)
    try:
        normalized = normalize_mongodb_full_version(raw_version)
    except ValueError:
        return None
    return _lookup_mongodb_package_exact(normalized)


def apply_mongodb_metadata_versions_to_cluster(cluster, raw_version: str, *, package=None, instance_ids=None) -> None:
    """
    Persist MongoDB versions: cluster.major_version and instance.version are both mongodb-M.m.p.
    When instance_ids is provided, only those storage/proxy instances are updated.
    """
    if not raw_version:
        return
    package = lookup_mongodb_package(raw_version, package=package)
    versions = resolve_mongodb_metadata_versions(raw_version, package=package)
    instance_version = versions["instance"]
    cluster_version = versions["cluster"]

    if instance_ids is None:
        cluster.storageinstance_set.update(version=instance_version)
        cluster.proxyinstance_set.update(version=instance_version)
    else:
        id_set = set(instance_ids)
        cluster.storageinstance_set.filter(id__in=id_set).update(version=instance_version)
        cluster.proxyinstance_set.filter(id__in=id_set).update(version=instance_version)

    if cluster.major_version != cluster_version:
        cluster.major_version = cluster_version
        cluster.save(update_fields=["major_version"])

    warn = check_cluster_instance_mm_consistency(cluster)
    if warn:
        logger.warning("cluster %s version consistency: %s", getattr(cluster, "immute_domain", cluster.id), warn)


def _get_package_db_version(package):
    db_version = getattr(package, "db_version", None)
    if db_version is not None:
        return db_version
    db_version_id = getattr(package, "db_version_id", None)
    if not db_version_id:
        return None
    from backend.db_meta.models.db_version import DBVersion

    return DBVersion.objects.filter(pk=db_version_id).first()


def _resolve_package_instance_version_from_db_version(package, major_minor: str) -> Optional[str]:
    """Read M.m.p from Package.db_version (base_version / name)."""
    db_version = _get_package_db_version(package)
    if db_version is None:
        return None
    for candidate in (getattr(db_version, "base_version", None), getattr(db_version, "name", None)):
        if not candidate:
            continue
        try:
            normalized = normalize_mongodb_full_version(candidate)
        except ValueError:
            continue
        if extract_mongodb_major_minor(normalized) == major_minor:
            return normalized
    return None


def _resolve_package_full_version(package) -> str:
    """
    Resolve full mongodb-M.m.p for instance metadata from a Package row.
    package.version may be major.minor only (e.g. mongodb-6.0); patch comes from db_version.
    """
    pkg_version = getattr(package, "version", None)
    if not pkg_version:
        raise ValueError("package has no version")
    if not is_mongodb_major_minor_only(pkg_version):
        return normalize_mongodb_full_version(pkg_version)

    major_minor = extract_mongodb_major_minor(pkg_version)
    from_db_version = _resolve_package_instance_version_from_db_version(package, major_minor)
    if from_db_version:
        return from_db_version
    raise ValueError(
        "major.minor-only package.version {} requires db_version with patch, package_id={}".format(
            pkg_version, getattr(package, "id", None)
        )
    )


def resolve_mongodb_persist_version(version: str, package=None) -> str:
    """
    Resolve version string for cluster/instance metadata persistence.
    Full versions normalize directly; major.minor-only inputs resolve patch from package.db_version.
    """
    if not version:
        raise ValueError("version is empty")
    if is_mongodb_major_minor_only(version):
        if package is None:
            raise ValueError("major.minor-only version {} requires package context for persistence".format(version))
        return _resolve_package_full_version(package)
    return normalize_mongodb_full_version(version)
