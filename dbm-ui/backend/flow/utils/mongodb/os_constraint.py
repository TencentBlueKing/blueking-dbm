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
from typing import Callable, Iterable, List, Optional, Tuple

from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from backend.flow.utils.mongodb.version_utils import extract_mongodb_version_tuple

logger = logging.getLogger("flow")

# MongoDB >= 8.0 的官方包要求 glibc >= 2.28，只在 tlinux4（RHEL 9）上部署。
# 资源池中 tlinux4 的 os_name 固定为 tlinux-4、tlinux-4.4。
# 7.0 及以下也能在装了 compat-openssl10 的 tlinux4 上运行，但默认排除这些机器，留给 8.0。
MONGODB_TLINUX4_OS_NAMES = ("tlinux-4", "tlinux-4.4")
MONGODB_LEGACY_MAX_MAJOR = 7


def mongodb_os_names_for_version(version: str) -> Optional[Tuple[str, ...]]:
    """Map a MongoDB version to its mandatory resource-pool OS names."""
    if not version:
        return None
    major, minor, _ = extract_mongodb_version_tuple(version)
    if (major, minor) >= (8, 0):
        return MONGODB_TLINUX4_OS_NAMES
    return None


def _explicit_versions(*sources: Optional[dict]) -> List[str]:
    versions = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key in ("db_version", "major_version"):
            value = source.get(key)
            if value:
                versions.append(value)
    return versions


def _cluster_ids(current: Optional[dict]) -> List[int]:
    if not isinstance(current, dict):
        return []
    ids = []
    if current.get("cluster_id"):
        ids.append(current["cluster_id"])
    for cluster_id in current.get("cluster_ids") or []:
        ids.append(cluster_id)
    return ids


def _cluster_version_items(cluster_ids: Iterable[int], loader: Optional[Callable[[Iterable[int]], List[str]]]):
    """Yield (cluster_id, version). A custom loader does not know cluster ids."""
    if loader is not None:
        for version in loader(cluster_ids):
            yield None, version
        return
    from backend.db_meta.models import Cluster

    for cluster in Cluster.objects.filter(id__in=list(cluster_ids)).only("id", "major_version"):
        if cluster.major_version:
            yield cluster.id, cluster.major_version


def legacy_mongodb_allows_tlinux4() -> bool:
    """SystemSettings switch. Missing or false keeps tlinux4 for MongoDB 8.0."""
    from backend.configuration.constants import SystemSettingsEnum
    from backend.configuration.models import SystemSettings

    return bool(SystemSettings.get_setting_value(SystemSettingsEnum.MONGODB_LEGACY_ALLOW_TLINUX4.value, default=False))


def _legacy_os_filter(allow_legacy_tlinux4: bool) -> Optional[Tuple[List[str], bool]]:
    """OS filter for MongoDB <= 7. None when those versions may use tlinux4."""
    if allow_legacy_tlinux4:
        return None
    return list(MONGODB_TLINUX4_OS_NAMES), True


def mongodb_os_filter_for_version(
    version: str, allow_legacy_tlinux4: bool = False
) -> Optional[Tuple[List[str], bool]]:
    """Return (os_names, exclude_os_name). exclude=True means os_names is a blacklist."""
    if not version:
        return None
    major, minor, _ = extract_mongodb_version_tuple(version)
    if (major, minor) >= (8, 0):
        return list(MONGODB_TLINUX4_OS_NAMES), False
    if major <= MONGODB_LEGACY_MAX_MAJOR:
        return _legacy_os_filter(allow_legacy_tlinux4)
    return None


def _os_filter_for_source(
    version: str, allow_legacy_tlinux4: bool, *, from_cluster: bool, cluster_id: Optional[int] = None
) -> Optional[Tuple[List[str], bool]]:
    """Explicit ticket versions raise ValidationError. Cluster metadata falls back to <=7."""
    try:
        return mongodb_os_filter_for_version(version, allow_legacy_tlinux4=allow_legacy_tlinux4)
    except ValueError:
        if not from_cluster:
            raise ValidationError(_("MongoDB 版本号无法解析: {}").format(version))
        logger.warning("invalid mongodb cluster major_version %r on cluster %s, treat as <=7", version, cluster_id)
        return _legacy_os_filter(allow_legacy_tlinux4)


def mongodb_resource_os_names(
    parent: Optional[dict],
    current: Optional[dict],
    cluster_version_loader: Optional[Callable[[Iterable[int]], List[str]]] = None,
    allow_legacy_tlinux4: bool = False,
) -> Optional[List[str]]:
    """
    OS names for this MongoDB resource apply.

    Explicit db_version / major_version on the current info wins; parent is only a fallback.
    Otherwise fall back to cluster.major_version of cluster_id / cluster_ids.
    """
    os_filter = mongodb_resource_os_filter(
        parent, current, cluster_version_loader=cluster_version_loader, allow_legacy_tlinux4=allow_legacy_tlinux4
    )
    if not os_filter or os_filter[1]:
        return None
    return os_filter[0]


def mongodb_resource_os_filter(
    parent: Optional[dict],
    current: Optional[dict],
    cluster_version_loader: Optional[Callable[[Iterable[int]], List[str]]] = None,
    allow_legacy_tlinux4: bool = False,
) -> Optional[Tuple[List[str], bool]]:
    """Same version selection as mongodb_resource_os_names, including the <=7 blacklist."""
    explicit = _explicit_versions(current)
    if not explicit:
        explicit = _explicit_versions(parent)
    if explicit:
        for version in explicit:
            os_filter = _os_filter_for_source(version, allow_legacy_tlinux4, from_cluster=False)
            if os_filter:
                return os_filter
        return None

    cluster_ids = _cluster_ids(current)
    if not cluster_ids:
        return None
    for cluster_id, version in _cluster_version_items(cluster_ids, cluster_version_loader):
        os_filter = _os_filter_for_source(version, allow_legacy_tlinux4, from_cluster=True, cluster_id=cluster_id)
        if os_filter:
            return os_filter
    return None


def apply_os_names_to_resource_spec(
    resource_spec: Optional[dict], os_names: List[str], exclude_os_name: bool = False
) -> None:
    """Force os filter onto every pooled role. Hosts already chosen are left alone."""
    if not isinstance(resource_spec, dict):
        return
    for role_spec in resource_spec.values():
        if not isinstance(role_spec, dict) or role_spec.get("hosts") or role_spec.get("os_names"):
            continue
        role_spec["os_names"] = list(os_names)
        if exclude_os_name:
            role_spec["exclude_os_name"] = True


def apply_mongodb_os_constraint(
    ticket_data: Optional[dict],
    cluster_version_loader: Optional[Callable[[Iterable[int]], List[str]]] = None,
    allow_legacy_tlinux4: Optional[bool] = None,
) -> None:
    """Write os_names into every resource_spec on a MongoDB resource-apply payload.

    Batch tickets keep specs under infos[]. Deploy tickets such as shard apply keep
    resource_spec on the payload itself. Subclasses replace or reshape specs in format(),
    so this runs after format().
    """
    if not isinstance(ticket_data, dict):
        return
    if allow_legacy_tlinux4 is None:
        allow_legacy_tlinux4 = legacy_mongodb_allows_tlinux4()
    for info in ticket_data.get("infos") or []:
        constrain_mongodb_resource_os(
            ticket_data,
            info,
            cluster_version_loader=cluster_version_loader,
            allow_legacy_tlinux4=allow_legacy_tlinux4,
        )
    if ticket_data.get("resource_spec"):
        constrain_mongodb_resource_os(
            None, ticket_data, cluster_version_loader=cluster_version_loader, allow_legacy_tlinux4=allow_legacy_tlinux4
        )


def constrain_mongodb_resource_os(
    parent: Optional[dict],
    current: Optional[dict],
    cluster_version_loader: Optional[Callable[[Iterable[int]], List[str]]] = None,
    allow_legacy_tlinux4: bool = False,
) -> bool:
    """
    Write the version's os_names into resource_spec.
    Versions >= 8.0 use tlinux-4 and tlinux-4.4.
    Older versions exclude those names unless MONGODB_LEGACY_ALLOW_TLINUX4 is on.
    Returns True when the filter was applied.
    """
    if not isinstance(current, dict):
        return False
    os_filter = mongodb_resource_os_filter(
        parent, current, cluster_version_loader=cluster_version_loader, allow_legacy_tlinux4=allow_legacy_tlinux4
    )
    if not os_filter:
        return False
    os_names, exclude_os_name = os_filter
    apply_os_names_to_resource_spec(current.get("resource_spec"), os_names, exclude_os_name=exclude_os_name)
    return True
