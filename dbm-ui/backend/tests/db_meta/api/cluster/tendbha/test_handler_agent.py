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
import ipaddress
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.api.cluster.tendbha import (
    add_proxy,
    add_slave,
    add_storage_tuple,
    change_proxy_storage_entry,
    change_storage_cluster_entry,
    cluster_add_storage,
    cluster_remove_storage,
    create,
    create_precheck,
    decommission,
    decommission_precheck,
    reduce_proxy,
    remove_slave,
    remove_storage_tuple,
    scan_cluster,
    switch_single,
    switch_slave,
    switch_storage,
)
from backend.db_meta.api.cluster.tendbha.others import add_slaves, delete_slaves
from backend.db_meta.api.cluster.tendbha.status_flag import status_flag
from backend.db_meta.api.cluster.tendbha.storage_tuple import update_storage_tuple
from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import (
    BKCity,
    Cluster,
    ClusterEntry,
    Machine,
    ProxyInstance,
    StorageInstance,
    StorageInstanceTuple,
)
from backend.tests.mock_data import constant
from backend.tests.mock_data.components import cc

pytestmark = pytest.mark.django_db

# ==================== 测试文件局部常量 ====================
TEST_MASTER_DOMAIN = "test-master.db.com"
TEST_SLAVE_DOMAIN = "test-slave.db.com"
TEST_MASTER_DOMAIN2 = "test-master2.db.com"
TEST_SLAVE_DOMAIN2 = "test-slave2.db.com"
TEST_STORAGE_PORT = 20000
TEST_PROXY_PORT = 10000
TEST_BK_CLOUD_ID = 0

# ==================== Fixture 定义 ====================


@pytest.fixture
def bk_city():
    """获取测试用城市"""
    return BKCity.objects.first()


@pytest.fixture
def master_machine(bk_city):
    """创建主库机器"""
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP)),
        bk_cloud_id=TEST_BK_CLOUD_ID,
    )
    return machine


@pytest.fixture
def slave_machine(bk_city):
    """创建从库机器"""
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP2,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.BACKEND.value,
        bk_city=bk_city,
        access_layer=AccessLayer.STORAGE,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP2)),
        bk_cloud_id=TEST_BK_CLOUD_ID,
    )
    return machine


@pytest.fixture
def proxy_machine_1(bk_city):
    """创建代理机器1"""
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP3,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.PROXY.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP3)),
        bk_cloud_id=TEST_BK_CLOUD_ID,
    )
    return machine


@pytest.fixture
def proxy_machine_2(bk_city):
    """创建代理机器2"""
    machine = Machine.objects.create(
        ip=cc.NORMAL_IP4,
        bk_biz_id=constant.BK_BIZ_ID,
        machine_type=MachineType.PROXY.value,
        bk_city=bk_city,
        access_layer=AccessLayer.PROXY,
        bk_host_id=int(ipaddress.IPv4Address(cc.NORMAL_IP4)),
        bk_cloud_id=TEST_BK_CLOUD_ID,
    )
    return machine


@pytest.fixture
def master_instance(master_machine):
    """创建主库实例"""
    instance = StorageInstance.objects.create(
        machine=master_machine,
        port=TEST_STORAGE_PORT,
        instance_role=InstanceRole.BACKEND_MASTER.value,
        instance_inner_role=InstanceInnerRole.MASTER.value,
        status=InstanceStatus.RUNNING.value,
        phase=InstancePhase.ONLINE.value,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
        is_stand_by=True,
    )
    return instance


@pytest.fixture
def slave_instance(slave_machine):
    """创建从库实例"""
    instance = StorageInstance.objects.create(
        machine=slave_machine,
        port=TEST_STORAGE_PORT,
        instance_role=InstanceRole.BACKEND_SLAVE.value,
        instance_inner_role=InstanceInnerRole.SLAVE.value,
        status=InstanceStatus.RUNNING.value,
        phase=InstancePhase.ONLINE.value,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
        is_stand_by=True,
    )
    return instance


@pytest.fixture
def proxy_instance_1(proxy_machine_1):
    """创建代理实例1"""
    instance = ProxyInstance.objects.create(
        machine=proxy_machine_1,
        port=TEST_PROXY_PORT,
        status=InstanceStatus.RUNNING.value,
        phase=InstancePhase.ONLINE.value,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
    )
    return instance


@pytest.fixture
def proxy_instance_2(proxy_machine_2):
    """创建代理实例2"""
    instance = ProxyInstance.objects.create(
        machine=proxy_machine_2,
        port=TEST_PROXY_PORT,
        status=InstanceStatus.RUNNING.value,
        phase=InstancePhase.ONLINE.value,
        bk_biz_id=constant.BK_BIZ_ID,
        cluster_type=ClusterType.TenDBHA.value,
    )
    return instance


@pytest.fixture
def init_cluster(master_instance, slave_instance, proxy_instance_1, proxy_instance_2):
    """创建包含完整拓扑的 TenDBHA 测试集群"""
    cluster = Cluster.objects.create(
        bk_biz_id=constant.BK_BIZ_ID,
        name=constant.CLUSTER_NAME,
        cluster_type=ClusterType.TenDBHA.value,
        db_module_id=constant.DB_MODULE_ID,
        immute_domain=TEST_MASTER_DOMAIN,
        phase=ClusterPhase.ONLINE.value,
        status=ClusterStatus.NORMAL.value,
        bk_cloud_id=TEST_BK_CLOUD_ID,
        time_zone="+08:00",
        major_version="MySQL-5.7",
        region="",
    )

    # 关联实例
    cluster.storageinstance_set.add(master_instance, slave_instance)
    cluster.proxyinstance_set.add(proxy_instance_1, proxy_instance_2)

    # 设置接入层后端（proxy -> master）
    master_instance.proxyinstance_set.add(proxy_instance_1, proxy_instance_2)

    # 设置主从同步关系
    StorageInstanceTuple.objects.create(ejector=master_instance, receiver=slave_instance)

    # 创建主域名
    master_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS,
        entry=TEST_MASTER_DOMAIN,
        role=ClusterEntryRole.MASTER_ENTRY.value,
    )
    master_entry.proxyinstance_set.add(proxy_instance_1, proxy_instance_2)

    # 创建从域名
    slave_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS,
        entry=TEST_SLAVE_DOMAIN,
        role=ClusterEntryRole.SLAVE_ENTRY.value,
    )
    slave_entry.storageinstance_set.add(slave_instance)

    return cluster


# ==================== 测试类：create_cluster.py ====================


class TestCreatePrecheck:
    """测试 create_precheck 创建前置检查函数"""

    def test_create_precheck_success(self):
        """前置检查通过（无重复集群和域名）"""
        create_precheck(
            bk_biz_id=constant.BK_BIZ_ID,
            name="unique_cluster",
            immute_domain="unique.domain.db",
            db_module_id=constant.DB_MODULE_ID,
            slave_domain="unique-slave.domain.db",
        )
        # 无异常抛出即为通过

    def test_create_precheck_err_with_duplicate_cluster_name(self, init_cluster):
        """集群名已存在时抛出异常"""
        with pytest.raises(DBMetaException):
            create_precheck(
                bk_biz_id=constant.BK_BIZ_ID,
                name=constant.CLUSTER_NAME,
                immute_domain="another.domain.db",
                db_module_id=constant.DB_MODULE_ID,
            )

    def test_create_precheck_err_with_duplicate_domain(self, init_cluster):
        """域名已存在时抛出异常"""
        with pytest.raises(DBMetaException):
            create_precheck(
                bk_biz_id=constant.BK_BIZ_ID,
                name="another_cluster",
                immute_domain=TEST_MASTER_DOMAIN,
                db_module_id=constant.DB_MODULE_ID,
            )

    def test_create_precheck_err_with_duplicate_slave_domain(self, init_cluster):
        """从域名已存在时抛出异常"""
        with pytest.raises(DBMetaException):
            create_precheck(
                bk_biz_id=constant.BK_BIZ_ID,
                name="another_cluster",
                immute_domain="another.domain.db",
                db_module_id=constant.DB_MODULE_ID,
                slave_domain=TEST_SLAVE_DOMAIN,
            )


class TestCreateCluster:
    """测试 create 集群注册函数"""

    def test_create_success(self, master_instance, slave_instance, proxy_instance_1, proxy_instance_2):
        """注册 TenDBHA 集群成功"""
        storages = [
            {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_PORT},
            {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT},
        ]
        proxies = [
            {"ip": cc.NORMAL_IP3, "port": TEST_PROXY_PORT},
            {"ip": cc.NORMAL_IP4, "port": TEST_PROXY_PORT},
        ]

        cluster = create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="new_cluster",
            immute_domain="new-cluster.db.com",
            major_version="MySQL-5.7",
            db_module_id=constant.DB_MODULE_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            time_zone="+08:00",
            region="",
            disaster_tolerance_level="NONE",
            slave_domain="new-cluster-slave.db.com",
            proxies=proxies,
            storages=storages,
            creator="admin",
        )

        assert Cluster.objects.filter(name="new_cluster").exists()
        assert cluster.storageinstance_set.count() == 2
        assert cluster.proxyinstance_set.count() == 2

        # 验证主域名
        assert ClusterEntry.objects.filter(entry="new-cluster.db.com", cluster=cluster).exists()
        master_entry = ClusterEntry.objects.get(entry="new-cluster.db.com", cluster=cluster)
        assert master_entry.proxyinstance_set.count() == 2

        # 验证从域名
        assert ClusterEntry.objects.filter(entry="new-cluster-slave.db.com", cluster=cluster).exists()
        slave_entry = ClusterEntry.objects.get(entry="new-cluster-slave.db.com", cluster=cluster)
        assert slave_entry.storageinstance_set.count() == 1

        # 验证主从同步关系
        assert StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).exists()

        # 验证 db_module_id 已更新
        master_instance.refresh_from_db()
        assert master_instance.db_module_id == constant.DB_MODULE_ID

    def test_create_success_without_slave_domain(
        self, master_instance, slave_instance, proxy_instance_1, proxy_instance_2
    ):
        """不带从域名注册集群成功"""
        storages = [
            {"ip": cc.NORMAL_IP, "port": TEST_STORAGE_PORT},
            {"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT},
        ]
        proxies = [
            {"ip": cc.NORMAL_IP3, "port": TEST_PROXY_PORT},
            {"ip": cc.NORMAL_IP4, "port": TEST_PROXY_PORT},
        ]

        cluster = create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="no_slave_domain_cluster",
            immute_domain="no-slave.db.com",
            major_version="MySQL-5.7",
            db_module_id=constant.DB_MODULE_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            time_zone="+08:00",
            region="",
            disaster_tolerance_level="NONE",
            proxies=proxies,
            storages=storages,
            creator="admin",
        )

        assert Cluster.objects.filter(name="no_slave_domain_cluster").exists()
        # 只有主域名，无从域名
        assert ClusterEntry.objects.filter(cluster=cluster).count() == 1


class TestClusterAddRemoveStorage:
    """测试 cluster_add_storage 和 cluster_remove_storage 函数"""

    def test_cluster_add_storage_success(self, init_cluster, bk_city):
        """向集群添加存储实例成功"""
        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP5,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100001,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        original_count = init_cluster.storageinstance_set.count()
        cluster_add_storage([{"ip": cc.NORMAL_IP5, "port": TEST_STORAGE_PORT, "cluster_id": init_cluster.id}])
        assert init_cluster.storageinstance_set.count() == original_count + 1

    def test_cluster_remove_storage_success(self, init_cluster, slave_instance):
        """从集群移除存储实例成功"""
        original_count = init_cluster.storageinstance_set.count()
        cluster_remove_storage(
            cluster_id=init_cluster.id,
            ip=cc.NORMAL_IP2,
            port=TEST_STORAGE_PORT,
        )
        assert init_cluster.storageinstance_set.count() == original_count - 1


# ==================== 测试类：decommission.py ====================


class TestDecommissionPrecheck:
    """测试 decommission_precheck 下架前置检查函数"""

    def test_decommission_precheck_success(self, init_cluster):
        """无跨集群同步关系时检查通过"""
        decommission_precheck(init_cluster)
        # 无异常抛出即为通过

    def test_decommission_precheck_err_with_cross_cluster_sync(self, init_cluster, bk_city):
        """存在跨集群同步关系时抛出异常"""
        # 创建另一个集群的从库
        other_machine = Machine.objects.create(
            ip=cc.NORMAL_IP6,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100002,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        other_slave = StorageInstance.objects.create(
            machine=other_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        other_cluster = Cluster.objects.create(
            bk_biz_id=constant.BK_BIZ_ID,
            name="other_cluster",
            cluster_type=ClusterType.TenDBHA.value,
            db_module_id=constant.DB_MODULE_ID,
            immute_domain="other.db.com",
            phase=ClusterPhase.ONLINE.value,
            status=ClusterStatus.NORMAL.value,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        other_cluster.storageinstance_set.add(other_slave)

        # 创建跨集群同步关系：当前集群的 master 向其他集群的 slave 同步
        master = init_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        StorageInstanceTuple.objects.create(ejector=master, receiver=other_slave)

        with pytest.raises(DBMetaException):
            decommission_precheck(init_cluster)


class TestDecommission:
    """测试 decommission 集群下架函数"""

    @patch("backend.db_meta.api.cluster.tendbha.decommission.DBPartitionApi")
    @patch("backend.db_meta.api.cluster.tendbha.decommission.DBPrivManagerApi")
    @patch("backend.db_meta.api.cluster.tendbha.decommission.CcManage")
    def test_decommission_success(self, mock_cc_manage, mock_priv_api, mock_partition_api, init_cluster):
        """下架集群成功，验证所有关联数据已清理"""
        mock_cc_manage_instance = MagicMock()
        mock_cc_manage.return_value = mock_cc_manage_instance

        cluster_id = init_cluster.id
        decommission(init_cluster)

        # 验证集群已删除
        assert not Cluster.objects.filter(id=cluster_id).exists()
        # 验证域名已删除
        assert not ClusterEntry.objects.filter(entry=TEST_MASTER_DOMAIN).exists()
        assert not ClusterEntry.objects.filter(entry=TEST_SLAVE_DOMAIN).exists()
        # 验证 CcManage 被调用
        assert mock_cc_manage.called


# ==================== 测试类：storage_tuple.py ====================


class TestStorageTuple:
    """测试 storage_tuple 主从关系操作函数"""

    def test_add_storage_tuple_success(self, master_instance, slave_instance):
        """添加主从同步关系成功"""
        # 清理可能存在的关系
        StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).delete()

        add_storage_tuple(
            master_ip=cc.NORMAL_IP,
            slave_ip=cc.NORMAL_IP2,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            port_list=[TEST_STORAGE_PORT],
        )

        assert StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).count() == 1

    def test_remove_storage_tuple_success(self, master_instance, slave_instance):
        """移除主从同步关系成功"""
        StorageInstanceTuple.objects.create(ejector=master_instance, receiver=slave_instance)

        remove_storage_tuple(
            master_ip=cc.NORMAL_IP,
            slave_ip=cc.NORMAL_IP2,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            port_list=[TEST_STORAGE_PORT],
        )

        assert StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).count() == 0

    def test_update_storage_tuple_success(self, master_instance, slave_instance, bk_city):
        """更新主从同步关系的 ejector 成功"""
        StorageInstanceTuple.objects.create(ejector=master_instance, receiver=slave_instance)

        # 创建新的 master
        new_master_machine = Machine.objects.create(
            ip=cc.NORMAL_IP7,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100003,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_master = StorageInstance.objects.create(
            machine=new_master_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_MASTER.value,
            instance_inner_role=InstanceInnerRole.MASTER.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        update_storage_tuple(
            master_ip=cc.NORMAL_IP,
            new_master_ip=cc.NORMAL_IP7,
            exclude_ips=[],
            bk_cloud_id=TEST_BK_CLOUD_ID,
            port_list=[TEST_STORAGE_PORT],
        )

        # 验证 ejector 已更新为新 master
        assert StorageInstanceTuple.objects.filter(ejector=new_master, receiver=slave_instance).exists()
        # 验证旧关系已不存在
        assert not StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).exists()

    def test_update_storage_tuple_with_exclude_ips(self, master_instance, slave_instance, bk_city):
        """更新主从关系时排除指定 IP"""
        StorageInstanceTuple.objects.create(ejector=master_instance, receiver=slave_instance)

        new_master_machine = Machine.objects.create(
            ip=cc.NORMAL_IP8,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100004,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        StorageInstance.objects.create(
            machine=new_master_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_MASTER.value,
            instance_inner_role=InstanceInnerRole.MASTER.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        # 排除 slave 的 IP，则不应更新
        update_storage_tuple(
            master_ip=cc.NORMAL_IP,
            new_master_ip=cc.NORMAL_IP8,
            exclude_ips=[cc.NORMAL_IP2],
            bk_cloud_id=TEST_BK_CLOUD_ID,
            port_list=[TEST_STORAGE_PORT],
        )

        # 由于 slave IP 被排除，原关系应保持不变
        assert StorageInstanceTuple.objects.filter(ejector=master_instance, receiver=slave_instance).exists()


# ==================== 测试类：switch_storage.py ====================


class TestSwitchStorage:
    """测试 switch_storage 主从迁移切换函数"""

    def test_switch_storage_success(self, init_cluster, bk_city):
        """主从迁移切换成功"""
        # 创建新的目标存储实例
        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP9,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100005,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_storage = StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RESTORING.value,
            phase=InstancePhase.OFFLINE.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_storage)

        switch_storage(
            cluster_id=init_cluster.id,
            target_storage_ip=cc.NORMAL_IP9,
            origin_storage_ip=cc.NORMAL_IP2,
        )

        # 验证新实例状态已更新
        new_storage.refresh_from_db()
        assert new_storage.status == InstanceStatus.RUNNING.value
        assert new_storage.phase == InstancePhase.ONLINE.value

        # 验证旧实例状态已更新
        old_slave = StorageInstance.objects.get(machine__ip=cc.NORMAL_IP2, port=TEST_STORAGE_PORT)
        assert old_slave.status == InstanceStatus.UNAVAILABLE.value
        assert old_slave.phase == InstancePhase.OFFLINE.value

        # 验证旧实例已从集群移除
        assert not init_cluster.storageinstance_set.filter(machine__ip=cc.NORMAL_IP2).exists()

    @patch("backend.db_meta.api.cluster.tendbha.switch_storage.MysqlCCTopoOperator")
    def test_switch_storage_with_role_change(self, mock_topo_operator, init_cluster, bk_city):
        """带角色变更的主从迁移切换成功"""
        mock_topo_instance = MagicMock()
        mock_topo_operator.return_value = mock_topo_instance

        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP10,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100006,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_storage = StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RESTORING.value,
            phase=InstancePhase.OFFLINE.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_storage)

        switch_storage(
            cluster_id=init_cluster.id,
            target_storage_ip=cc.NORMAL_IP10,
            origin_storage_ip=cc.NORMAL_IP2,
            role=InstanceRole.BACKEND_MASTER.value,
        )

        new_storage.refresh_from_db()
        assert new_storage.instance_role == InstanceRole.BACKEND_MASTER.value
        assert new_storage.instance_inner_role == InstanceInnerRole.MASTER.value
        # 验证 MysqlCCTopoOperator 被调用
        mock_topo_instance.transfer_instances_to_cluster_module.assert_called_once()


class TestChangeProxyStorageEntry:
    """测试 change_proxy_storage_entry 代理后端切换函数"""

    def test_change_proxy_storage_entry_success(self, init_cluster, bk_city):
        """代理后端从旧 master 切换到新 master"""
        # 创建新 master
        new_master_machine = Machine.objects.create(
            ip=cc.NORMAL_IP11,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100007,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_master = StorageInstance.objects.create(
            machine=new_master_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_MASTER.value,
            instance_inner_role=InstanceInnerRole.MASTER.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_master)

        change_proxy_storage_entry(
            cluster_id=init_cluster.id,
            master_ip=cc.NORMAL_IP,
            new_master_ip=cc.NORMAL_IP11,
        )

        # 验证 proxy 的后端已切换到新 master
        assert new_master.proxyinstance_set.count() == 2
        old_master = StorageInstance.objects.get(machine__ip=cc.NORMAL_IP, port=TEST_STORAGE_PORT)
        assert old_master.proxyinstance_set.count() == 0


class TestChangeStorageClusterEntry:
    """测试 change_storage_cluster_entry 从域名切换函数"""

    def test_change_storage_cluster_entry_success(self, init_cluster, bk_city):
        """从域名从旧 slave 切换到新 slave"""
        new_slave_machine = Machine.objects.create(
            ip=cc.NORMAL_IP12,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100008,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_slave = StorageInstance.objects.create(
            machine=new_slave_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_slave)

        change_storage_cluster_entry(
            cluster_id=init_cluster.id,
            slave_ip=cc.NORMAL_IP2,
            new_slave_ip=cc.NORMAL_IP12,
        )

        # 验证从域名已绑定到新 slave
        slave_entry = ClusterEntry.objects.get(entry=TEST_SLAVE_DOMAIN, cluster=init_cluster)
        assert slave_entry.storageinstance_set.filter(machine__ip=cc.NORMAL_IP12).exists()
        assert not slave_entry.storageinstance_set.filter(machine__ip=cc.NORMAL_IP2).exists()


# ==================== 测试类：switch_slave.py ====================


class TestSwitchSlave:
    """测试 switch_slave 从库替换函数"""

    def test_switch_slave_success(self, init_cluster, bk_city):
        """从库替换成功"""
        new_slave_machine = Machine.objects.create(
            ip=cc.NORMAL_IP13,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100009,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_slave = StorageInstance.objects.create(
            machine=new_slave_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RESTORING.value,
            phase=InstancePhase.OFFLINE.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_slave)

        switch_slave(
            cluster_id=init_cluster.id,
            target_slave_ip=cc.NORMAL_IP13,
            source_slave_ip=cc.NORMAL_IP2,
            slave_domain=[TEST_SLAVE_DOMAIN],
        )

        # 验证新 slave 状态
        new_slave.refresh_from_db()
        assert new_slave.status == InstanceStatus.RUNNING.value
        assert new_slave.phase == InstancePhase.ONLINE.value
        assert new_slave.is_stand_by is True

        # 验证旧 slave 已从集群移除
        assert not init_cluster.storageinstance_set.filter(machine__ip=cc.NORMAL_IP2).exists()

        # 验证从域名已绑定到新 slave
        slave_entry = ClusterEntry.objects.get(entry=TEST_SLAVE_DOMAIN, cluster=init_cluster)
        assert slave_entry.storageinstance_set.filter(machine__ip=cc.NORMAL_IP13).exists()

    def test_switch_slave_same_ip_rebuild(self, init_cluster):
        """原地重建场景（source 和 target 相同）"""
        # 先将 slave 状态设为异常
        old_slave = init_cluster.storageinstance_set.get(machine__ip=cc.NORMAL_IP2)
        old_slave.status = InstanceStatus.UNAVAILABLE.value
        old_slave.phase = InstancePhase.OFFLINE.value
        old_slave.save()

        switch_slave(
            cluster_id=init_cluster.id,
            target_slave_ip=cc.NORMAL_IP2,
            source_slave_ip=cc.NORMAL_IP2,
            slave_domain=[TEST_SLAVE_DOMAIN],
        )

        # 原地重建不移除集群关系
        old_slave.refresh_from_db()
        assert old_slave.status == InstanceStatus.RUNNING.value
        assert old_slave.phase == InstancePhase.ONLINE.value
        assert init_cluster.storageinstance_set.filter(machine__ip=cc.NORMAL_IP2).exists()


class TestSwitchSingle:
    """测试 switch_single 单节点替换函数"""

    def test_switch_single_success(self, init_cluster, bk_city):
        """单节点替换成功"""
        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP14,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100010,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_storage = StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RESTORING.value,
            phase=InstancePhase.OFFLINE.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )
        init_cluster.storageinstance_set.add(new_storage)

        switch_single(
            cluster_id=init_cluster.id,
            target_orphan_ip=cc.NORMAL_IP14,
            source_orphan_ip=cc.NORMAL_IP2,
            domains=[TEST_SLAVE_DOMAIN],
        )

        new_storage.refresh_from_db()
        assert new_storage.status == InstanceStatus.RUNNING.value
        assert new_storage.phase == InstancePhase.ONLINE.value

        # 验证旧实例已从集群移除
        assert not init_cluster.storageinstance_set.filter(machine__ip=cc.NORMAL_IP2).exists()


class TestAddRemoveSlave:
    """测试 add_slave 和 remove_slave 函数"""

    def test_add_slave_success(self, init_cluster, bk_city):
        """向集群添加 slave 成功"""
        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP15,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100011,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        original_count = init_cluster.storageinstance_set.count()
        add_slave(cluster_id=init_cluster.id, target_slave_ip=cc.NORMAL_IP15)
        assert init_cluster.storageinstance_set.count() == original_count + 1

    def test_remove_slave_success(self, init_cluster):
        """从集群移除 slave 成功"""
        original_count = init_cluster.storageinstance_set.count()
        remove_slave(cluster_id=init_cluster.id, target_slave_ip=cc.NORMAL_IP2)
        assert init_cluster.storageinstance_set.count() == original_count - 1


# ==================== 测试类：switch_proxy.py ====================


class TestAddProxy:
    """测试 add_proxy 添加代理函数"""

    @patch("backend.db_meta.api.cluster.tendbha.switch_proxy.MysqlCCTopoOperator")
    def test_add_proxy_success(self, mock_topo_operator, init_cluster, bk_city):
        """向集群添加新代理成功"""
        mock_topo_instance = MagicMock()
        mock_topo_operator.return_value = mock_topo_instance

        # 创建新代理
        new_proxy_machine = Machine.objects.create(
            ip=cc.NORMAL_IP16,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.PROXY.value,
            bk_city=bk_city,
            access_layer=AccessLayer.PROXY,
            bk_host_id=100012,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        ProxyInstance.objects.create(
            machine=new_proxy_machine,
            port=TEST_PROXY_PORT,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        original_proxy_count = init_cluster.proxyinstance_set.count()
        add_proxy(
            cluster_ids=[init_cluster.id],
            proxy_ip=cc.NORMAL_IP16,
        )

        # 验证代理已添加到集群
        assert init_cluster.proxyinstance_set.count() == original_proxy_count + 1

        # 验证代理已关联到 master 后端
        master = init_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        assert master.proxyinstance_set.filter(machine__ip=cc.NORMAL_IP16).exists()

        # 验证 MysqlCCTopoOperator 被调用
        mock_topo_instance.transfer_instances_to_cluster_module.assert_called_once()


class TestReduceProxy:
    """测试 reduce_proxy 回收代理函数"""

    @patch("backend.db_meta.api.cluster.tendbha.switch_proxy.CcManage")
    def test_reduce_proxy_success(self, mock_cc_manage, init_cluster):
        """回收代理成功"""
        mock_cc_manage_instance = MagicMock()
        mock_cc_manage.return_value = mock_cc_manage_instance

        original_proxy_count = init_cluster.proxyinstance_set.count()
        reduce_proxy(
            cluster_ids=[init_cluster.id],
            origin_proxy_ip=cc.NORMAL_IP3,
        )

        # 验证代理已从集群移除
        assert init_cluster.proxyinstance_set.count() == original_proxy_count - 1
        assert not init_cluster.proxyinstance_set.filter(machine__ip=cc.NORMAL_IP3).exists()


# ==================== 测试类：others.py ====================


class TestAddSlaves:
    """测试 add_slaves 批量添加从库函数"""

    def test_add_slaves_success(self, init_cluster, bk_city):
        """批量添加从库成功"""
        # 创建新 slave 并建立同步关系
        new_machine = Machine.objects.create(
            ip=cc.NORMAL_IP17,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=MachineType.BACKEND.value,
            bk_city=bk_city,
            access_layer=AccessLayer.STORAGE,
            bk_host_id=100013,
            bk_cloud_id=TEST_BK_CLOUD_ID,
        )
        new_slave = StorageInstance.objects.create(
            machine=new_machine,
            port=TEST_STORAGE_PORT,
            instance_role=InstanceRole.BACKEND_SLAVE.value,
            instance_inner_role=InstanceInnerRole.SLAVE.value,
            status=InstanceStatus.RUNNING.value,
            bk_biz_id=constant.BK_BIZ_ID,
            cluster_type=ClusterType.TenDBHA.value,
        )

        # 建立与 master 的同步关系（add_slaves 要求 slave 已有同步关系）
        master = init_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        StorageInstanceTuple.objects.create(ejector=master, receiver=new_slave)

        original_count = init_cluster.storageinstance_set.count()
        add_slaves(init_cluster, [{"ip": cc.NORMAL_IP17, "port": TEST_STORAGE_PORT}])
        assert init_cluster.storageinstance_set.count() == original_count + 1

    def test_add_slaves_err_with_not_match(self, init_cluster):
        """添加不存在的从库时抛出异常"""
        with pytest.raises(Exception, match="not match"):
            add_slaves(init_cluster, [{"ip": "non_exist_ip", "port": 99999}])


class TestDeleteSlaves:
    """测试 delete_slaves 批量删除从库函数"""

    def test_delete_slaves_success(self, init_cluster):
        """批量删除从库成功"""
        original_count = init_cluster.storageinstance_set.count()
        delete_slaves(init_cluster, [{"ip": cc.NORMAL_IP2, "port": TEST_STORAGE_PORT}])
        assert init_cluster.storageinstance_set.count() == original_count - 1

    def test_delete_slaves_err_with_not_match(self, init_cluster):
        """删除不存在的从库时抛出异常"""
        with pytest.raises(Exception, match="not match"):
            delete_slaves(init_cluster, [{"ip": "non_exist_ip", "port": 99999}])


# ==================== 测试类：status_flag.py ====================


class TestStatusFlag:
    """测试 status_flag 集群状态标记函数"""

    def test_status_flag_returns_int(self, init_cluster):
        """获取集群状态标记返回整数"""
        result = status_flag(init_cluster)
        assert isinstance(result, int)


# ==================== 测试类：detail.py ====================


class TestScanCluster:
    """测试 scan_cluster 集群拓扑扫描函数"""

    def test_scan_cluster_returns_graphic(self, init_cluster):
        """扫描集群拓扑返回 Graphic 对象"""
        from backend.db_meta.api.cluster.base.graph import Graphic

        result = scan_cluster(init_cluster)
        assert isinstance(result, Graphic)

    def test_scan_cluster_to_dict(self, init_cluster):
        """扫描集群拓扑可转换为字典"""
        result = scan_cluster(init_cluster)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
