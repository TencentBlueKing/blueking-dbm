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
from dataclasses import dataclass
from typing import Dict, List, Literal, Mapping, Optional, Sequence, Tuple

from django.utils.translation import gettext_lazy as _

from backend.db_meta.exceptions import DBModuleVersionException
from backend.db_services.ipchooser.constants import BkOsType


@dataclass(frozen=True)
class DBModuleComponentVersion:
    """DBModule.current_db_version_info_dict / target_db_version_info_dict 中单个组件的值。

    permit_os 为空：跟随该 db_version 已启用介质包的操作系统，介质包变化后读取结果跟着变。
    permit_os 非空：固定范围，写入后不随介质包变化。
    tendbsingle 样例
    "single": {
        "db_version_id": 1,
        "permit_os_type": "Linux",
        "permit_os": [] // 跟随版本包
    }
    tendbha 样例
    "proxy": {
        "db_version_id": 1,
        "permit_os_type": "Linux",
        "permit_os": ["tlinux", "centos"] // 固定范围
    }
    """

    db_version_id: int
    permit_os_type: str
    permit_os: Tuple[str, ...] = ()

    @property
    def follow_package(self) -> bool:
        return not self.permit_os

    def to_dict(self) -> Dict:
        return {
            "db_version_id": self.db_version_id,
            "permit_os_type": self.permit_os_type,
            "permit_os": list(self.permit_os),
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "DBModuleComponentVersion":
        if not isinstance(data, Mapping):
            raise DBModuleVersionException(message=_("组件版本必须是对象"))
        try:
            db_version_id = int(data["db_version_id"])
            permit_os_type = data["permit_os_type"]
            permit_os = data["permit_os"]
        except (KeyError, TypeError, ValueError):
            raise DBModuleVersionException(message=_("组件版本需要 db_version_id、permit_os_type、permit_os"))

        if db_version_id <= 0:
            raise DBModuleVersionException(message=_("db_version_id 必须大于 0"))

        if not isinstance(permit_os_type, str) or permit_os_type not in {item.value for item in BkOsType}:
            raise DBModuleVersionException(message=_("permit_os_type 不在操作系统类型范围内"))

        if not isinstance(permit_os, Sequence) or isinstance(permit_os, (str, bytes)):
            raise DBModuleVersionException(message=_("permit_os 必须是字符串列表"))

        normalized: List[str] = []
        for item in permit_os:
            if not isinstance(item, str) or not item:
                raise DBModuleVersionException(message=_("permit_os 中的每一项都必须是非空字符串"))
            if item not in normalized:
                normalized.append(item)

        return cls(db_version_id=db_version_id, permit_os_type=permit_os_type, permit_os=tuple(normalized))


@dataclass(frozen=True)
class VersionInfo:
    """一个具体版本。full_version 是六段式，例如 8.0.32.0.0.11。"""

    db_version_id: int
    full_version: str
    version_series: str
    version_name: str
    distribution: str

    @classmethod
    def from_db_version(cls, db_version) -> "VersionInfo":
        return cls(
            db_version_id=db_version.id,
            full_version=db_version.full_version,
            version_series=db_version.version_series.name if db_version.version_series else "",
            version_name=db_version.name,
            distribution=(db_version.distribution_snapshot or {}).get("name", ""),
        )


@dataclass(frozen=True)
class LayerVersion:
    """组件绑定的版本，以及当前生效的操作系统约束。

    binding：模块或集群快照上保存的原始绑定。
    effective_permit_os：生效的操作系统列表，空列表表示不限制；
        跟随版本包但查不到同类型的已启用介质包时为 None。
    version：绑定的版本已被删除时为 None。
    source：数据来自模块（module）还是集群部署快照（snapshot）。
    """

    component: str
    binding: DBModuleComponentVersion
    effective_permit_os: Optional[List[str]]
    version: Optional[VersionInfo]
    source: Literal["module", "snapshot"]
