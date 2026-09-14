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
from typing import List

from backend.configuration.constants import DBType
from backend.db_package.constants import PackageType
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum

_AUDIT = {"creator": "admin", "updater": "admin"}


def ensure_package(
    *,
    pkg_type: str,
    db_type: str,
    version: str = MediumEnum.Latest.value,
    name: str = "",
    path: str = "",
) -> Package:
    """写入一条能被 Package.get_latest_package 命中的旧版介质包。"""
    package, _ = Package.objects.get_or_create(
        pkg_type=pkg_type,
        db_type=db_type,
        version=version,
        defaults={
            "name": name or f"{pkg_type}.tar.gz",
            "path": path or f"/tmp/{pkg_type}/",
            "size": 0,
            "md5": "",
            "enable": True,
            **_AUDIT,
        },
    )
    return package


def seed_redis_packages() -> List[Package]:
    """Redis 单据 patch_ticket_detail 会冻结 RedisTools latest 包。"""
    return [
        ensure_package(
            pkg_type=PackageType.RedisTools.value,
            db_type=DBType.Redis.value,
            version=MediumEnum.Latest.value,
        )
    ]
