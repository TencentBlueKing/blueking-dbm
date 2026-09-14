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


def ensure_v2_release_package(*, pkg_type: str, db_type: str = DBType.MySQL.value) -> Package:
    """写入一条能被 Package.get_latest_package_v2_release 命中的介质包。"""
    dist, _ = Distribution.objects.get_or_create(
        db_type=db_type,
        pkg_type=pkg_type,
        name=f"test-{pkg_type}",
        defaults={"engine": "", **_AUDIT},
    )
    series, _ = VersionSeries.objects.get_or_create(
        distribution=dist,
        name=PkgSeries.LATEST.value,
        defaults=_AUDIT,
    )
    db_version, _ = DBVersion.objects.get_or_create(
        full_version=_V2_FULL_VERSION,
        distribution_id=dist.id,
        defaults={
            "name": f"test-{pkg_type}-1.0.0",
            "version_series": series,
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
            "name": f"{pkg_type}.tar.gz",
            "version": PkgSeries.LATEST.value,
            "db_type": db_type,
            "path": f"/tmp/{pkg_type}/",
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


def clear_mysql_v2_release_packages() -> None:
    """先删 Package，再拆 V2 版本链路（外键 on_delete=PROTECT）。"""
    Package.objects.filter(db_version__isnull=False).delete()
    DBVersion.objects.filter(full_version=_V2_FULL_VERSION, name__startswith="test-").delete()
    VersionSeries.objects.filter(name=PkgSeries.LATEST.value, distribution__name__startswith="test-").delete()
    Distribution.objects.filter(name__startswith="test-").delete()
