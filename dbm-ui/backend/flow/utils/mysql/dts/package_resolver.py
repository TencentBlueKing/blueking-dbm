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
import os
from typing import Optional

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import VersionPhase
from backend.db_package.exceptions import DBPackageBaseException
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_VERSION_SERIES

logger = logging.getLogger("flow")

_DTS_PHASE_PRIORITY = [VersionPhase.ALPHA.value, VersionPhase.RELEASE.value]
# 与 mysql_rollback_exercise 的 V2 备份介质 series 保持一致
_MYSQL_DBBACKUP_VERSION_SERIES = "beta"
_DBBACKUP_PHASE_PRIORITY = [VersionPhase.ALPHA.value, VersionPhase.RELEASE.value]


def _get_v2_package_by_phase(
    db_type: str,
    pkg_type: str,
    version_series: str,
    phase: str,
    permit_os_type: str,
) -> Optional[Package]:
    packages = list(
        Package.objects.filter(
            enable=True,
            permit_os_type=permit_os_type,
            db_version__phase=phase,
            db_version__enable=True,
            db_version__version_series__name=version_series,
            db_version__version_series__distribution__db_type=db_type,
            db_version__version_series__distribution__pkg_type=pkg_type,
        ).select_related("db_version")
    )
    if not packages:
        return None
    # Package 无 recommend 字段；recommend 在 DBVersion 上，priority 在 Package 上
    # 与 mysql_rollback_exercise 的 V2 选包逻辑保持一致
    return max(
        packages,
        key=lambda pkg: (
            pkg.db_version.full_version_n if pkg.db_version else 0,
            pkg.db_version.recommend if pkg.db_version else False,
            pkg.priority,
        ),
    )


def resolve_v2_dbbackup_package(
    *,
    pkg_type: str = MediumEnum.DbBackup.value,
    version_series: str = _MYSQL_DBBACKUP_VERSION_SERIES,
    phase_priority: list[str] | None = None,
    permit_os_type: str = "Linux",
) -> Package:
    """解析 V2 dbbackup 介质包（对齐 mysql_rollback_exercise 选包逻辑）。"""
    for phase in phase_priority or _DBBACKUP_PHASE_PRIORITY:
        pkg = _get_v2_package_by_phase(
            db_type=DBType.MySQL.value,
            pkg_type=pkg_type,
            version_series=version_series,
            phase=phase,
            permit_os_type=permit_os_type,
        )
        if pkg:
            logger.info(
                _("V2 备份包命中 series={}, phase={}, pkg_type={}, package_id={}").format(
                    version_series, phase, pkg_type, pkg.id
                )
            )
            return pkg
    raise DBPackageBaseException(
        _("未找到 V2 备份介质: series={}, pkg_type={}, permit_os_type={}").format(version_series, pkg_type, permit_os_type)
    )


def resolve_mysql_dts_package(
    *,
    version_series: str = MYSQL_DTS_VERSION_SERIES,
    phase_priority: list[str] | None = None,
    permit_os_type: str = "Linux",
    pkg_id: int | None = None,
) -> Package:
    if pkg_id:
        return Package.objects.get(id=pkg_id, enable=True)
    for phase in phase_priority or _DTS_PHASE_PRIORITY:
        pkg = _get_v2_package_by_phase(
            db_type=DBType.MySQL.value,
            pkg_type=MediumEnum.MySQLDts.value,
            version_series=version_series,
            phase=phase,
            permit_os_type=permit_os_type,
        )
        if pkg:
            logger.info(_("V2 DTS 介质包命中 series={}, phase={}, package_id={}").format(version_series, phase, pkg.id))
            return pkg
    raise DBPackageBaseException(
        _("未找到 V2 DTS 介质: series={}, pkg_type={}, permit_os_type={}").format(
            version_series, MediumEnum.MySQLDts.value, permit_os_type
        )
    )


def build_mysql_dts_bkrepo_paths(pkg: Package) -> tuple[list[str], str]:
    # Job 下发到目标机后，文件名取 path 最后一段，须与启动脚本 /data/install/${PKG_NAME} 一致
    pkg_file_name = os.path.basename(pkg.path.rstrip("/")) or pkg.name
    return (
        [f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{pkg.path}"],
        pkg_file_name,
    )
