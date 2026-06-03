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
from functools import reduce
from operator import or_
from typing import Tuple

from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from packaging import version as pkg_version
from packaging.version import InvalidVersion

from backend.configuration.constants import DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum

logger = logging.getLogger("root")


class DorisUpgradeVersionPolicy:
    """
    Doris 升级版本策略：列表与校验的唯一真源。

    封装的业务规则（统一在此处实现，避免 query / validator 双写漂移）：
    1. series 白名单：取 major.minor 作为系列号，从 SystemSettings.DORIS_UPGRADE_VERSION_MAP
       读取 current_series -> [allowed_series, ...] 的映射；
    2. 版本严格大于：目标版本必须语义大于当前版本（避免 "2.1.10" 字符串序误判 < "2.1.9"）；
    3. 介质存在性：目标版本必须在 db_package.Package 表中以 db_type=Doris、pkg_type=Doris、
       enable=True 的形式存在（即"已上架的可安装介质"）。

    对外暴露两个方法：
    - list_candidates(current_version): 列出所有合法可升级目标的 Package QuerySet；
    - validate(current_version, new_version): 校验 (当前, 目标) 这一对版本是否合法。
    """

    # ---------- 内部小工具 ----------

    @staticmethod
    def _series_of(version_str: str) -> str:
        """取版本号前两位作为 series，例如 '2.1.5' -> '2.1'"""
        return ".".join(version_str.split(".")[:2])

    @staticmethod
    def _load_upgrade_map() -> dict:
        """读取 Doris 版本升级映射；未配置时兜底为 {}"""
        return SystemSettings.get_setting_value(key=SystemSettingsEnum.DORIS_UPGRADE_VERSION_MAP.value, default={})

    @classmethod
    def _allowed_series(cls, current_version: str) -> list:
        """获取 current_version 所在 series 允许升级到的 series 列表；若无配置返回 []"""
        upgrade_map = cls._load_upgrade_map()
        return upgrade_map.get(cls._series_of(current_version)) or []

    @staticmethod
    def _safe_parse(version_str: str):
        """安全解析版本号；非法版本号返回 None，由调用方决定如何处理"""
        try:
            return pkg_version.parse(version_str)
        except InvalidVersion:
            return None

    @staticmethod
    def _query_packages_by_series(allowed_series: list) -> QuerySet:
        """
        按 series 白名单查询 Doris 安装介质（DB 层一次性下推 series + db_type + pkg_type + enable）。

        例：allowed_series=['2.1', '3.0'] → version LIKE '2.1.%' OR version LIKE '3.0.%'
        加 "." 后缀以防止 "2.1" 误匹配 "2.10.x"。
        """
        series_q = reduce(or_, (Q(version__startswith=f"{s}.") for s in allowed_series))
        return Package.objects.filter(series_q, db_type=DBType.Doris, pkg_type=MediumEnum.Doris, enable=True).order_by(
            "-priority", "-update_at"
        )

    @classmethod
    def _filter_strictly_greater(cls, qs: QuerySet, current_version: str) -> QuerySet:
        """
        在已按 series 过滤的 qs 上，再剔除"版本号 <= 当前版本"的包。

        语义比较走 packaging（避免 "2.1.10" 字符串序误判 < "2.1.9"），无法下推 DB，
        故在应用层捞出 (id, version) 后再回 DB 用 id__in 拿一个新 QuerySet，
        以保留 order_by("-priority", "-update_at") 的链式可用性。
        """
        current_parsed = cls._safe_parse(current_version)
        if current_parsed is None:
            # 当前版本号异常时，跳过大小比较，仅按 series + 介质过滤
            logger.warning("doris upgrade: invalid current_version=%s, skip strict-gt filter", current_version)
            return qs

        upgradable_ids = [
            pkg_id
            for pkg_id, ver in qs.values_list("id", "version")
            if (parsed := cls._safe_parse(ver)) is not None and parsed > current_parsed
        ]
        return Package.objects.filter(id__in=upgradable_ids).order_by("-priority", "-update_at")

    # ---------- 对外接口 ----------

    @classmethod
    def list_candidates(cls, current_version: str) -> QuerySet:
        """
        列出 current_version 所有合法的可升级目标 Package。

        过滤管道（先 DB 下推、后应用层比较）：
            series 白名单  →  介质字段(db_type/pkg_type/enable)  →  版本严格大于

        @param current_version: 当前集群版本，如 "2.0.4"
        @return: 已过滤、按 priority/update_at 倒序的 Package QuerySet；
                 无任何合法升级路径时返回空 QuerySet。
        """
        allowed_series = cls._allowed_series(current_version)
        if not allowed_series:
            return Package.objects.none()

        qs = cls._query_packages_by_series(allowed_series)
        return cls._filter_strictly_greater(qs, current_version)

    @classmethod
    def validate(cls, current_version: str, new_version: str) -> Tuple[bool, str]:
        """
        校验是否可以从 current_version 升级到 new_version。

        @param current_version: 当前集群版本，如 "2.0.4"
        @param new_version: 目标升级版本，如 "2.1.5"
        @return: (是否合法, 错误信息)；合法时错误信息为空字符串。

        注意：本方法严格复用 list_candidates 的过滤规则（含介质存在性），
        以保证"前端列表给得出"与"后端校验放得过"两侧语义完全一致。
        """
        if not new_version:
            return False, _("new_version 不能为空")

        if current_version == new_version:
            return False, _("目标版本 {} 与集群当前版本相同，无需升级").format(new_version)

        # series 白名单（先做这层判断是为了给出更精准的错误信息）
        allowed_series = cls._allowed_series(current_version)
        if not allowed_series:
            # 内部配置缺失的细节仅落日志，避免对外暴露内部模型/配置项名称
            logger.error(
                "doris upgrade version map missing series: current_series=%s, setting_key=%s",
                cls._series_of(current_version),
                SystemSettingsEnum.DORIS_UPGRADE_VERSION_MAP.value,
            )
            return False, _("当前版本 {} 暂不支持升级，请联系系统管理员").format(current_version)

        if cls._series_of(new_version) not in allowed_series:
            return False, _("不支持从版本 {} 升级到版本 {}").format(current_version, new_version)

        # 严格大于（同 series 下也不允许降级到更低补丁号，如 2.1.10 -> 2.1.5）
        current_parsed = cls._safe_parse(current_version)
        new_parsed = cls._safe_parse(new_version)
        if current_parsed is None or new_parsed is None:
            logger.error(
                "doris upgrade version parse failed: current_version=%s, new_version=%s",
                current_version,
                new_version,
            )
            return False, _("版本号格式非法：current={}, new={}").format(current_version, new_version)
        if new_parsed <= current_parsed:
            return False, _("目标版本 {} 必须高于当前版本 {}").format(new_version, current_version)

        # 介质存在性：复用 list_candidates 的 QuerySet，避免规则双写
        if not cls.list_candidates(current_version).filter(version=new_version).exists():
            return False, _("目标版本 {} 暂无可用安装介质，请联系系统管理员上架对应版本").format(new_version)

        return True, ""
