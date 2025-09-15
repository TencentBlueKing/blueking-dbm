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
import random

import pytest
from django.utils.crypto import get_random_string

from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryRole,
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import city_map
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import CLBEntryDetail, ClusterEntry, PolarisEntryDetail
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_meta.models.machine import Machine
from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple
from backend.db_meta.models.tag import Tag
from backend.tests.mock_data import constant


def get_random_ip():
    """生成随机IP地址"""
    return f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"


@pytest.fixture
def bk_biz_id():
    """提供随机的业务ID用于测试"""
    return random.randint(0, 1000)


@pytest.fixture
def dbha_module(bk_biz_id):
    """创建DBHA模块用于测试"""
    return DBModule.objects.create(
        bk_biz_id=bk_biz_id, db_module_name=get_random_string(6), cluster_type=ClusterType.TenDBHA
    )


@pytest.fixture
def dbha_cluster(bk_biz_id, dbha_module):
    """创建完整的DBHA集群用于测试，包含机器、存储实例、代理实例和集群入口"""
    db_module_id = dbha_module.db_module_id
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"gamedb.{cluster_name}.blueking.db",
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
    )

    # 创建逻辑城市和城市
    logic_city = city_map.LogicalCity.objects.create(name=get_random_string(6))
    bk_city = city_map.BKCity.objects.create(bk_idc_city_id=random.randint(0, 1000000), logical_city=logic_city)

    # 创建机器IP
    proxy_ips = [get_random_ip() for _ in range(2)]
    master_ip = get_random_ip()
    slave_ip = get_random_ip()

    # 创建机器对象
    machines = []
    for ip in proxy_ips + [master_ip, slave_ip]:
        machine = Machine.objects.create(
            ip=ip,
            bk_city=bk_city,
            bk_biz_id=bk_biz_id,
            db_module_id=db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
        )
        machines.append(machine)

    # 创建主存储实例
    master = StorageInstance.objects.create(
        machine=machines[2],  # master_ip对应的机器
        port=30000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=bk_biz_id,
        instance_inner_role=InstanceInnerRole.MASTER,
        db_module_id=db_module_id,
    )
    master.cluster.add(cluster)

    # 创建从存储实例
    slave = StorageInstance.objects.create(
        machine=machines[3],  # slave_ip对应的机器
        port=30000,
        cluster_type=ClusterType.TenDBHA,
        status=InstanceStatus.RUNNING.value,
        bk_biz_id=bk_biz_id,
        instance_inner_role=InstanceInnerRole.SLAVE,
        db_module_id=db_module_id,
    )
    slave.cluster.add(cluster)

    # 创建代理实例
    for machine in machines[:2]:
        proxy = ProxyInstance.objects.create(
            machine=machine,
            port=10000,
            cluster_type=ClusterType.TenDBHA,
            bk_biz_id=bk_biz_id,
            db_module_id=db_module_id,
            status=InstanceStatus.RUNNING.value,
        )
        proxy.cluster.add(cluster)

    # 创建集群入口
    ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    )

    return cluster


@pytest.fixture
def dbha_cluster_with_tuple(dbha_cluster, bk_biz_id):
    """创建带有主从关系的DBHA集群，用于测试主从关系相关功能"""
    # 获取master和slave实例
    master = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.MASTER).first()
    slave = StorageInstance.objects.filter(cluster=dbha_cluster, instance_inner_role=InstanceInnerRole.SLAVE).first()

    if master and slave:
        # 创建主从关系
        StorageInstanceTuple.objects.create(ejector=master, receiver=slave)

    return dbha_cluster


@pytest.fixture
def test_bk_biz_id():
    """提供测试业务ID"""
    return constant.BK_BIZ_ID


@pytest.fixture
def test_cluster_module(test_bk_biz_id):
    """创建测试集群模块"""
    module, created = DBModule.objects.get_or_create(
        db_module_id=constant.DB_MODULE_ID,
        defaults={
            "bk_biz_id": test_bk_biz_id,
            "db_module_name": "test_module",
            "cluster_type": ClusterType.TenDBHA,
        },
    )
    yield module
    # 只在创建时删除
    if created:
        module.delete()


@pytest.fixture
def test_city():
    """创建测试城市"""
    logic_city = city_map.LogicalCity.objects.create(name="测试城市")
    bk_city = city_map.BKCity.objects.create(
        bk_idc_city_id=random.randint(1000000, 9999999),
        bk_idc_city_name="测试城市",
        logical_city=logic_city,
    )
    yield bk_city
    bk_city.delete()
    logic_city.delete()


@pytest.fixture
def test_cluster_with_entries(test_bk_biz_id, test_cluster_module, test_city):
    """创建带有多种访问入口的测试集群"""
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        alias=f"{cluster_name}_alias",
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"test.{cluster_name}.db",
        bk_biz_id=test_bk_biz_id,
        db_module_id=test_cluster_module.db_module_id,
        major_version="MySQL-5.7",
        region="test_region",
    )

    # 创建机器和实例
    proxy_ips = [get_random_ip() for _ in range(2)]
    master_ip = get_random_ip()
    slave_ip = get_random_ip()

    machines = []
    for ip in proxy_ips + [master_ip, slave_ip]:
        machine = Machine.objects.create(
            ip=ip,
            bk_city=test_city,
            bk_biz_id=test_bk_biz_id,
            db_module_id=test_cluster_module.db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
            machine_type=MachineType.BACKEND,
            access_layer=AccessLayer.PROXY if ip in proxy_ips else AccessLayer.STORAGE,
        )
        machines.append(machine)

    # 创建存储实例
    master = StorageInstance.objects.create(
        machine=machines[2],
        port=20000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=test_bk_biz_id,
        instance_inner_role=InstanceInnerRole.MASTER,
        instance_role=InstanceRole.BACKEND_MASTER,
        db_module_id=test_cluster_module.db_module_id,
        status=InstanceStatus.RUNNING.value,
        version="MySQL-5.7",
    )
    master.cluster.add(cluster)

    slave = StorageInstance.objects.create(
        machine=machines[3],
        port=20000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=test_bk_biz_id,
        instance_inner_role=InstanceInnerRole.SLAVE,
        instance_role=InstanceRole.BACKEND_SLAVE,
        db_module_id=test_cluster_module.db_module_id,
        status=InstanceStatus.RUNNING.value,
        version="MySQL-5.7",
    )
    slave.cluster.add(cluster)

    # 创建代理实例
    for machine in machines[:2]:
        proxy = ProxyInstance.objects.create(
            machine=machine,
            port=10000,
            admin_port=10001,
            cluster_type=ClusterType.TenDBHA,
            bk_biz_id=test_bk_biz_id,
            access_layer=AccessLayer.PROXY,
            db_module_id=test_cluster_module.db_module_id,
            status=InstanceStatus.RUNNING.value,
            version="latest",
        )
        proxy.cluster.add(cluster)

    # 创建DNS入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=cluster.immute_domain,
        role=ClusterEntryRole.MASTER_ENTRY.value,
    )

    # 创建从域名入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=f"slave.{cluster.immute_domain}",
        role=ClusterEntryRole.SLAVE_ENTRY.value,
    )

    # 创建CLB入口
    clb_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLB.value,
        entry="clb.test.db",
        role=ClusterEntryRole.MASTER_ENTRY.value,
    )
    CLBEntryDetail.objects.create(
        entry=clb_entry,
        clb_ip="1.1.1.100",
        clb_id="lb-12345",
        listener_id="lbl-12345",
        clb_region="ap-shanghai",
        clb_port=10000,
    )

    # 创建CLB DNS入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLBDNS.value,
        entry="clb-dns.test.db",
        role=ClusterEntryRole.MASTER_ENTRY.value,
        forward_to=clb_entry,
    )

    # 创建Polaris入口
    polaris_entry = ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.POLARIS.value,
        entry="polaris.test.db",
        role=ClusterEntryRole.MASTER_ENTRY.value,
    )
    PolarisEntryDetail.objects.create(
        entry=polaris_entry,
        polaris_name="test_polaris",
        polaris_l5="123456:65535",
        polaris_token="test_token",
        alias_token="alias_token",
    )

    yield cluster

    # 清理数据 - 需要按照外键关系的逆序删除
    # 1. 先删除实例（实例可能引用集群）
    ProxyInstance.objects.filter(cluster=cluster).delete()
    StorageInstance.objects.filter(cluster=cluster).delete()

    # 2. 删除集群入口 - 需要先删除带有forward_to的entry（如CLBDNS），然后再删除被指向的entry（如CLB）
    # 先删除所有带forward_to的ClusterEntry
    ClusterEntry.objects.filter(cluster=cluster, forward_to__isnull=False).delete()
    # 再删除其他所有ClusterEntry（会自动CASCADE删除CLBEntryDetail和PolarisEntryDetail）
    ClusterEntry.objects.filter(cluster=cluster).delete()

    # 3. 删除集群
    cluster.delete()

    # 4. 删除机器（在集群删除后）
    Machine.objects.filter(bk_biz_id=test_bk_biz_id, db_module_id=test_cluster_module.db_module_id).delete()


@pytest.fixture
def test_cluster_with_tags(test_cluster_with_entries):
    """创建带有标签的测试集群"""
    cluster = test_cluster_with_entries

    # 创建标签
    tag1 = Tag.objects.create(key="env", value="test")
    tag2 = Tag.objects.create(key="team", value="dba")

    cluster.tags.add(tag1, tag2)

    yield cluster

    # 清理标签
    cluster.tags.clear()
    tag1.delete()
    tag2.delete()


@pytest.fixture
def test_temporary_cluster(test_bk_biz_id, test_cluster_module, test_city):
    """创建临时集群用于测试"""
    cluster_name = get_random_string(6)
    # 临时集群名称格式：原集群名_日期_ticket_id
    temp_cluster = Cluster.objects.create(
        name=cluster_name,
        alias="source_cluster-20231225-12345",
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"temp.{cluster_name}.db",
        bk_biz_id=test_bk_biz_id,
        db_module_id=test_cluster_module.db_module_id,
        major_version="MySQL-5.7",
    )

    # 添加临时标签（系统标签需要is_builtin=True和bk_biz_id=0）
    temp_tag = Tag.objects.create(key="temporary", value="1", is_builtin=True, bk_biz_id=0)
    temp_cluster.tags.add(temp_tag)

    # 创建对应的Ticket和Flow以便创建ClusterOperateRecord
    from backend.ticket.constants import FlowType, TicketStatus, TicketType
    from backend.ticket.models import Flow, Ticket

    ticket = Ticket.objects.create(
        id=12345,
        bk_biz_id=test_bk_biz_id,
        ticket_type=TicketType.MYSQL_ROLLBACK_CLUSTER,
        status=TicketStatus.SUCCEEDED,
    )

    flow = Flow.objects.create(
        ticket=ticket,
        flow_type=FlowType.INNER_FLOW,
    )

    from backend.ticket.models import ClusterOperateRecord

    operate_record = ClusterOperateRecord.objects.create(
        cluster_id=temp_cluster.id,
        ticket=ticket,
        flow=flow,
    )

    yield temp_cluster

    # 清理数据
    operate_record.delete()
    flow.delete()
    ticket.delete()
    temp_cluster.tags.clear()
    temp_tag.delete()
    temp_cluster.delete()


@pytest.fixture
def test_multiple_clusters(test_bk_biz_id, test_cluster_module, test_city):
    """创建多个测试集群用于批量查询测试"""
    clusters = []
    machines = []

    for i in range(3):
        cluster_name = f"test_cluster_{i}"
        cluster = Cluster.objects.create(
            name=cluster_name,
            alias=f"{cluster_name}_alias",
            cluster_type=ClusterType.TenDBHA,
            immute_domain=f"{cluster_name}.test.db",
            bk_biz_id=test_bk_biz_id,
            db_module_id=test_cluster_module.db_module_id,
            major_version="MySQL-5.7",
            region="test_region",
        )
        clusters.append(cluster)

        # 为每个集群创建实例
        master_ip = get_random_ip()
        machine = Machine.objects.create(
            ip=master_ip,
            bk_city=test_city,
            bk_biz_id=test_bk_biz_id,
            db_module_id=test_cluster_module.db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(master_ip)),
            machine_type=MachineType.BACKEND,
        )
        machines.append(machine)

        storage = StorageInstance.objects.create(
            machine=machine,
            port=20000,
            cluster_type=ClusterType.TenDBHA,
            bk_biz_id=test_bk_biz_id,
            instance_inner_role=InstanceInnerRole.MASTER,
            instance_role=InstanceRole.BACKEND_MASTER,
            db_module_id=test_cluster_module.db_module_id,
            status=InstanceStatus.RUNNING.value,
        )
        storage.cluster.add(cluster)

        # 创建DNS入口
        ClusterEntry.objects.create(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS.value,
            entry=cluster.immute_domain,
        )

    yield clusters

    # 清理数据
    for cluster in clusters:
        ClusterEntry.objects.filter(cluster=cluster).delete()
        StorageInstance.objects.filter(cluster=cluster).delete()
        cluster.delete()

    for machine in machines:
        machine.delete()
