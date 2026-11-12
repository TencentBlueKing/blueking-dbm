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
from backend.db_meta.enums import (
    AccessLayer,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    MachineType,
    TenDBClusterSpiderRole,
)
from backend.db_meta.enums.version_phase import VersionPhase
from backend.db_meta.models import BKCity, Cluster, DBModule, Machine, StorageInstance
from backend.db_meta.models.db_version import DBVersion, Distribution, VersionSeries
from backend.db_package.models import Package
from backend.db_services.ipchooser.constants import BkOsType
from backend.flow.consts import MediumEnum
from backend.tests.mock_data import constant
from backend.ticket.builders import BuilderFactory, ResourceApplyParamBuilder
from backend.ticket.constants import TicketType

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


class TestStorageResourceOsParams:
    # 各集群类型存储层在模块版本里对应的组件
    STORAGE_COMPONENT = {
        ClusterType.TenDBSingle.value: MachineType.SINGLE.value,
        ClusterType.TenDBHA.value: MachineType.BACKEND.value,
        ClusterType.TenDBCluster.value: MachineType.REMOTE.value,
    }

    @classmethod
    def _make_storage_cluster(cls, name: str, cluster_type: str, with_version: bool = True) -> Cluster:
        layers = {}
        if with_version:
            storage = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.41", ["tlinux-3.2", "tlinux-4"])
            layers = {cls.STORAGE_COMPONENT[cluster_type]: (storage, [])}
        return _make_cluster(name, _make_module(name, cluster_type, layers))

    @staticmethod
    def _add_master(cluster: Cluster):
        """添加从库要按集群的 master 计算亲和性，集群下需要有一台 master"""
        machine = Machine.objects.create(
            ip="127.0.0.41",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_host_id=41,
            machine_type=MachineType.BACKEND.value,
            access_layer=AccessLayer.STORAGE.value,
            bk_city=BKCity.objects.first(),
        )
        master = StorageInstance.objects.create(
            machine=machine,
            port=20000,
            instance_role=InstanceRole.BACKEND_MASTER.value,
            instance_inner_role=InstanceInnerRole.MASTER.value,
        )
        master.cluster.add(cluster)

    @staticmethod
    def _format(ticket_type: str, role: str, cluster: Cluster) -> dict:
        """按单据实际挂的资源申请 builder 补参，返回该角色的申请参数"""
        info = {
            "cluster_ids": [cluster.id],
            "old_nodes": {"old_slave": []},
            "resource_spec": {role: {"spec_id": 1, "count": 1}},
        }
        resource_builder_cls = BuilderFactory.registry[ticket_type].resource_batch_apply_builder
        builder = resource_builder_cls(SimpleNamespace(details={"infos": [info]}))
        builder.format()
        return builder.ticket_data["infos"][0]["resource_spec"][role]

    @pytest.mark.parametrize(
        "ticket_type, role, cluster_type",
        [
            (TicketType.MYSQL_ADD_SLAVE, "new_slave", ClusterType.TenDBHA.value),
            (TicketType.MYSQL_RESTORE_SLAVE, "new_slave", ClusterType.TenDBHA.value),
            (TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE, "new_slave", ClusterType.TenDBHA.value),
            (TicketType.TENDBCLUSTER_RESTORE_SLAVE, "new_slave", ClusterType.TenDBCluster.value),
            (TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE, "new_slave", ClusterType.TenDBCluster.value),
            (TicketType.MYSQL_MIGRATE_CLUSTER, "backend_group", ClusterType.TenDBHA.value),
            (TicketType.MYSQL_MIGRATE_SINGLE, "bk_new_orphan", ClusterType.TenDBSingle.value),
            (TicketType.TENDBCLUSTER_MIGRATE_CLUSTER, "backend_group", ClusterType.TenDBCluster.value),
            (TicketType.TENDBCLUSTER_NODE_REBALANCE, "backend_group", ClusterType.TenDBCluster.value),
        ],
    )
    def test_storage_tickets_patch_storage_layer_os(self, ticket_type, role, cluster_type):
        cluster = self._make_storage_cluster("storage-os", cluster_type)
        if ticket_type == TicketType.MYSQL_ADD_SLAVE:
            self._add_master(cluster)

        resource_spec = self._format(ticket_type, role, cluster)

        assert resource_spec["os_type"] == BkOsType.LINUX.value
        assert resource_spec["os_names"] == ["tlinux-3.2", "tlinux-4"]

    def test_storage_ticket_keeps_legacy_module_unchanged(self):
        cluster = self._make_storage_cluster("storage-legacy", ClusterType.TenDBHA.value, with_version=False)

        resource_spec = self._format(TicketType.MYSQL_RESTORE_SLAVE, "new_slave", cluster)

        assert "os_type" not in resource_spec
        assert "os_names" not in resource_spec


class TestMysqlProxyResourceOsParams:
    @pytest.mark.parametrize(
        "ticket_type, role, cluster_key",
        [
            (TicketType.MYSQL_PROXY_ADD, "new_proxies", "cluster_ids"),
            (TicketType.MYSQL_PROXY_SWITCH, "target_proxies", "cluster_ids"),
            (TicketType.MYSQL_PROXY_MIGRATE, "target_proxies", "cluster_ids"),
            (TicketType.MYSQL_PROXY_MIGRATE_INS, "target_proxies", "cluster_ids"),
            (TicketType.MYSQL_PROXY_CONF_CHANGE, "target_proxies", "cluster_ids"),
            (TicketType.MYSQL_DBHA_AF_PROXY_REPLACE, "target_proxies", "cluster_ids"),
            (TicketType.MYSQL_PROXY_RESCUE, "new_proxies", "cluster_id"),
        ],
    )
    def test_proxy_tickets_patch_proxy_layer_os(self, ticket_type, role, cluster_key):
        backend = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.21", ["tlinux-3.2"])
        proxy = _make_version(MediumEnum.MySQLProxy.value, "0.82.19.0.0.21", ["tlinux-3.2", "tlinux-4"])
        module = _make_module(
            "proxy-os",
            ClusterType.TenDBHA.value,
            {MachineType.BACKEND.value: (backend, []), MachineType.PROXY.value: (proxy, [])},
        )
        cluster = _make_cluster("proxy-os", module)
        cluster_value = [cluster.id] if cluster_key == "cluster_ids" else cluster.id
        info = {
            cluster_key: cluster_value,
            "old_nodes": {"proxy": []},
            "resource_spec": {role: {"spec_id": 1, "count": 2}},
        }

        resource_builder_cls = BuilderFactory.registry[ticket_type].resource_batch_apply_builder
        builder = resource_builder_cls(SimpleNamespace(details={"infos": [info]}))
        builder.format()

        resource_spec = builder.ticket_data["infos"][0]["resource_spec"][role]
        assert resource_spec["os_type"] == BkOsType.LINUX.value
        assert resource_spec["os_names"] == ["tlinux-3.2", "tlinux-4"]

    def test_proxy_ticket_keeps_legacy_module_unchanged(self):
        legacy = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="proxy-legacy",
            alias_name="proxy-legacy",
            cluster_type=ClusterType.TenDBHA.value,
            **_AUDIT,
        )
        cluster = _make_cluster("proxy-legacy", legacy)
        info = {"cluster_ids": [cluster.id], "resource_spec": {"new_proxies": {"spec_id": 1, "count": 2}}}

        resource_builder_cls = BuilderFactory.registry[TicketType.MYSQL_PROXY_ADD].resource_batch_apply_builder
        builder = resource_builder_cls(SimpleNamespace(details={"infos": [info]}))
        builder.format()

        resource_spec = builder.ticket_data["infos"][0]["resource_spec"]["new_proxies"]
        assert "os_type" not in resource_spec
        assert "os_names" not in resource_spec


class TestTendbSpiderResourceOsParams:
    @staticmethod
    def _make_spider_cluster(name: str, with_version: bool = True) -> Cluster:
        layers = {}
        if with_version:
            remote = _make_version(MediumEnum.MySQL.value, "8.0.32.0.0.31", ["tlinux-3.2"])
            spider = _make_version(MediumEnum.Spider.value, "3.8.5.0.0.31", ["tlinux-3.2", "tlinux-4"])
            layers = {MachineType.REMOTE.value: (remote, []), MachineType.SPIDER.value: (spider, [])}
        return _make_cluster(name, _make_module(name, ClusterType.TenDBCluster.value, layers))

    @staticmethod
    def _format(ticket_type: str, role: str, cluster: Cluster) -> dict:
        """按单据实际挂的资源申请 builder 补参，返回该角色的申请参数"""
        info = {
            "cluster_id": cluster.id,
            "add_spider_role": TenDBClusterSpiderRole.SPIDER_MASTER.value,
            "switch_spider_role": role,
            "spider_old_ip_list": [],
            "old_nodes": {"proxy": []},
            "resource_spec": {role: {"spec_id": 1, "count": 2}},
        }
        resource_builder_cls = BuilderFactory.registry[ticket_type].resource_batch_apply_builder
        builder = resource_builder_cls(SimpleNamespace(details={"infos": [info]}))
        builder.format()
        return builder.ticket_data["infos"][0]["resource_spec"][role]

    @pytest.mark.parametrize(
        "ticket_type, role",
        [
            (TicketType.TENDBCLUSTER_SPIDER_ADD_NODES, "spider_ip_list"),
            (TicketType.TENDBCLUSTER_SPIDER_SLAVE_APPLY, "spider_slave_ip_list"),
            (TicketType.TENDBCLUSTER_SPIDER_LAYER_DR, "spider_master_new_ip_list"),
            (TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES, TenDBClusterSpiderRole.SPIDER_MASTER.value),
            (TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES, TenDBClusterSpiderRole.SPIDER_SLAVE.value),
            (TicketType.MYSQL_DBHA_AF_SPIDER_REPLACE, TenDBClusterSpiderRole.SPIDER_MASTER.value),
            (TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN, TenDBClusterSpiderRole.SPIDER_MASTER.value),
            (TicketType.TENDBCLUSTER_SPIDER_CONF_UP_DOWN, TenDBClusterSpiderRole.SPIDER_SLAVE.value),
        ],
    )
    def test_spider_tickets_patch_spider_layer_os(self, ticket_type, role):
        cluster = self._make_spider_cluster("spider-os")

        resource_spec = self._format(ticket_type, role, cluster)

        assert resource_spec["os_type"] == BkOsType.LINUX.value
        assert resource_spec["os_names"] == ["tlinux-3.2", "tlinux-4"]

    @pytest.mark.parametrize(
        "ticket_type, role",
        [
            (TicketType.TENDBCLUSTER_SPIDER_ADD_NODES, "spider_ip_list"),
            (TicketType.TENDBCLUSTER_SPIDER_SWITCH_NODES, TenDBClusterSpiderRole.SPIDER_MASTER.value),
        ],
    )
    def test_spider_ticket_keeps_legacy_module_unchanged(self, ticket_type, role):
        cluster = self._make_spider_cluster("spider-legacy", with_version=False)

        resource_spec = self._format(ticket_type, role, cluster)

        assert "os_type" not in resource_spec
        assert "os_names" not in resource_spec


class TestMigrateUpgradeResourceOsParams:
    """迁移升级按单据选择的介质包 pkg_id 约束操作系统，与模块是否绑定版本无关"""

    @staticmethod
    def _make_package(pkg_type: str, permit_os_type: str, permit_os: list) -> Package:
        return Package.objects.create(
            name=f"{pkg_type}-upgrade.tar.gz",
            version="8.0",
            pkg_type=pkg_type,
            db_type=DBType.MySQL.value,
            path="/tmp/upgrade",
            size=1,
            md5="abc",
            enable=True,
            permit_os=permit_os,
            permit_os_type=permit_os_type,
            **_AUDIT,
        )

    @staticmethod
    def _format(ticket_type: str, role: str, cluster_type: str, package: Package) -> dict:
        """在未绑定版本的存量模块集群上提单，返回该角色的申请参数"""
        legacy = DBModule.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            db_module_name="upgrade-legacy",
            alias_name="upgrade-legacy",
            cluster_type=cluster_type,
            **_AUDIT,
        )
        cluster = _make_cluster("upgrade-legacy", legacy)
        cluster_key = "cluster_ids" if ticket_type == TicketType.MYSQL_MIGRATE_UPGRADE else "cluster_id"
        cluster_value = [cluster.id] if cluster_key == "cluster_ids" else cluster.id
        info = {
            cluster_key: cluster_value,
            "pkg_id": package.id,
            "old_nodes": {},
            "resource_spec": {role: {"spec_id": 1, "count": 1}},
        }
        resource_builder_cls = BuilderFactory.registry[ticket_type].resource_batch_apply_builder
        builder = resource_builder_cls(SimpleNamespace(details={"infos": [info]}))
        builder.format()
        return builder.ticket_data["infos"][0]["resource_spec"][role]

    @pytest.mark.parametrize(
        "ticket_type, role, cluster_type, pkg_type",
        [
            (TicketType.MYSQL_MIGRATE_UPGRADE, "backend_group", ClusterType.TenDBHA.value, MediumEnum.MySQL.value),
            (
                TicketType.TENDBCLUSTER_MIGRATE_UPGRADE,
                "backend_group",
                ClusterType.TenDBCluster.value,
                MediumEnum.MySQL.value,
            ),
            (
                TicketType.TENDBCLUSTER_SPIDER_UPGRADE,
                "spider_master",
                ClusterType.TenDBCluster.value,
                MediumEnum.Spider.value,
            ),
            (
                TicketType.TENDBCLUSTER_SPIDER_UPGRADE,
                "spider_slave",
                ClusterType.TenDBCluster.value,
                MediumEnum.Spider.value,
            ),
        ],
    )
    def test_upgrade_tickets_patch_package_os(self, ticket_type, role, cluster_type, pkg_type):
        package = self._make_package(pkg_type, BkOsType.LINUX.value, ["tlinux-3.2", "tlinux-4"])

        resource_spec = self._format(ticket_type, role, cluster_type, package)

        assert resource_spec["os_type"] == BkOsType.LINUX.value
        assert resource_spec["os_names"] == ["tlinux-3.2", "tlinux-4"]

    def test_unrestricted_package_only_sets_os_type(self):
        package = self._make_package(MediumEnum.MySQL.value, BkOsType.LINUX.value, [])

        resource_spec = self._format(
            TicketType.MYSQL_MIGRATE_UPGRADE, "backend_group", ClusterType.TenDBHA.value, package
        )

        assert resource_spec["os_type"] == BkOsType.LINUX.value
        assert "os_names" not in resource_spec

    def test_package_without_os_type_keeps_unchanged(self):
        package = self._make_package(MediumEnum.MySQL.value, "", ["tlinux-3.2"])

        resource_spec = self._format(
            TicketType.MYSQL_MIGRATE_UPGRADE, "backend_group", ClusterType.TenDBHA.value, package
        )

        assert "os_type" not in resource_spec
        assert "os_names" not in resource_spec
