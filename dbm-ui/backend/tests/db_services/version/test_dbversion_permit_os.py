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
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from backend.configuration.constants import DBType
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.models import Package
from backend.db_services.ipchooser.constants import BkOsType
from backend.db_services.version.views.dbversion import DBVersionViewSet
from backend.flow.consts import MediumEnum

pytestmark = pytest.mark.django_db

_AUDIT = {"creator": "admin", "updater": "admin"}


def _make_version() -> DBVersion:
    dist = Distribution.objects.create(
        name="Tendb Proxy", engine="", db_type=DBType.MySQL.value, pkg_type=MediumEnum.MySQLProxy.value, **_AUDIT
    )
    series = VersionSeries.objects.create(distribution=dist, name="Proxy-2.x", **_AUDIT)
    return DBVersion.objects.create(
        full_version="2.1.0.0.0.1",
        name="Proxy-2.1",
        version_series=series,
        phase=VersionPhase.RELEASE.value,
        distribution_id=dist.id,
        **_AUDIT,
    )


def _make_package(version: DBVersion, name: str, os_type: str, permit_os: list, enable: bool = True) -> None:
    Package.objects.create(
        name=name,
        version=version.full_version,
        pkg_type=MediumEnum.MySQLProxy.value,
        db_type=DBType.MySQL.value,
        path=f"/tmp/{name}",
        size=1,
        md5="abc",
        enable=enable,
        db_version=version,
        permit_os=permit_os,
        permit_os_type=os_type,
        **_AUDIT,
    )


def _get_permit_os(version_id: int):
    request = APIRequestFactory().get(f"/apis/version/dbversion/{version_id}/list_permit_os/")
    force_authenticate(request, user=get_user_model()(username="admin"))
    view = DBVersionViewSet.as_view({"get": "list_permit_os"})
    with patch.object(DBVersionViewSet, "get_permissions", lambda self: []):
        return view(request, pk=version_id)


class TestDBVersionPermitOs:
    def test_first_enabled_package(self):
        version = _make_version()
        _make_package(version, "proxy-a.tar.gz", BkOsType.LINUX.value, ["centos-7"], enable=False)
        _make_package(version, "proxy-b.tar.gz", BkOsType.LINUX.value, ["tlinux-3.2", "tlinux-4"])
        _make_package(version, "proxy-c.tar.gz", BkOsType.WINDOWS.value, ["windows-2019"])

        response = _get_permit_os(version.id)

        assert response.status_code == 200
        assert response.data == [{"permit_os_type": BkOsType.LINUX.value, "permit_os": ["tlinux-3.2", "tlinux-4"]}]

    def test_no_enabled_package(self):
        version = _make_version()
        _make_package(version, "proxy-a.tar.gz", BkOsType.LINUX.value, ["tlinux-3.2"], enable=False)

        response = _get_permit_os(version.id)

        assert response.status_code == 200
        assert response.data == []
