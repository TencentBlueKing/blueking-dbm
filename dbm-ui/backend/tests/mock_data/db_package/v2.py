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
from typing import Iterable, List

from backend.configuration.constants import DBType
from backend.db_meta.enums.version_phase import PkgSeries, VersionPhase
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.db_services.ipchooser.constants import BkOsType

_AUDIT = {"creator": "admin", "updater": "admin"}
_V2_FULL_VERSION = "1.0.0.0.0.0"

# GetFileList.mysql_install_package 通过 get_latest_package_v2_release 取备份包
MYSQL_V2_RELEASE_PKG_TYPES = (
    PackageType.DbBackup.value,
    PackageType.DbBackupTXSQL.value,
)


def ensure_v2_release_package(
    *,
    pkg_type: str,
    db_type: str = DBType.MySQL.value,
    series: str = PkgSeries.LATEST.value,
    full_version: str = _V2_FULL_VERSION,
    name: str = "",
    path: str = "",
) -> Package:
    """写入一条能被 Package.get_latest_package_v2_release 命中的介质包。"""
    dist, _ = Distribution.objects.get_or_create(
        db_type=db_type,
        pkg_type=pkg_type,
        name=f"test-{pkg_type}",
        defaults={"engine": "", **_AUDIT},
    )
    series_obj, _ = VersionSeries.objects.get_or_create(
        distribution=dist,
        name=series,
        defaults=_AUDIT,
    )
    db_version, _ = DBVersion.objects.get_or_create(
        full_version=full_version,
        distribution_id=dist.id,
        defaults={
            "name": f"test-{pkg_type}-{full_version}",
            "version_series": series_obj,
            "phase": VersionPhase.RELEASE.value,
            "enable": True,
            "recommend": True,
            **_AUDIT,
        },
    )
    package, _ = Package.objects.get_or_create(
        pkg_type=pkg_type,
        db_version=db_version,
        defaults={
            "name": name or f"{pkg_type}.tar.gz",
            "version": series,
            "db_type": db_type,
            "path": path or f"/tmp/{pkg_type}/",
            "size": 0,
            "md5": "",
            "enable": True,
            "permit_os_type": BkOsType.LINUX.value,
            **_AUDIT,
        },
    )
    return package


def seed_mysql_v2_release_packages(pkg_types: Iterable[str] = MYSQL_V2_RELEASE_PKG_TYPES) -> List[Package]:
    return [ensure_v2_release_package(pkg_type=pkg_type) for pkg_type in pkg_types]


# redis 介质查询已整体切换到 V2，flow 侧按 (pkg_type, version_series) 取包
REDIS_V2_RELEASE_PKG_SPECS = (
    # (pkg_type, series, pkg_name, full_version)
    (PackageType.DBActuator.value, PkgSeries.LATEST.value, "dbactuator_redis.tar.gz", "1.0.5.0.0.0"),
    (PackageType.DbMon.value, PkgSeries.LATEST.value, "bk-dbmon.tar.gz", "1.0.5.0.0.0"),
    (PackageType.RedisTools.value, PkgSeries.LATEST.value, "dbtools.tar.gz", "1.0.0.0.0.0"),
    (PackageType.RedisModules.value, PkgSeries.LATEST.value, "redis_modules.tar.gz", "1.0.0.0.0.0"),
    (PackageType.RedisDts.value, PkgSeries.LATEST.value, "redis_dts.tar.gz", "1.0.0.0.0.0"),
    (PackageType.Redis.value, "Redis-6", "redis-6.2.14.tar.gz", "6.2.14.0.0.0"),
    (PackageType.TendisPlus.value, "Tendisplus-2.7", "tendisplus-2.7.3-rocksdb-v8.5.3.tgz", "2.7.3.0.0.0"),
    (PackageType.TendisSsd.value, "TendisSSD-1.2", "tendisssd-1.2.3.tar.gz", "1.2.3.0.0.0"),
    (PackageType.Predixy.value, "Predixy-latest", "predixy-1.4.3.tar.gz", "1.4.3.0.0.0"),
    (PackageType.Twemproxy.value, "Twemproxy-latest", "twemproxy-0.4.1.tar.gz", "0.4.1.0.0.0"),
)


def seed_redis_v2_release_packages(pkg_specs: Iterable = REDIS_V2_RELEASE_PKG_SPECS) -> List[Package]:
    return [
        ensure_v2_release_package(
            pkg_type=pkg_type, db_type=DBType.Redis.value, series=series, full_version=full_version, name=name
        )
        for pkg_type, series, name, full_version in pkg_specs
    ]


def clear_mysql_v2_release_packages() -> None:
    """先删 Package，再拆 V2 版本链路（外键 on_delete=PROTECT）。test- 前缀发行版统一清理。"""
    Package.objects.filter(db_version__isnull=False).delete()
    DBVersion.objects.filter(version_series__distribution__name__startswith="test-").delete()
    VersionSeries.objects.filter(distribution__name__startswith="test-").delete()
    Distribution.objects.filter(name__startswith="test-").delete()
