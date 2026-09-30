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
import pytest

from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.api.db_module.version import (
    PackageOs,
    describe_module_version,
    enabled_package_os,
    get_layer_permit_os,
    storage_version_series,
    validate_components,
)
from backend.db_meta.dataclass import DBModuleComponentVersion
from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.enums.machine_type import MachineType
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.exceptions import DBModuleVersionException
from backend.db_meta.models import DBModule
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.models import Package
from backend.db_services.cmdb.serializers import CreateModuleSLZ
from backend.db_services.ipchooser.constants import BkOsType
from backend.flow.consts import MediumEnum
from backend.tests.mock_data import constant

pytestmark = pytest.mark.django_db

_AUDIT = {"creator": "admin", "updater": "admin"}


def _make_version(pkg_type: str, series_name: str, full_version: str, permit_os, enable=True) -> DBVersion:
    dist = Distribution.objects.create(
        name=f"TXSQL-{full_version}",
        engine="",
        db_type=DBType.MySQL.value,
        pkg_type=pkg_type,
        **_AUDIT,
    )
    series = VersionSeries.objects.create(distribution=dist, name=series_name, **_AUDIT)
    version = DBVersion.objects.create(
        full_version=full_version,
        name=series_name,
        version_series=series,
        phase=VersionPhase.RELEASE.value,
        enable=enable,
        distribution_id=dist.id,
        **_AUDIT,
    )
    Package.objects.create(
        name=f"{pkg_type}-{full_version}.tar.gz",
        version=full_version,
        pkg_type=pkg_type,
        db_type=DBType.MySQL.value,
        path=f"/tmp/{full_version}",
        size=1,
        md5="abc",
        enable=True,
        db_version=version,
        permit_os=list(permit_os),
        permit_os_type=BkOsType.LINUX.value,
        **_AUDIT,
    )
    return version


def _layer(version: DBVersion, permit_os) -> dict:
    return {
        "db_version_id": version.id,
        "permit_os_type": BkOsType.LINUX.value,
        "permit_os": list(permit_os),
    }


class TestDBModuleComponentVersion:
    def test_create_ha_follow_and_fixed(self):
        backend = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.1", ["tlinux-3.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "Proxy-2.x", "2.1.0.0.0.1", ["tlinux-3.2", "tlinux-4"])
        created = api.db_module.create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="order-service",
            cluster_type=ClusterType.TenDBHA.value,
            creator="admin",
            db_versions={
                MachineType.BACKEND.value: _layer(backend, []),
                MachineType.PROXY.value: _layer(proxy, ["tlinux-3.2"]),
            },
        )
        module = DBModule.objects.get(db_module_id=created["db_module_id"])
        assert module.current_db_version[MachineType.BACKEND.value].follow_package is True
        assert module.current_db_version[MachineType.PROXY.value].permit_os == ("tlinux-3.2",)
        info = created["db_version_info"]
        assert info[MachineType.BACKEND.value]["effective_permit_os"] == ["tlinux-3.2"]
        assert info[MachineType.BACKEND.value]["distribution"] == "TXSQL-8.0.32.0.0.1"
        assert info[MachineType.PROXY.value]["effective_permit_os"] == ["tlinux-3.2"]
        assert info[MachineType.PROXY.value]["follow_package"] is False

        Package.objects.filter(db_version=backend).update(permit_os=["tlinux-3.2", "tlinux-4"])
        refreshed = describe_module_version(module)
        assert refreshed[MachineType.BACKEND.value]["effective_permit_os"] == ["tlinux-3.2", "tlinux-4"]
        assert refreshed[MachineType.PROXY.value]["effective_permit_os"] == ["tlinux-3.2"]

        Package.objects.filter(db_version=backend).update(enable=False)
        no_package = describe_module_version(module)
        assert no_package[MachineType.BACKEND.value]["effective_permit_os"] is None

    def test_only_first_enabled_package_counts(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.10", ["tlinux-3.2"])
        Package.objects.create(
            name="mysql-extra.tar.gz",
            version="8.0.32.0.0.10-extra",
            pkg_type=MediumEnum.MySQL.value,
            db_type=DBType.MySQL.value,
            path="/tmp/extra",
            size=1,
            md5="def",
            enable=True,
            db_version=mysql,
            permit_os=["tlinux-4"],
            permit_os_type=BkOsType.LINUX.value,
            **_AUDIT,
        )
        assert enabled_package_os([mysql.id]) == {mysql.id: PackageOs(BkOsType.LINUX.value, ["tlinux-3.2"])}
        with pytest.raises(DBModuleVersionException):
            validate_components(
                {MachineType.SINGLE.value: DBModuleComponentVersion.from_dict(_layer(mysql, ["tlinux-4"]))}
            )

    def test_get_layer_permit_os(self):
        backend = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.7", ["tlinux-3.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "Proxy-2.x", "2.1.0.0.0.7", ["tlinux-3.2", "tlinux-4"])
        created = api.db_module.create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="os-query",
            cluster_type=ClusterType.TenDBHA.value,
            creator="admin",
            db_versions={
                MachineType.BACKEND.value: _layer(backend, []),
                MachineType.PROXY.value: _layer(proxy, ["tlinux-4"]),
            },
        )
        module = DBModule.objects.get(db_module_id=created["db_module_id"])

        assert get_layer_permit_os(module, AccessLayer.PROXY) == (BkOsType.LINUX.value, ["tlinux-4"])
        assert get_layer_permit_os(module, AccessLayer.STORAGE) == (BkOsType.LINUX.value, ["tlinux-3.2"])

        Package.objects.filter(db_version=backend).update(permit_os=[])
        assert get_layer_permit_os(module, AccessLayer.STORAGE) == (BkOsType.LINUX.value, [])

        Package.objects.filter(db_version=backend).update(enable=False)
        assert get_layer_permit_os(module, AccessLayer.STORAGE) == (BkOsType.LINUX.value, None)

        legacy = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="legacy-os",
            cluster_type=ClusterType.TenDBHA.value,
            alias_name="legacy-os",
            **_AUDIT,
        )
        assert get_layer_permit_os(legacy, AccessLayer.PROXY) is None

    def test_update_os_keeps_version_id(self):
        backend = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.2", ["tlinux-3.2", "tlinux-4"])
        another = _make_version(MediumEnum.MySQL.value, "MySQL-5.7", "5.7.36.0.0.2", ["tlinux-2.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "Proxy-2.x", "2.1.0.0.0.2", ["tlinux-3.2"])
        created = api.db_module.create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="payment",
            cluster_type=ClusterType.TenDBHA.value,
            creator="admin",
            db_versions={
                MachineType.BACKEND.value: _layer(backend, []),
                MachineType.PROXY.value: _layer(proxy, []),
            },
        )
        module = DBModule.objects.get(db_module_id=created["db_module_id"])
        ignored = api.db_module.update_permit_os(
            constant.BK_BIZ_ID,
            module.db_module_id,
            {MachineType.BACKEND.value: _layer(another, [])},
        )
        assert ignored["db_version_info"][MachineType.BACKEND.value]["db_version_id"] == backend.id

        updated = api.db_module.update_permit_os(
            constant.BK_BIZ_ID,
            module.db_module_id,
            {MachineType.BACKEND.value: {"permit_os_type": BkOsType.LINUX.value, "permit_os": ["tlinux-4"]}},
        )
        assert updated["db_version_info"][MachineType.BACKEND.value]["permit_os"] == ["tlinux-4"]
        assert updated["db_version_info"][MachineType.BACKEND.value]["db_version_id"] == backend.id
        module.refresh_from_db()
        assert module.current_db_version[MachineType.PROXY.value].db_version_id == proxy.id

    def test_reject_wrong_pkg_disabled_version_and_os(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.3", ["tlinux-3.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "Proxy-2.x", "2.1.0.0.0.3", ["tlinux-3.2"])
        disabled = _make_version(MediumEnum.MySQL.value, "MySQL-5.6", "5.6.24.0.0.3", ["tlinux-1.2"], enable=False)
        invalid_layers = [
            _layer(proxy, []),
            _layer(disabled, []),
            _layer(mysql, ["windows-2019"]),
            {"db_version_id": mysql.id, "permit_os_type": BkOsType.WINDOWS.value, "permit_os": []},
        ]
        for raw in invalid_layers:
            with pytest.raises(DBModuleVersionException):
                validate_components({MachineType.BACKEND.value: DBModuleComponentVersion.from_dict(raw)})

    def test_setter_rejects_unknown_component(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.6", ["tlinux-3.2"])
        module = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="legacy",
            cluster_type=ClusterType.TenDBCluster.value,
            alias_name="legacy",
            **_AUDIT,
        )
        with pytest.raises(DBModuleVersionException):
            module.current_db_version = {"tdbctl": _layer(mysql, [])}

        redis_module = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="redis-mod",
            cluster_type=ClusterType.TendisPredixyRedisCluster.value,
            alias_name="redis-mod",
            **_AUDIT,
        )
        with pytest.raises(DBModuleVersionException):
            redis_module.current_db_version = {MachineType.PREDIXY.value: _layer(mysql, [])}

    def test_unrestricted_package_os_allows_any_specified_os(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.8", [])
        validate_components(
            {MachineType.SINGLE.value: DBModuleComponentVersion.from_dict(_layer(mysql, ["a", "b", "c"]))}
        )

    def test_reject_follow_when_version_has_no_package(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.5", ["tlinux-3.2"])
        Package.objects.filter(db_version=mysql).update(enable=False)
        with pytest.raises(DBModuleVersionException):
            validate_components({MachineType.SINGLE.value: DBModuleComponentVersion.from_dict(_layer(mysql, []))})

    def test_target_version_does_not_overwrite_current(self):
        mysql = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.4", ["tlinux-3.2"])
        module = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="single-mod",
            cluster_type=ClusterType.TenDBSingle.value,
            alias_name="single-mod",
            **_AUDIT,
        )
        module.target_db_version = {MachineType.SINGLE.value: _layer(mysql, [])}
        module.save()
        module.refresh_from_db()
        assert module.current_db_version_info_dict == {}
        assert module.target_db_version[MachineType.SINGLE.value].db_version_id == mysql.id

    def test_create_serializer_requires_layers(self):
        serializer = CreateModuleSLZ(data={"db_module_name": "web", "cluster_type": ClusterType.TenDBSingle.value})
        assert serializer.is_valid() is False

    def test_storage_version_series_uses_storage_layer(self):
        backend = _make_version(MediumEnum.MySQL.value, "MySQL-8.0", "8.0.32.0.0.9", ["tlinux-3.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "Proxy-2.x", "2.1.0.0.0.9", ["tlinux-3.2"])
        created = api.db_module.create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="series-ha",
            cluster_type=ClusterType.TenDBHA.value,
            creator="admin",
            db_versions={
                MachineType.BACKEND.value: _layer(backend, []),
                MachineType.PROXY.value: _layer(proxy, []),
            },
        )
        ha_module = DBModule.objects.get(db_module_id=created["db_module_id"])
        bare_module = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="series-bare",
            cluster_type=ClusterType.TenDBHA.value,
            alias_name="series-bare",
            **_AUDIT,
        )
        series = storage_version_series([ha_module, bare_module])
        assert series[ha_module.db_module_id] == "MySQL-8.0"
        assert series[bare_module.db_module_id] == ""
