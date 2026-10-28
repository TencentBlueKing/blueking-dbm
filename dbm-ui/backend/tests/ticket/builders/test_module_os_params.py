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
from types import SimpleNamespace

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.models import Cluster, DBModule
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.models import Package
from backend.db_services.ipchooser.constants import BkOsType
from backend.flow.consts import MediumEnum
from backend.tests.mock_data import constant
from backend.ticket.builders import ResourceApplyParamBuilder

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


def _make_module(name: str, cluster_type: str, layers: dict) -> DBModule:
    module = DBModule(
        bk_biz_id=constant.BK_BIZ_ID, db_module_name=name, alias_name=name, cluster_type=cluster_type, **_AUDIT
    )
    module.current_db_version = {
        component: {"db_version_id": version.id, "permit_os_type": BkOsType.LINUX.value, "permit_os": permit_os}
        for component, (version, permit_os) in layers.items()
    }
    module.save()
    return module


def _make_cluster(name: str, module: DBModule) -> Cluster:
    return Cluster.objects.create(
        name=name,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=module.cluster_type,
        db_module_id=module.db_module_id,
        immute_domain=f"{name}.db",
        **_AUDIT,
    )


class TestPatchModuleOsParams:
    def test_ha_module_storage_and_proxy(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.11", ["tlinux-3.2", "tlinux-4"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "2.1.0.0.0.11", ["tlinux-3.2", "tlinux-4"])
        module = _make_module(
            "ha-os",
            ClusterType.TenDBHA.value,
            {MachineType.BACKEND.value: (backend, []), MachineType.PROXY.value: (proxy, ["tlinux-4"])},
        )
        resource_spec = {"backend_group": {"spec_id": 1, "count": 1}, "proxy": {"spec_id": 2, "count": 2}}

        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "backend_group", module, AccessLayer.STORAGE)
        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "proxy", module, AccessLayer.PROXY)

        assert resource_spec["backend_group"]["os_type"] == BkOsType.LINUX.value
        assert resource_spec["backend_group"]["os_names"] == ["tlinux-3.2", "tlinux-4"]
        assert resource_spec["proxy"]["os_names"] == ["tlinux-4"]

    def test_single_module_storage_uses_single_component(self):
        single = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.12", ["tlinux-3.2"])
        module = _make_module("single-os", ClusterType.TenDBSingle.value, {MachineType.SINGLE.value: (single, [])})
        resource_spec = {"backend": {"spec_id": 1, "count": 1}}

        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "backend", module, AccessLayer.STORAGE)

        assert resource_spec["backend"]["os_names"] == ["tlinux-3.2"]

    def test_unrestricted_package_only_sets_os_type(self):
        remote = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.13", [])
        module = _make_module("cluster-os", ClusterType.TenDBCluster.value, {MachineType.REMOTE.value: (remote, [])})
        resource_spec = {"remote": {"spec_id": 1, "count": 1}}

        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "remote", module, AccessLayer.STORAGE)

        assert resource_spec["remote"]["os_type"] == BkOsType.LINUX.value
        assert "os_names" not in resource_spec["remote"]

    def test_no_enabled_package_only_sets_os_type(self):
        single = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.17", ["tlinux-3.2"])
        module = _make_module("single-no-pkg", ClusterType.TenDBSingle.value, {MachineType.SINGLE.value: (single, [])})
        Package.objects.filter(db_version=single).update(enable=False)
        resource_spec = {"backend": {"spec_id": 1, "count": 1}}

        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "backend", module, AccessLayer.STORAGE)

        assert resource_spec["backend"] == {"spec_id": 1, "count": 1, "os_type": BkOsType.LINUX.value}

    def test_skip_manual_hosts_and_unset_layer(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.14", ["tlinux-3.2"])
        module = _make_module("ha-partial", ClusterType.TenDBHA.value, {MachineType.BACKEND.value: (backend, [])})
        resource_spec = {"new_slave": {"hosts": [{"ip": "127.0.0.1"}]}, "proxy": {"spec_id": 2, "count": 2}}

        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "new_slave", module, AccessLayer.STORAGE)
        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "proxy", module, AccessLayer.PROXY)
        ResourceApplyParamBuilder.patch_module_os_params(resource_spec, "missing", module, AccessLayer.PROXY)

        assert resource_spec == {"new_slave": {"hosts": [{"ip": "127.0.0.1"}]}, "proxy": {"spec_id": 2, "count": 2}}

    def test_info_patch_resolves_component_by_cluster_module(self):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.15", ["tlinux-3.2"])
        remote = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.16", ["tlinux-4"])
        ha_cluster = _make_cluster(
            "ha-batch", _make_module("ha-batch", ClusterType.TenDBHA.value, {MachineType.BACKEND.value: (backend, [])})
        )
        spider_cluster = _make_cluster(
            "tendb-batch",
            _make_module("tendb-batch", ClusterType.TenDBCluster.value, {MachineType.REMOTE.value: (remote, [])}),
        )
        infos = [
            {"cluster_ids": [ha_cluster.id], "resource_spec": {"new_slave": {"spec_id": 1, "count": 1}}},
            {"cluster_id": spider_cluster.id, "resource_spec": {"new_slave": {"spec_id": 1, "count": 1}}},
        ]
        builder = ResourceApplyParamBuilder(SimpleNamespace(details={"infos": infos}))

        builder.patch_info_module_os_params("new_slave", AccessLayer.STORAGE)

        patched = builder.ticket_data["infos"]
        assert patched[0]["resource_spec"]["new_slave"]["os_names"] == ["tlinux-3.2"]
        assert patched[1]["resource_spec"]["new_slave"]["os_names"] == ["tlinux-4"]
