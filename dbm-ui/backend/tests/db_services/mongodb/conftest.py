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

from backend.db_meta.enums import AccessLayer, ClusterEntryType, ClusterType, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import Spec, city_map
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_meta.models.machine import Machine
from backend.db_meta.models.storage_instance_tuple import StorageInstanceTuple
from backend.db_meta.models.storage_set_dtl import NosqlStorageSetDtl


def get_random_ip():
    """生成随机IP地址"""
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"


@pytest.fixture
def mongodb_bk_biz_id():
    """提供MongoDB测试业务ID"""
    return random.randint(1000, 9999)


@pytest.fixture
def mongodb_module(mongodb_bk_biz_id):
    """创建MongoDB模块用于测试"""
    module = DBModule.objects.create(
        bk_biz_id=mongodb_bk_biz_id,
        db_module_name=get_random_string(6),
        cluster_type=ClusterType.MongoReplicaSet,
    )
    yield module
    module.delete()


@pytest.fixture
def mongodb_city():
    """创建MongoDB测试城市"""
    logic_city = city_map.LogicalCity.objects.create(name=get_random_string(6))
    bk_city = city_map.BKCity.objects.create(
        bk_idc_city_id=random.randint(1000000, 9999999),
        bk_idc_city_name=get_random_string(6),
        logical_city=logic_city,
    )
    yield bk_city
    bk_city.delete()
    logic_city.delete()


@pytest.fixture
def mongodb_spec():
    """创建MongoDB规格"""
    spec = Spec.objects.create(
        spec_id=random.randint(10000, 99999),
        spec_name=f"mongodb_spec_{get_random_string(4)}",
        spec_cluster_type="MongoSharedCluster",
        spec_machine_type=MachineType.MONGODB.value,
        cpu={"max": 8, "min": 8},
        mem={"max": 32, "min": 32},
        storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
        device_class=["S5"],
        enable=True,
    )
    yield spec
    spec.delete()


@pytest.fixture
def mongodb_replicaset_cluster(mongodb_bk_biz_id, mongodb_module, mongodb_city, mongodb_spec):
    """创建MongoDB副本集集群用于测试"""
    db_module_id = mongodb_module.db_module_id
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        alias=f"{cluster_name}_alias",
        cluster_type=ClusterType.MongoReplicaSet,
        immute_domain=f"mongo.{cluster_name}.db",
        bk_biz_id=mongodb_bk_biz_id,
        db_module_id=db_module_id,
        major_version="MongoDB-4.4",
        region="test_region",
    )

    # 创建MongoDB存储节点机器和实例 (副本集：1个Primary + 2个Secondary)
    mongodb_ips = [get_random_ip() for _ in range(3)]
    mongodb_machines = []
    mongodb_instances = []

    for i, ip in enumerate(mongodb_ips):
        machine = Machine.objects.create(
            ip=ip,
            bk_city=mongodb_city,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
            machine_type=MachineType.MONGODB,
            spec_id=mongodb_spec.spec_id,
            spec_config=mongodb_spec.get_spec_info(),
        )
        mongodb_machines.append(machine)

        # 创建MongoDB实例
        instance_role = InstanceRole.MONGO_M1 if i == 0 else InstanceRole.MONGO_BACKUP
        instance = StorageInstance.objects.create(
            machine=machine,
            port=27017,
            cluster_type=ClusterType.MongoReplicaSet,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            instance_role=instance_role,
            status=InstanceStatus.RUNNING.value,
            version="MongoDB-4.4",
        )
        instance.cluster.add(cluster)
        mongodb_instances.append(instance)

    # 创建主从关系
    primary = mongodb_instances[0]
    for secondary in mongodb_instances[1:]:
        StorageInstanceTuple.objects.create(ejector=primary, receiver=secondary)

    # 创建DNS入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=cluster.immute_domain,
    )

    yield cluster

    # 清理数据
    StorageInstanceTuple.objects.filter(ejector__cluster=cluster).delete()
    StorageInstance.objects.filter(cluster=cluster).delete()
    ClusterEntry.objects.filter(cluster=cluster).delete()
    cluster.delete()
    Machine.objects.filter(bk_biz_id=mongodb_bk_biz_id, db_module_id=db_module_id).delete()


@pytest.fixture
def mongodb_sharded_cluster(mongodb_bk_biz_id, mongodb_module, mongodb_city, mongodb_spec):
    """创建MongoDB分片集群用于测试"""
    db_module_id = mongodb_module.db_module_id
    cluster_name = get_random_string(6)
    cluster = Cluster.objects.create(
        name=cluster_name,
        alias=f"{cluster_name}_alias",
        cluster_type=ClusterType.MongoShardedCluster,
        immute_domain=f"mongo.{cluster_name}.db",
        bk_biz_id=mongodb_bk_biz_id,
        db_module_id=db_module_id,
        major_version="MongoDB-4.4",
        region="test_region",
    )

    # 创建Mongos节点 (2个)
    mongos_ips = [get_random_ip() for _ in range(2)]
    mongos_machines = []
    mongos_instances = []

    for ip in mongos_ips:
        machine = Machine.objects.create(
            ip=ip,
            bk_city=mongodb_city,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
            machine_type=MachineType.MONGOS,
            spec_id=mongodb_spec.spec_id,
            spec_config=mongodb_spec.get_spec_info(),
        )
        mongos_machines.append(machine)

        mongos = ProxyInstance.objects.create(
            machine=machine,
            port=27017,
            cluster_type=ClusterType.MongoShardedCluster,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            access_layer=AccessLayer.PROXY,
            status=InstanceStatus.RUNNING.value,
            version="MongoDB-4.4",
        )
        mongos.cluster.add(cluster)
        mongos_instances.append(mongos)

    # 创建ConfigSvr节点 (3个)
    config_ips = [get_random_ip() for _ in range(3)]
    config_machines = []
    config_instances = []

    for i, ip in enumerate(config_ips):
        machine = Machine.objects.create(
            ip=ip,
            bk_city=mongodb_city,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            bk_host_id=int(ipaddress.IPv4Address(ip)),
            machine_type=MachineType.MONOG_CONFIG,
            spec_id=mongodb_spec.spec_id,
            spec_config=mongodb_spec.get_spec_info(),
        )
        config_machines.append(machine)

        instance_role = InstanceRole.MONGO_M1 if i == 0 else InstanceRole.MONGO_BACKUP
        config_inst = StorageInstance.objects.create(
            machine=machine,
            port=27019,
            cluster_type=ClusterType.MongoShardedCluster,
            bk_biz_id=mongodb_bk_biz_id,
            db_module_id=db_module_id,
            instance_role=instance_role,
            status=InstanceStatus.RUNNING.value,
            version="MongoDB-4.4",
        )
        config_inst.cluster.add(cluster)
        config_instances.append(config_inst)

    # 创建ShardSvr节点 (2个分片，每个分片3个节点)
    shard_instances = []
    shard_machines = []
    num_shards = 2
    nodes_per_shard = 3

    for shard_idx in range(num_shards):
        shard_nodes = []
        for node_idx in range(nodes_per_shard):
            ip = get_random_ip()
            machine = Machine.objects.create(
                ip=ip,
                bk_city=mongodb_city,
                bk_biz_id=mongodb_bk_biz_id,
                db_module_id=db_module_id,
                bk_host_id=int(ipaddress.IPv4Address(ip)),
                machine_type=MachineType.MONGODB,
                spec_id=mongodb_spec.spec_id,
                spec_config=mongodb_spec.get_spec_info(),
            )
            shard_machines.append(machine)

            instance_role = InstanceRole.MONGO_M1 if node_idx == 0 else InstanceRole.MONGO_BACKUP
            shard_inst = StorageInstance.objects.create(
                machine=machine,
                port=27018,
                cluster_type=ClusterType.MongoShardedCluster,
                bk_biz_id=mongodb_bk_biz_id,
                db_module_id=db_module_id,
                instance_role=instance_role,
                status=InstanceStatus.RUNNING.value,
                version="MongoDB-4.4",
            )
            shard_inst.cluster.add(cluster)
            shard_nodes.append(shard_inst)

        # 创建分片信息
        seg_range = f"shard_{shard_idx:02d}"
        for node in shard_nodes:
            NosqlStorageSetDtl.objects.create(
                cluster=cluster,
                instance=node,
                seg_range=seg_range,
                bk_biz_id=mongodb_bk_biz_id,
            )

        # 创建主从关系
        primary = shard_nodes[0]
        for secondary in shard_nodes[1:]:
            StorageInstanceTuple.objects.create(ejector=primary, receiver=secondary)

        shard_instances.extend(shard_nodes)

    # 创建DNS入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=cluster.immute_domain,
    )

    yield cluster

    # 清理数据
    NosqlStorageSetDtl.objects.filter(cluster=cluster).delete()
    StorageInstanceTuple.objects.filter(ejector__cluster=cluster).delete()
    ProxyInstance.objects.filter(cluster=cluster).delete()
    StorageInstance.objects.filter(cluster=cluster).delete()
    ClusterEntry.objects.filter(cluster=cluster).delete()
    cluster.delete()
    Machine.objects.filter(bk_biz_id=mongodb_bk_biz_id, db_module_id=db_module_id).delete()
