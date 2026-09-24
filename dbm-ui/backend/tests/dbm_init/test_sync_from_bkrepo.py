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
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from backend.db_package.models import Package

pytestmark = pytest.mark.django_db

FORMAL_DIR = "/es/actuator/DBM/1.0.5.0.0.0"


def test_sync_five_level_dirs():
    media = {
        "name": "dbactuator",
        "fullPath": f"{FORMAL_DIR}/dbactuator",
        "path": f"{FORMAL_DIR}/",
        "size": 3,
        "md5": "md5",
        "createdDate": "2026-09-23T10:00:00",
        "lastModifiedDate": "2026-09-23T10:00:00",
    }
    tree = {
        # sqlfile 不是介质类型目录，不应被下钻
        "/es": (
            [{"name": "actuator", "fullPath": "/es/actuator"}, {"name": "sqlfile", "fullPath": "/es/sqlfile"}],
            [],
        ),
        "/es/actuator": ([{"name": "DBM", "fullPath": "/es/actuator/DBM"}], []),
        "/es/actuator/DBM": ([{"name": "1.0.5.0.0.0", "fullPath": FORMAL_DIR}], []),
        FORMAL_DIR: ([], [media]),
    }
    storage = Mock()
    storage.listdir.side_effect = lambda path: tree[path]

    with patch("backend.dbm_init.management.commands.sync_from_bkrepo.get_storage", return_value=storage):
        call_command("sync_from_bkrepo", "-t", "es")

    package = Package.objects.get(db_type="es", pkg_type="actuator", name="dbactuator")
    assert package.path == f"{FORMAL_DIR}/dbactuator"
    assert package.version == "1.0.5.0.0.0"
