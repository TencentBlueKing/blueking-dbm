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
from unittest.mock import Mock

import pytest

from backend.core.storages.handlers import StorageHandler
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.exceptions import PackagePathException
from backend.db_package.models import Package
from backend.db_package.views import DBPackageViewSet

move_package_to_formal = DBPackageViewSet.move_package_to_formal

pytestmark = pytest.mark.django_db

_AUDIT = {"creator": "admin", "updater": "admin"}
FULL_VERSION = "8.0.30.0.0.1"


@pytest.fixture
def db_version():
    distribution = Distribution.objects.create(name="TMySQL", engine="", db_type="mysql", pkg_type="mysql", **_AUDIT)
    series = VersionSeries.objects.create(distribution=distribution, name="8.0", **_AUDIT)
    return DBVersion.objects.create(
        full_version=FULL_VERSION,
        name="mysql_tmysql_8.0.30",
        version_series=series,
        phase=VersionPhase.RELEASE.value,
        **_AUDIT,
    )


class TestBuildFormalPath:
    def test_build_from_distribution_snapshot(self, db_version):
        path = Package.build_formal_path(db_version, "mysql", "mysql", "mysql-8.0.30.tar.gz")

        assert path == f"/mysql/mysql/TMySQL/{FULL_VERSION}/mysql-8.0.30.tar.gz"

    def test_fallback_to_distribution_when_snapshot_empty(self, db_version):
        DBVersion.objects.filter(id=db_version.id).update(distribution_snapshot={})
        db_version.refresh_from_db()

        path = Package.build_formal_path(db_version, "mysql", "mysql", "mysql-8.0.30.tar.gz")

        assert path == f"/mysql/mysql/TMySQL/{FULL_VERSION}/mysql-8.0.30.tar.gz"

    @pytest.mark.parametrize(
        "db_type,pkg_type,file_name",
        [
            ("redis", "mysql", "a.tar.gz"),
            ("mysql", "spider", "a.tar.gz"),
            ("mysql", "mysql", ".."),
            ("mysql", "mysql", ""),
        ],
    )
    def test_invalid_args_raise(self, db_version, db_type, pkg_type, file_name):
        with pytest.raises(PackagePathException):
            Package.build_formal_path(db_version, db_type, pkg_type, file_name)


class TestMovePackageToFormal:
    def test_staging_path_moved_by_db_version(self, db_version):
        handler = StorageHandler(storage=Mock())
        handler.move_staging_file_to_formal = Mock(side_effect=lambda staging, formal: formal)
        pkg_data = {
            "path": "/staging/mysql/mysql/TMySQL/1790153031593/mysql-8.0.30.tar.gz",
            "db_type": "mysql",
            "pkg_type": "mysql",
            "db_version": db_version,
        }

        assert move_package_to_formal(handler, pkg_data) == f"/mysql/mysql/TMySQL/{FULL_VERSION}/mysql-8.0.30.tar.gz"

    def test_formal_path_kept(self):
        handler = StorageHandler(storage=Mock())
        pkg_data = {"path": "/mysql/mysql/8.0/mysql-8.0.30.tar.gz", "db_type": "mysql", "pkg_type": "mysql"}

        assert move_package_to_formal(handler, pkg_data) == pkg_data["path"]
        handler.storage.client.move_file.assert_not_called()

    def test_staging_without_db_version_raises(self):
        handler = StorageHandler(storage=Mock())
        pkg_data = {
            "path": "/staging/mysql/mysql/TMySQL/1790153031593/mysql-8.0.30.tar.gz",
            "db_type": "mysql",
            "pkg_type": "mysql",
            "db_version": None,
        }

        with pytest.raises(PackagePathException):
            move_package_to_formal(handler, pkg_data)
        handler.storage.client.move_file.assert_not_called()
