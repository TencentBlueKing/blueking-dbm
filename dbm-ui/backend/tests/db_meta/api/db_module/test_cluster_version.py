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
from backend.db_meta.api.db_module import (
    get_cluster_module_layer_version,
    get_cluster_module_versions,
    get_clusters_module_versions,
    get_instance_version,
    get_instances_version,
    get_mysql_cluster_os_version,
    get_mysql_cluster_versions,
    get_mysql_clusters_os_version,
)
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.models import BKCity, Cluster, DBModule, Machine, StorageInstance
from backend.db_package.models import DBVersion, Distribution, Package, VersionSeries
from backend.db_services.ipchooser.constants import BkOsType
from backend.flow.consts import MediumEnum
from backend.tests.mock_data import constant

pytestmark = pytest.mark.django_db

_AUDIT = {"creator": "admin", "updater": "admin"}


def _make_version(pkg_type: str, full_version: str, package_os: list) -> DBVersion:
    dist = Distribution.objects.create(
        name=f"dist-{full_version}", engine="", db_type=DBType.MySQL.value, pkg_type=pkg_type, **_AUDIT
    )
    series = VersionSeries.objects.create(distribution=dist, name=f"series-{full_version}", **_AUDIT)
    version = DBVersion.objects.create(
        full_version=full_version,
        name=f"version-{full_version}",
        version_series=series,
        phase=VersionPhase.RELEASE.value,
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
        permit_os=package_os,
        permit_os_type=BkOsType.LINUX.value,
        **_AUDIT,
    )
    return version


def _binding(version: DBVersion, permit_os: list) -> dict:
    return {"db_version_id": version.id, "permit_os_type": BkOsType.LINUX.value, "permit_os": permit_os}


def _make_cluster(
    name: str, layers: dict, apply_snapshot: dict = None, cluster_type: str = ClusterType.TenDBHA
) -> Cluster:
    module = DBModule(
        bk_biz_id=constant.BK_BIZ_ID,
        db_module_name=name,
        alias_name=name,
        cluster_type=cluster_type,
        **_AUDIT,
    )
    module.current_db_version = layers
    module.save()
    return Cluster.objects.create(
        name=name,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=cluster_type,
        db_module_id=module.db_module_id,
        immute_domain=f"{name}.db",
        apply_snapshot=apply_snapshot or {},
        **_AUDIT,
    )


def _make_storage_instance(port: int, db_package: Package = None) -> StorageInstance:
    machine = Machine.objects.create(
        ip=f"127.0.0.{port % 200}",
        bk_biz_id=constant.BK_BIZ_ID,
        bk_host_id=port,
        machine_type=MachineType.BACKEND.value,
        access_layer=AccessLayer.STORAGE.value,
        bk_city=BKCity.objects.first(),
    )
    return StorageInstance.objects.create(
        machine=machine,
        port=port,
        instance_role=InstanceRole.BACKEND_MASTER.value,
        instance_inner_role=InstanceInnerRole.MASTER.value,
        db_package=db_package,
    )


class TestClusterModuleVersion:
    def test_module_versions(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.51", ["tlinux-3.2", "tlinux-4"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "0.82.19.0.0.51", ["tlinux-4"])
        cluster = _make_cluster(
            "module-only",
            {MachineType.BACKEND.value: _binding(backend, []), MachineType.PROXY.value: _binding(proxy, [])},
        )

        versions = get_cluster_module_versions(cluster)

        assert set(versions) == {MachineType.BACKEND.value, MachineType.PROXY.value}
        assert versions[MachineType.BACKEND.value].source == "module"
        assert versions[MachineType.BACKEND.value].version.full_version == "8.0.32.0.0.51"
        assert versions[MachineType.BACKEND.value].effective_permit_os == ["tlinux-3.2", "tlinux-4"]

        proxy_layer = get_cluster_module_layer_version(cluster, AccessLayer.PROXY)
        assert proxy_layer.component == MachineType.PROXY.value
        assert proxy_layer.effective_permit_os == ["tlinux-4"]

    def test_ignores_snapshot(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.55", ["tlinux-3.2", "tlinux-4"])
        cluster = _make_cluster(
            "module-ignores-snapshot",
            {MachineType.BACKEND.value: _binding(backend, [])},
            apply_snapshot={MachineType.BACKEND.value: _binding(backend, ["tlinux-4"])},
        )

        storage = get_cluster_module_layer_version(cluster, AccessLayer.STORAGE)
        assert storage.source == "module"
        assert storage.effective_permit_os == ["tlinux-3.2", "tlinux-4"]

    def test_cluster_without_version(self):
        legacy = _make_cluster("legacy", {})
        redis = _make_cluster("redis", {}, cluster_type=ClusterType.TendisPredixyRedisCluster)

        assert get_clusters_module_versions([legacy, redis]) == {legacy.id: {}, redis.id: {}}
        assert get_cluster_module_layer_version(redis, AccessLayer.STORAGE) is None


class TestMysqlClusterVersion:
    def test_without_snapshot_uses_module(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.56", ["tlinux-3.2"])
        cluster = _make_cluster("mysql-module", {MachineType.BACKEND.value: _binding(backend, [])})

        storage = get_mysql_cluster_os_version(cluster, AccessLayer.STORAGE)
        assert storage.source == "module"
        assert storage.effective_permit_os == ["tlinux-3.2"]

    def test_snapshot_takes_priority_over_module(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.52", ["tlinux-3.2", "tlinux-4"])
        cluster = _make_cluster(
            "with-snapshot",
            {MachineType.BACKEND.value: _binding(backend, [])},
            apply_snapshot={MachineType.BACKEND.value: _binding(backend, ["tlinux-4"])},
        )

        storage = get_mysql_cluster_versions(cluster)[MachineType.BACKEND.value]
        assert storage.source == "snapshot"
        assert storage.binding.permit_os == ("tlinux-4",)
        assert storage.effective_permit_os == ["tlinux-4"]
        assert storage.version.full_version == "8.0.32.0.0.52"
        assert get_mysql_cluster_os_version(cluster, AccessLayer.STORAGE) == storage

    def test_legacy_cluster_has_no_version(self):
        cluster = _make_cluster("mysql-legacy", {})

        assert get_mysql_cluster_versions(cluster) == {}
        assert get_mysql_cluster_os_version(cluster, AccessLayer.STORAGE) is None

    def test_batch_mixes_snapshot_module_and_legacy(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.53", ["tlinux-3.2"])
        by_module = _make_cluster("batch-module", {MachineType.BACKEND.value: _binding(backend, [])})
        by_snapshot = _make_cluster(
            "batch-snapshot",
            {MachineType.BACKEND.value: _binding(backend, [])},
            apply_snapshot={MachineType.BACKEND.value: _binding(backend, [])},
        )
        legacy = _make_cluster("batch-legacy", {})

        result = get_mysql_clusters_os_version([by_module, by_snapshot, legacy], AccessLayer.STORAGE)

        assert result[by_module.id].source == "module"
        assert result[by_snapshot.id].source == "snapshot"
        assert result[legacy.id] is None


class TestInstanceVersion:
    def test_version_from_db_package(self):
        version = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.54", [])
        installed = _make_storage_instance(20001, Package.objects.get(db_version=version))
        legacy = _make_storage_instance(20002)

        result = get_instances_version([installed, legacy])

        assert result[installed.id].full_version == "8.0.32.0.0.54"
        assert result[installed.id].version_series == "series-8.0.32.0.0.54"
        assert result[legacy.id] is None
        assert get_instance_version(installed).db_version_id == version.id
