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

from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import city_map
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_meta.models.machine import Machine


def get_random_ip():
    return f"{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"


@pytest.fixture
def bk_biz_id():
    return random.randint(0, 1000)


@pytest.fixture
def dbsingle_machine_ip_list():
    return [get_random_ip()]


@pytest.fixture
def dbha_proxy_ip_list():
    return [get_random_ip() for _ in range(2)]


@pytest.fixture
def dbha_master_ip():
    return get_random_ip()


@pytest.fixture
def dbha_slave_ip():
    return get_random_ip()


@pytest.fixture
def dbsingle_module(bk_biz_id):
    return DBModule.objects.create(
        bk_biz_id=bk_biz_id, db_module_name=get_random_string(6), cluster_type=ClusterType.TenDBSingle
    )


@pytest.fixture
def dbha_module(bk_biz_id):
    return DBModule.objects.create(
        bk_biz_id=bk_biz_id, db_module_name=get_random_string(6), cluster_type=ClusterType.TenDBHA
    )


@pytest.fixture
def dbsingle_cluster(bk_biz_id, dbsingle_module, dbsingle_machine_ip_list):
    db_module_id = dbsingle_module.db_module_id
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        cluster_type=ClusterType.TenDBSingle,
        immute_domain=f"gamedb.{cluster_name}.blueking.db",
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
    )

    logic_city = city_map.LogicalCity.objects.create(name=get_random_string(6))
    bk_city = city_map.BKCity.objects.create(
        bk_idc_city_id=random.randint(0, 1000000), logical_city=logic_city, bk_idc_city_name=get_random_string(6)
    )
    machine1 = Machine.objects.create(
        ip=dbsingle_machine_ip_list[0],
        bk_city=bk_city,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        bk_host_id=int(ipaddress.IPv4Address(dbsingle_machine_ip_list[0])),
    )
    inst1 = StorageInstance.objects.create(
        machine=machine1,
        port=30000,
        cluster_type=ClusterType.TenDBSingle,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
    )
    inst1.cluster.add(cluster)

    return cluster


@pytest.fixture
def dbha_cluster(bk_biz_id, dbha_module, dbha_proxy_ip_list, dbha_master_ip, dbha_slave_ip):
    db_module_id = dbha_module.db_module_id
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"gamedb.{cluster_name}.blueking.db",
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
    )

    logic_city = city_map.LogicalCity.objects.create(name=get_random_string(6))
    bk_city = city_map.BKCity.objects.create(bk_idc_city_id=random.randint(0, 1000000), logical_city=logic_city)
    machine1 = Machine.objects.create(
        ip=dbha_proxy_ip_list[0],
        bk_city=bk_city,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        bk_host_id=int(ipaddress.IPv4Address(dbha_proxy_ip_list[0])),
    )
    machine2 = Machine.objects.create(
        ip=dbha_proxy_ip_list[1],
        bk_city=bk_city,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        bk_host_id=int(ipaddress.IPv4Address(dbha_proxy_ip_list[1])),
    )
    machine3 = Machine.objects.create(
        ip=dbha_master_ip,
        bk_city=bk_city,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        bk_host_id=int(ipaddress.IPv4Address(dbha_master_ip)),
    )
    machine4 = Machine.objects.create(
        ip=dbha_slave_ip,
        bk_city=bk_city,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        bk_host_id=int(ipaddress.IPv4Address(dbha_slave_ip)),
    )

    master = StorageInstance.objects.create(
        machine=machine3,
        port=30000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=bk_biz_id,
        instance_inner_role=InstanceInnerRole.MASTER,
        db_module_id=db_module_id,
    )
    master.cluster.add(cluster)

    slave = StorageInstance.objects.create(
        machine=machine4,
        port=30000,
        cluster_type=ClusterType.TenDBHA,
        status=InstanceStatus.RUNNING.value,
        bk_biz_id=bk_biz_id,
        instance_inner_role=InstanceInnerRole.SLAVE,
        db_module_id=db_module_id,
    )
    slave.cluster.add(cluster)

    proxy1 = ProxyInstance.objects.create(
        machine=machine1,
        port=10000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        status=InstanceStatus.RUNNING.value,
    )
    proxy1.cluster.add(cluster)

    proxy2 = ProxyInstance.objects.create(
        machine=machine2,
        port=10000,
        cluster_type=ClusterType.TenDBHA,
        bk_biz_id=bk_biz_id,
        db_module_id=db_module_id,
        status=InstanceStatus.RUNNING.value,
    )
    proxy2.cluster.add(cluster)

    ClusterEntry.objects.create(
        cluster=cluster, cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    )
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=f"slave-{cluster.immute_domain}",
    )

    return cluster
