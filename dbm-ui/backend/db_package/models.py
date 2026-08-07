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
from typing import Optional

import django.utils.timezone as timezone
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from packaging.version import InvalidVersion, Version

from backend.bk_web.constants import LEN_LONG, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.db_meta.enums.version_phase import PkgSeries, VersionPhase
from backend.db_meta.models.db_version import DBVersion
from backend.db_package.constants import PackageMode, PackageType
from backend.db_package.exceptions import PackageNotExistException, VersionNoNotExistException
from backend.db_services.ipchooser.constants import BkOsType
from backend.flow.consts import MediumEnum


class Package(AuditedModel):
    name = models.CharField(_("文件名"), max_length=LEN_LONG)
    version = models.CharField(_("版本号"), max_length=LEN_NORMAL)

    # 和新版本管理的信息是重复的, 后续可以删掉
    pkg_type = models.CharField(_("安装包类型"), max_length=LEN_SHORT)
    db_type = models.CharField(
        _("存储类型"), choices=DBType.get_choices(), max_length=LEN_SHORT, default=DBType.MySQL.value
    )
    path = models.CharField(_("包路径"), max_length=LEN_LONG)
    size = models.BigIntegerField(_("包大小"))
    md5 = models.CharField(_("md5值"), max_length=LEN_SHORT)
    # allow_biz_ids 主要用于灰度场景，部分业务先用，不配置/为空 代表全业务可用
    allow_biz_ids = models.JSONField(_("允许的业务列表"), null=True)
    mode = models.CharField(_("安装包模式"), choices=PackageMode.get_choices(), max_length=LEN_SHORT, default="system")
    priority = models.IntegerField(_("文件优先级(目前只用作区分是否为默认版本)"), default=0)
    enable = models.BooleanField(help_text=_("是否启用"), default=True)
    # package独立出时间字段
    create_at = models.DateTimeField(_("创建时间"), default=timezone.now)
    update_at = models.DateTimeField(_("更新时间"), default=timezone.now)

    # 新版本管理
    db_version = models.ForeignKey(DBVersion, on_delete=models.PROTECT, blank=True, null=True)
    # os 信息
    permit_os = models.JSONField(blank=True, null=True, help_text=_("os 列表"), default=list)
    permit_os_type = models.CharField(max_length=128, default="", blank=True, null=True, help_text=_("os 类型"))

    class Meta:
        verbose_name_plural = verbose_name = _("介质包（Package）")
        ordering = ("-create_at",)

    @classmethod
    def get_latest_package(
        cls,
        version: str,
        pkg_type: str,
        bk_biz_id: Optional[int] = None,
        db_type: Optional[str] = DBType.MySQL,
        name_prefix: Optional[str] = None,
        only_enable_pkg: Optional[bool] = True,
    ) -> "Package":
        """
        根据版本和包类型获取最新的介质包
        """
        filters = {"pkg_type": pkg_type, "db_type": db_type}

        # 是否让enable参与介质过滤
        # 获取介质有不同的语义场景：有时候要是enable=True的最新/有时候要绝对意义的最新
        if only_enable_pkg:
            filters["enable"] = True

        if name_prefix:
            filters["name__startswith"] = name_prefix

        if version != MediumEnum.Latest:
            filters["version"] = version

        packages = cls.objects.filter(**filters)

        if bk_biz_id:
            # 过滤出灰度的业务以及无指定业务的包
            allow_biz_filter = Q(allow_biz_ids__contains=bk_biz_id) | Q(allow_biz_ids__isnull=True)
            packages = packages.filter(allow_biz_filter)

        if not packages:
            raise PackageNotExistException(version=version, pkg_type=pkg_type, db_type=db_type)

        # 取最新的版本
        return packages.latest("update_at")

    @staticmethod
    def _parse_semver(version: str):
        """
        将版本号解析为可比较的 packaging.version.Version 对象。
        解析失败（非法版本字符串）时兜底为 0.0.0，避免整体排序失败。
        """
        try:
            return Version(version)
        except InvalidVersion:
            return Version("0.0.0")

    @classmethod
    def get_latest_package_by_semver(
        cls,
        pkg_type: str,
        db_type: Optional[str] = DBType.MySQL,
        bk_biz_id: Optional[int] = None,
        name_prefix: Optional[str] = None,
        only_enable_pkg: Optional[bool] = True,
    ) -> "Package":
        """
        按 version 字段的语义化版本号取最大版本的介质包，而非按 update_at 时间。

        适用场景：介质包按版本号目录结构（如 /cloud/dbha-v2-probe/v2.0.0/v2.0.0-probe.tar.gz），

        排序策略：
        - 主排序：version 字段语义化比较（取最大目录版本，如 v2.0.1 > v2.0.0）。
        - 次级排序：同版本（version 相同）时按 update_at 取最新上传的包（虽然上传时要求一个目录只保留一个包，但理论上是可能存在多个的）。
        """
        filters = {"pkg_type": pkg_type, "db_type": db_type}

        if only_enable_pkg:
            filters["enable"] = True

        if name_prefix:
            filters["name__startswith"] = name_prefix

        packages = cls.objects.filter(**filters)

        if bk_biz_id:
            allow_biz_filter = Q(allow_biz_ids__contains=bk_biz_id) | Q(allow_biz_ids__isnull=True)
            packages = packages.filter(allow_biz_filter)

        if not packages:
            raise PackageNotExistException(version=MediumEnum.Latest, pkg_type=pkg_type, db_type=db_type)

        # 主排序按 version 语义版本号，并列时按 update_at 取最新
        # TODO：接入版本管理V2后，用 pkg.db_version.full_version 作比较
        return max(packages, key=lambda pkg: (cls._parse_semver(pkg.version), pkg.update_at))

    @classmethod
    def get_package_for_version_no(cls, db_type: DBType, pkg_type: PackageType, version_no: str):
        """
        根据当前版本类型，和db_meta记录的版本号信息，找到对应的介质包
        @param db_type: 包的对应的组件类型
        @param pkg_type: 包类型
        @param version_no: 实例版本号（0.0.0）
        """
        packages = cls.objects.filter(db_type=db_type, pkg_type=pkg_type, name__icontains=version_no, enable=True)

        if not packages:
            raise VersionNoNotExistException(version_no=version_no, pkg_type=pkg_type, db_type=db_type)

        # 取最新的版本
        return packages.latest("update_at")

    @classmethod
    def get_package_v2_by_phase(
        cls,
        pkg_type: str,
        series: str,
        phase: str = VersionPhase.RELEASE.value,
        db_type: Optional[str] = DBType.MySQL,
        permit_os_type: str = BkOsType.LINUX.value,
        only_enable_pkg: bool = False,
    ) -> Optional["Package"]:
        """
        获取指定数据库类型、介质类型和版本阶段（phase）的 V2 备份介质包

        逻辑说明：
        - 根据给定的 db_type、pkg_type、phase 检索可用、并启用的备份包，限定 version_series 名称为 beta
        - 默认按 permit_os_type=Linux 过滤介质包
        - 若存在多个备份包，优先选择 full_version 数值最大者；
          同一版本时，优先选择 recommend 和 priority 高的包

        返回：
        - 若找到符合条件的 Package 实例则返回，否则返回 None
        """
        # 如果 series 为空，不加过滤条件
        filters = {
            "permit_os_type": permit_os_type,
            "db_version__phase": phase,
            "db_version__version_series__distribution__db_type": db_type,
            "db_version__version_series__distribution__pkg_type": pkg_type,
        }
        if only_enable_pkg:
            filters["enable"] = only_enable_pkg
        if series:
            filters["db_version__version_series__name"] = series

        packages = list(Package.objects.filter(**filters).select_related("db_version"))
        if not packages:
            return None
        # 按 full_version 数值比较取最大版本，recommend/priority 作为同版本时的 tiebreaker
        return max(
            packages,
            key=lambda pkg: (pkg.db_version.full_version_n, pkg.db_version.recommend, pkg.priority),
        )

    @classmethod
    def get_latest_package_v2_release(
        cls, pkg_type: str, series: str = PkgSeries.LATEST.value, db_type: Optional[str] = DBType.MySQL
    ) -> Optional["Package"]:
        # series: version_series, or version_no
        return cls.get_package_v2_by_phase(
            pkg_type=pkg_type,
            series=series,
            phase=str(VersionPhase.RELEASE.value),
            permit_os_type=str(BkOsType.LINUX.value),
            db_type=db_type,
            only_enable_pkg=True,
        )

    @classmethod
    def get_latest_package_v2_alpha(
        cls,
        pkg_type: str,
        series: str = PkgSeries.LATEST.value,
        db_type: Optional[str] = DBType.MySQL,
    ) -> Optional["Package"]:
        phase = str(VersionPhase.ALPHA.value)
        permit_os_type = str(BkOsType.LINUX.value)
        return cls.get_package_v2_by_phase(
            pkg_type=pkg_type,
            series=series,
            phase=phase,
            permit_os_type=permit_os_type,
            db_type=db_type,
            only_enable_pkg=True,
        )
