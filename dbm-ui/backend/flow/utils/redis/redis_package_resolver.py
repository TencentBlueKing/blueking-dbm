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
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_package.constants import INIT_DB_PKG_SETTINGS
from backend.db_package.exceptions import PackageNotExistException
from backend.db_package.models import Package
from backend.db_package.models.db_version import DBVersion
from backend.db_services.ipchooser.constants import BkOsType
from backend.db_services.redis.util import (
    is_predixy_proxy_type,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import MediumEnum
from backend.flow.utils.redis.redis_util import get_redis_engine_family, version_parse

REDIS_STORAGE_PKG_TYPES = (MediumEnum.Redis.value, MediumEnum.TendisPlus.value, MediumEnum.TendisSsd.value)
REDIS_PROXY_PKG_TYPES = (MediumEnum.Predixy.value, MediumEnum.Twemproxy.value)
REDIS_UPGRADE_PKG_TYPES = REDIS_STORAGE_PKG_TYPES + REDIS_PROXY_PKG_TYPES

_PKG_SUFFIXES = (".tar.gz", ".tgz")
_DEFAULT_VERSION_NUM = 3


def strip_pkg_suffix(name: str) -> str:
    for suffix in _PKG_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


class RedisUpgradeTargetError(ValueError):
    pass


@dataclass(frozen=True)
class RedisUpgradeTarget:
    """升级目标: db_version_id 定位版本管理V2版本, version_name 仅用于展示"""

    db_version_id: int
    version_name: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict]) -> Optional["RedisUpgradeTarget"]:
        if not data:
            return None
        return cls(db_version_id=int(data["db_version_id"]), version_name=data.get("version_name", ""))

    @classmethod
    def from_db_version(cls, db_version: DBVersion) -> "RedisUpgradeTarget":
        return cls(db_version_id=db_version.id, version_name=db_version.name)

    @classmethod
    def from_package(cls, pkg: Package) -> "RedisUpgradeTarget":
        if not pkg.db_version_id:
            raise RedisUpgradeTargetError(_("介质包 {} 未关联版本管理V2版本").format(pkg.name))
        return cls.from_db_version(pkg.db_version)


# ---------------------------------------------------------------------------
# DBVersion 与运行态版本字符串的比较
# ---------------------------------------------------------------------------


def storage_pkg_type(cluster_type: str) -> Optional[str]:
    if is_redis_instance_type(cluster_type):
        return MediumEnum.Redis.value
    if is_tendisplus_instance_type(cluster_type):
        return MediumEnum.TendisPlus.value
    if is_tendisssd_instance_type(cluster_type):
        return MediumEnum.TendisSsd.value
    return None


def proxy_pkg_type(cluster_type: str) -> Optional[str]:
    if is_predixy_proxy_type(cluster_type):
        return MediumEnum.Predixy.value
    if is_twemproxy_proxy_type(cluster_type):
        return MediumEnum.Twemproxy.value
    return None


def db_version_pkg_type(db_version: DBVersion) -> str:
    snapshot = db_version.distribution_snapshot or {}
    if snapshot.get("pkg_type"):
        return snapshot["pkg_type"]
    series = db_version.version_series
    return series.distribution.pkg_type if series and series.distribution else ""


def version_num_of(pkg_type: str) -> int:
    """版本管理V2里该介质类型登记的版本号段数(3 或 6), 决定与运行态比较的精度"""
    settings = SystemSettings.get_setting_value(SystemSettingsEnum.DB_PACKAGE_SETTINGS, default=INIT_DB_PKG_SETTINGS)
    for item in settings.get(DBType.Redis.value, []):
        if str(item.get("value")) == pkg_type:
            return int(item.get("version_num") or _DEFAULT_VERSION_NUM)
    return _DEFAULT_VERSION_NUM


def db_version_engine_family(db_version: DBVersion) -> str:
    """引擎族取自版本系列名: Valkey-* 为 valkey, 其余为 redis"""
    series = db_version.version_series
    series_name = (series.name if series else "") or ""
    return "valkey" if series_name.strip().lower().startswith("valkey") else "redis"


def _db_version_key(db_version: DBVersion, version_num: int) -> Tuple[int, ...]:
    if version_num >= 6:
        return db_version.base_version_n, db_version.sub_version_n
    return (db_version.base_version_n,)


def _running_key(running_version: str, version_num: int) -> Optional[Tuple[int, ...]]:
    base, sub, err = version_parse(running_version or "")
    if err or not base:
        return None
    if version_num >= 6:
        return base, sub
    return (base,)


def compare_db_version(db_version: DBVersion, running_version: str) -> Optional[int]:
    """DBVersion 对比运行态版本: 1 高于 / 0 相等 / -1 低于; 运行态解析不了返回 None"""
    version_num = version_num_of(db_version_pkg_type(db_version))
    running = _running_key(running_version, version_num)
    if running is None:
        return None
    target = _db_version_key(db_version, version_num)
    return (target > running) - (target < running)


def is_cross_engine(db_version: DBVersion, running_version: str) -> bool:
    return db_version_engine_family(db_version) != get_redis_engine_family(running_version)


def validate_storage_upgrade(db_version: DBVersion, cluster_type: str, domain: str, ip_versions: Dict[str, str]):
    """存储层目标版本校验: 介质类型匹配集群架构, 每个 IP 同引擎且不降级"""
    expected = storage_pkg_type(cluster_type)
    if db_version_pkg_type(db_version) != expected:
        raise RedisUpgradeTargetError(_("Redis集群 {} 目标版本 {} 不是 {} 介质版本").format(domain, db_version.name, expected))
    for ip, cur_ver in ip_versions.items():
        if is_cross_engine(db_version, cur_ver):
            raise RedisUpgradeTargetError(
                _("集群 {} IP {} 当前版本 {} 与目标版本 {} 引擎不同(Redis/Valkey), 不支持跨引擎版本升级, 请使用 DTS 数据迁移").format(
                    domain, ip, cur_ver, db_version.name
                )
            )
        if compare_db_version(db_version, cur_ver) == -1:
            raise RedisUpgradeTargetError(
                _("集群 {} storage IP {} 当前版本 {} > 目标版本: {},不支持降级").format(domain, ip, cur_ver, db_version.name)
            )


def validate_proxy_upgrade(db_version: DBVersion, cluster_type: str, domain: str, ip_versions: Dict[str, str]):
    """接入层目标版本校验: 介质类型匹配集群架构, 所有 IP 都已是目标版本时无需执行"""
    expected = proxy_pkg_type(cluster_type)
    if db_version_pkg_type(db_version) != expected:
        raise RedisUpgradeTargetError(_("Redis集群 {} 目标版本 {} 不是 {} 介质版本").format(domain, db_version.name, expected))
    if ip_versions and all(compare_db_version(db_version, cur) == 0 for cur in ip_versions.values()):
        raise RedisUpgradeTargetError(_("集群 {} 所有proxy当前版本等于目标版本: {}, 无需执行").format(domain, db_version.name))


# ---------------------------------------------------------------------------
# 目标解析与取包
# ---------------------------------------------------------------------------


def _linux_packages(pkg_types: Iterable[str]) -> QuerySet:
    return Package.objects.filter(
        db_type=DBType.Redis.value, pkg_type__in=list(pkg_types), db_version__isnull=False
    ).filter(Q(permit_os_type__in=["", BkOsType.LINUX.value]) | Q(permit_os_type__isnull=True))


def upgrade_db_versions(pkg_types: Iterable[str]) -> QuerySet:
    """节点介质类型下、至少有一个 Linux 介质的 DBVersion, 标注 has_enabled_package"""
    pkg_types = list(pkg_types)
    packages = _linux_packages(pkg_types).filter(db_version_id=OuterRef("pk"))
    return (
        DBVersion.objects.filter(
            version_series__distribution__db_type=DBType.Redis.value,
            version_series__distribution__pkg_type__in=pkg_types,
        )
        .annotate(has_package=Exists(packages), has_enabled_package=Exists(packages.filter(enable=True)))
        .filter(has_package=True)
        .select_related("version_series", "version_series__distribution")
    )


class RedisUpgradePackageResolver:
    """把升级目标(db_version_id / 版本字符串)解析成唯一的 DBVersion, 下发时再按版本取介质包"""

    def __init__(self, pkg_types: Iterable[str] = REDIS_UPGRADE_PKG_TYPES):
        self.pkg_types = list(pkg_types)

    def db_version(self, db_version_id) -> DBVersion:
        db_version_id = self._parse_db_version_id(db_version_id)
        db_version = upgrade_db_versions(self.pkg_types).filter(id=db_version_id).first()
        if not db_version:
            raise RedisUpgradeTargetError(
                _("db_version_id={} 下找不到 {} 介质包").format(db_version_id, "/".join(self.pkg_types))
            )
        return db_version

    def target_of(self, db_version_id) -> RedisUpgradeTarget:
        return RedisUpgradeTarget.from_db_version(self.db_version(db_version_id))

    def resolve_target(self, name: str) -> RedisUpgradeTarget:
        """先按 DBVersion.name 精确匹配, 再按引擎族 + 解析出的版本数字匹配 full_version, 结果必须唯一"""
        if not name:
            raise RedisUpgradeTargetError(_("目标版本为空"))
        versions = list(upgrade_db_versions(self.pkg_types))
        matched = [v for v in versions if v.name == name]
        if not matched:
            version = strip_pkg_suffix(name)
            family = get_redis_engine_family(version)
            matched = [
                v for v in versions if db_version_engine_family(v) == family and compare_db_version(v, version) == 0
            ]
        if not matched:
            raise RedisUpgradeTargetError(_("目标版本 {} 找不到对应的版本管理V2版本").format(name))
        preferred = [v for v in matched if v.enable and v.has_enabled_package] or matched
        if len(preferred) > 1:
            raise RedisUpgradeTargetError(
                _("目标版本 {} 匹配到多个版本管理V2版本 {}, 无法唯一确定").format(name, sorted(v.id for v in preferred))
            )
        return RedisUpgradeTarget.from_db_version(preferred[0])

    def package(self, target: RedisUpgradeTarget) -> Package:
        """取该版本下首选 Linux 介质; 不强制启用: 审批期间目标版本或介质可能被禁用"""
        candidates = list(_linux_packages(self.pkg_types).filter(db_version_id=target.db_version_id))
        if not candidates:
            raise PackageNotExistException(
                version=f"{target.version_name}(db_version_id={target.db_version_id})",
                pkg_type="/".join(self.pkg_types),
                db_type=DBType.Redis.value,
            )
        return max(candidates, key=lambda pkg: (pkg.enable, pkg.priority, pkg.update_at))

    @staticmethod
    def series_name(target: RedisUpgradeTarget) -> str:
        db_version = DBVersion.objects.select_related("version_series").filter(id=target.db_version_id).first()
        if not db_version or not db_version.version_series:
            return ""
        return db_version.version_series.name

    @staticmethod
    def _parse_db_version_id(raw) -> int:
        try:
            db_version_id = int(raw)
        except (TypeError, ValueError):
            db_version_id = 0
        if isinstance(raw, bool) or db_version_id <= 0:
            raise RedisUpgradeTargetError(_("db_version_id={} 不合法").format(raw))
        return db_version_id


def resolve_ticket_upgrade_targets(infos: List[Dict], require_enabled: bool = False) -> Dict[int, DBVersion]:
    """
    解析版本升级单据 infos[].target_versions[] = [{ip, db_version_id}], 返回 db_version_id -> DBVersion,
    并把 DBVersion.name 写回 target_versions[].version_name 供展示; require_enabled 只在提单时打开
    """
    db_versions: Dict[int, DBVersion] = {}
    for info in infos:
        is_proxy = info.get("node_type") == RedisVerUpdateNodeType.Proxy.value
        resolver = RedisUpgradePackageResolver(REDIS_PROXY_PKG_TYPES if is_proxy else REDIS_STORAGE_PKG_TYPES)
        for entry in info.get("target_versions") or []:
            if not isinstance(entry, dict) or "db_version_id" not in entry or "ip" not in entry:
                raise RedisUpgradeTargetError(_("目标版本 {} 格式不合法, 应为 {{ip, db_version_id}}").format(entry))
            db_version = resolver.db_version(entry["db_version_id"])
            if require_enabled and not db_version.enable:
                raise RedisUpgradeTargetError(_("目标版本 {} 已禁用, 不允许提单").format(db_version.name))
            entry["db_version_id"] = db_version.id
            entry["version_name"] = db_version.name
            db_versions[db_version.id] = db_version
    return db_versions
