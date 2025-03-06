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
from backend.db_meta.enums import AccessLayer, ClusterType, InstanceInnerRole, InstanceRole, MachineType

MachineTypeAccessLayerMap = {
    MachineType.SPIDER: AccessLayer.PROXY,
    MachineType.REMOTE: AccessLayer.STORAGE,
    MachineType.PROXY: AccessLayer.PROXY,
    MachineType.BACKEND: AccessLayer.STORAGE,
    MachineType.SINGLE: AccessLayer.STORAGE,
    MachineType.TENDISPLUS: AccessLayer.STORAGE,
    MachineType.TENDISCACHE: AccessLayer.STORAGE,
    MachineType.TENDISSSD: AccessLayer.STORAGE,
    MachineType.REDIS: AccessLayer.STORAGE,
    MachineType.PREDIXY: AccessLayer.PROXY,
    MachineType.TWEMPROXY: AccessLayer.PROXY,
    MachineType.ES_DATANODE: AccessLayer.STORAGE,
    MachineType.ES_MASTER: AccessLayer.STORAGE,
    MachineType.ES_CLIENT: AccessLayer.STORAGE,
    MachineType.BROKER: AccessLayer.STORAGE,
    MachineType.ZOOKEEPER: AccessLayer.STORAGE,
    MachineType.HDFS_MASTER: AccessLayer.STORAGE,
    MachineType.HDFS_DATANODE: AccessLayer.STORAGE,
    MachineType.MONGOS: AccessLayer.PROXY,
    MachineType.MONGODB: AccessLayer.STORAGE,
    MachineType.MONOG_CONFIG: AccessLayer.STORAGE,
    MachineType.PULSAR_BROKER: AccessLayer.STORAGE,
    MachineType.PULSAR_BOOKKEEPER: AccessLayer.STORAGE,
    MachineType.PULSAR_ZOOKEEPER: AccessLayer.STORAGE,
    MachineType.INFLUXDB: AccessLayer.STORAGE,
    MachineType.RIAK: AccessLayer.STORAGE,
    MachineType.SQLSERVER_SINGLE: AccessLayer.STORAGE,
    MachineType.SQLSERVER_HA: AccessLayer.STORAGE,
    MachineType.DORIS_FOLLOWER: AccessLayer.STORAGE,
    MachineType.DORIS_OBSERVER: AccessLayer.STORAGE,
    MachineType.DORIS_BACKEND: AccessLayer.STORAGE,
    MachineType.VM_STORAGE: AccessLayer.STORAGE,
    MachineType.VM_INSERT: AccessLayer.STORAGE,
    MachineType.VM_SELECT: AccessLayer.STORAGE,
    MachineType.VM_AUTH: AccessLayer.STORAGE,
}

ClusterTypeMachineTypeDefine = {
    ClusterType.TenDBSingle: [MachineType.SINGLE],
    ClusterType.TenDBHA: [MachineType.PROXY, MachineType.BACKEND],
    ClusterType.TenDBCluster: [MachineType.SPIDER, MachineType.REMOTE],
    ClusterType.TendisRedisInstance: [MachineType.TENDISCACHE],
    ClusterType.TendisPredixyRedisCluster: [MachineType.PREDIXY, MachineType.TENDISCACHE],
    ClusterType.TendisPredixyTendisplusCluster: [MachineType.PREDIXY, MachineType.TENDISPLUS],
    ClusterType.TendisTwemproxyRedisInstance: [MachineType.TWEMPROXY, MachineType.TENDISCACHE],
    ClusterType.TwemproxyTendisSSDInstance: [MachineType.TWEMPROXY, MachineType.TENDISSSD],
    ClusterType.TendisTwemproxyTendisplusIns: [MachineType.TWEMPROXY, MachineType.TENDISPLUS],
    ClusterType.TendisTendisplusInsance: [MachineType.TENDISPLUS],
    ClusterType.TendisRedisCluster: [MachineType.TENDISCACHE],
    ClusterType.RedisCluster: [MachineType.TENDISCACHE],
    ClusterType.TendisTendisplusCluster: [MachineType.TENDISPLUS],
    ClusterType.Es: [MachineType.ES_CLIENT, MachineType.ES_DATANODE, MachineType.ES_MASTER],
    ClusterType.Kafka: [MachineType.BROKER, MachineType.ZOOKEEPER],
    ClusterType.Hdfs: [MachineType.HDFS_MASTER, MachineType.HDFS_DATANODE],
    ClusterType.MongoReplicaSet: [MachineType.MONGODB],
    ClusterType.MongoShardedCluster: [MachineType.MONGODB, MachineType.MONGOS, MachineType.MONOG_CONFIG],
    ClusterType.Pulsar: [MachineType.PULSAR_BROKER, MachineType.PULSAR_BOOKKEEPER, MachineType.PULSAR_ZOOKEEPER],
    ClusterType.Influxdb: [MachineType.INFLUXDB],
    ClusterType.Riak: [MachineType.RIAK],
    ClusterType.SqlserverSingle: [MachineType.SQLSERVER_SINGLE],
    ClusterType.SqlserverHA: [MachineType.SQLSERVER_HA],
    ClusterType.Doris: [MachineType.DORIS_BACKEND, MachineType.DORIS_FOLLOWER, MachineType.DORIS_OBSERVER],
    ClusterType.TBinlogDumper: [MachineType.TBinlogDumper],
    ClusterType.Vm: [MachineType.VM_STORAGE, MachineType.VM_SELECT, MachineType.VM_INSERT, MachineType.VM_AUTH],
}

ClusterMachineAccessTypeDefine = {
    ClusterType.TendisPredixyRedisCluster: {
        AccessLayer.PROXY: MachineType.PREDIXY,
        AccessLayer.STORAGE: MachineType.REDIS,
    },
    ClusterType.TendisPredixyTendisplusCluster: {
        AccessLayer.PROXY: MachineType.PREDIXY,
        AccessLayer.STORAGE: MachineType.TENDISPLUS,
    },
    ClusterType.TendisTwemproxyRedisInstance: {
        AccessLayer.PROXY: MachineType.TWEMPROXY,
        AccessLayer.STORAGE: MachineType.TENDISCACHE,
    },
    ClusterType.TwemproxyTendisSSDInstance: {
        AccessLayer.PROXY: MachineType.TWEMPROXY,
        AccessLayer.STORAGE: MachineType.TENDISSSD,
    },
    ClusterType.TendisTwemproxyTendisplusIns: {
        AccessLayer.PROXY: MachineType.TWEMPROXY,
        AccessLayer.STORAGE: MachineType.TENDISPLUS,
    },
    ClusterType.TendisRedisInstance: {
        AccessLayer.STORAGE: MachineType.TENDISCACHE,
    },
    ClusterType.TendisTendisplusInsance: {
        AccessLayer.STORAGE: MachineType.TENDISPLUS,
    },
    ClusterType.TendisRedisCluster: {
        AccessLayer.STORAGE: MachineType.REDIS,
    },
    ClusterType.TendisTendisplusCluster: {
        AccessLayer.STORAGE: MachineType.TENDISPLUS,
    },
    ClusterType.MongoReplicaSet: {
        AccessLayer.STORAGE: MachineType.MONGODB,
    },
    ClusterType.MongoShardedCluster: {
        AccessLayer.PROXY: MachineType.MONGOS,
        AccessLayer.CONFIG: MachineType.MONOG_CONFIG,
        AccessLayer.STORAGE: MachineType.MONGODB,
    },
    ClusterType.TenDBSingle: {
        AccessLayer.STORAGE: MachineType.SINGLE,
    },
    ClusterType.TenDBHA: {
        AccessLayer.PROXY: MachineType.PROXY,
        AccessLayer.STORAGE: MachineType.BACKEND,
    },
    ClusterType.TenDBCluster: {
        AccessLayer.PROXY: MachineType.SPIDER,
        AccessLayer.STORAGE: MachineType.REMOTE,
    },
    ClusterType.Riak: {
        AccessLayer.STORAGE: MachineType.RIAK,
    },
}

MachineTypeInstanceRoleMap = {
    MachineType.BACKEND: [
        InstanceRole.BACKEND_MASTER,
        InstanceRole.BACKEND_REPEATER,
        InstanceRole.BACKEND_SLAVE,
    ],
    MachineType.REMOTE: [
        InstanceRole.REMOTE_MASTER,
        InstanceRole.REMOTE_REPEATER,
        InstanceRole.REMOTE_SLAVE,
    ],
    MachineType.SINGLE: [InstanceRole.ORPHAN],
    MachineType.TENDISCACHE: [
        InstanceRole.REDIS_SLAVE,
        InstanceRole.REDIS_MASTER,
    ],
    MachineType.REDIS: [
        InstanceRole.REDIS_SLAVE,
        InstanceRole.REDIS_MASTER,
    ],
    MachineType.TENDISSSD: [
        InstanceRole.REDIS_SLAVE,
        InstanceRole.REDIS_MASTER,
    ],
    MachineType.TENDISPLUS: [
        InstanceRole.REDIS_SLAVE,
        InstanceRole.REDIS_MASTER,
    ],
    MachineType.ES_DATANODE: [InstanceRole.ES_DATANODE_HOT, InstanceRole.ES_DATANODE_COLD],
    MachineType.ES_MASTER: [InstanceRole.ES_MASTER],
    MachineType.ES_CLIENT: [InstanceRole.ES_CLIENT],
    MachineType.BROKER: [
        InstanceRole.BROKER,
        InstanceRole.ZOOKEEPER,
    ],
    MachineType.ZOOKEEPER: [InstanceRole.ZOOKEEPER, InstanceRole.BROKER],
    MachineType.HDFS_MASTER: [
        InstanceRole.HDFS_ZOOKEEPER,
        InstanceRole.HDFS_JOURNAL_NODE,
        InstanceRole.HDFS_NAME_NODE,
    ],
    MachineType.HDFS_DATANODE: [InstanceRole.HDFS_DATA_NODE],
    MachineType.MONGODB: [
        InstanceRole.MONGO_M1,
        InstanceRole.MONGO_M2,
        InstanceRole.MONGO_M3,
        InstanceRole.MONGO_M4,
        InstanceRole.MONGO_M5,
        InstanceRole.MONGO_M6,
        InstanceRole.MONGO_M7,
        InstanceRole.MONGO_M8,
        InstanceRole.MONGO_M9,
        InstanceRole.MONGO_M10,
        InstanceRole.MONGO_BACKUP,
    ],
    MachineType.MONOG_CONFIG: [
        InstanceRole.MONGO_M1,
        InstanceRole.MONGO_M2,
        InstanceRole.MONGO_M3,
        InstanceRole.MONGO_M4,
        InstanceRole.MONGO_M5,
        InstanceRole.MONGO_M6,
        InstanceRole.MONGO_M7,
        InstanceRole.MONGO_M8,
        InstanceRole.MONGO_M9,
        InstanceRole.MONGO_M10,
        InstanceRole.MONGO_BACKUP,
    ],
    MachineType.PULSAR_ZOOKEEPER: [InstanceRole.PULSAR_ZOOKEEPER],
    MachineType.PULSAR_BOOKKEEPER: [InstanceRole.PULSAR_BOOKKEEPER],
    MachineType.PULSAR_BROKER: [InstanceRole.PULSAR_BROKER],
    MachineType.INFLUXDB: [InstanceRole.INFLUXDB],
    MachineType.RIAK: [InstanceRole.RIAK_NODE],
    # MachineType.SPIDER: [InstanceRole.SPIDER_MASTER,InstanceRole.SPIDER_SLAVE]
    MachineType.SQLSERVER_SINGLE: [InstanceRole.ORPHAN],
    MachineType.SQLSERVER_HA: [
        InstanceRole.BACKEND_MASTER,
        InstanceRole.BACKEND_REPEATER,
        InstanceRole.BACKEND_SLAVE,
    ],
    MachineType.DORIS_BACKEND: [InstanceRole.DORIS_BACKEND_HOT, InstanceRole.DORIS_BACKEND_COLD],
    MachineType.DORIS_FOLLOWER: [InstanceRole.DORIS_FOLLOWER],
    MachineType.DORIS_OBSERVER: [InstanceRole.DORIS_OBSERVER],
    MachineType.VM_STORAGE: [InstanceRole.VM_STORAGE],
    MachineType.VM_INSERT: [InstanceRole.VM_INSERT],
    MachineType.VM_SELECT: [InstanceRole.VM_SELECT],
    MachineType.VM_AUTH: [InstanceRole.VM_AUTH],
}

InstanceRoleInstanceInnerRoleMap = {
    InstanceRole.ORPHAN: InstanceInnerRole.ORPHAN,
    InstanceRole.BACKEND_MASTER: InstanceInnerRole.MASTER,
    InstanceRole.BACKEND_SLAVE: InstanceInnerRole.SLAVE,
    InstanceRole.BACKEND_REPEATER: InstanceInnerRole.REPEATER,
    InstanceRole.REMOTE_MASTER: InstanceInnerRole.MASTER,
    InstanceRole.REMOTE_SLAVE: InstanceInnerRole.SLAVE,
    InstanceRole.REMOTE_REPEATER: InstanceInnerRole.REPEATER,
    InstanceRole.REDIS_SLAVE: InstanceInnerRole.SLAVE,
    InstanceRole.REDIS_MASTER: InstanceInnerRole.MASTER,
    InstanceRole.ES_MASTER: InstanceInnerRole.ORPHAN,
    InstanceRole.ES_DATANODE_HOT: InstanceInnerRole.ORPHAN,
    InstanceRole.ES_DATANODE_COLD: InstanceInnerRole.ORPHAN,
    InstanceRole.ES_CLIENT: InstanceInnerRole.ORPHAN,
    InstanceRole.BROKER: InstanceInnerRole.ORPHAN,
    InstanceRole.ZOOKEEPER: InstanceInnerRole.ORPHAN,
    InstanceRole.HDFS_NAME_NODE: InstanceInnerRole.ORPHAN,
    InstanceRole.HDFS_JOURNAL_NODE: InstanceInnerRole.ORPHAN,
    InstanceRole.HDFS_ZOOKEEPER: InstanceInnerRole.ORPHAN,
    InstanceRole.HDFS_DATA_NODE: InstanceInnerRole.ORPHAN,
    InstanceRole.MONGO_M1: InstanceInnerRole.MASTER,
    InstanceRole.MONGO_M2: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M3: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M4: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M5: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M6: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M7: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M8: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M9: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_M10: InstanceInnerRole.SLAVE,
    InstanceRole.MONGO_BACKUP: InstanceInnerRole.SLAVE,
    InstanceRole.PULSAR_BROKER: InstanceInnerRole.ORPHAN,
    InstanceRole.PULSAR_BOOKKEEPER: InstanceInnerRole.ORPHAN,
    InstanceRole.PULSAR_ZOOKEEPER: InstanceInnerRole.ORPHAN,
    InstanceRole.INFLUXDB: InstanceInnerRole.ORPHAN,
    InstanceRole.RIAK_NODE: InstanceInnerRole.ORPHAN,
    InstanceRole.DORIS_FOLLOWER: InstanceInnerRole.ORPHAN,
    InstanceRole.DORIS_OBSERVER: InstanceInnerRole.ORPHAN,
    InstanceRole.DORIS_BACKEND_COLD: InstanceInnerRole.ORPHAN,
    InstanceRole.DORIS_BACKEND_HOT: InstanceInnerRole.ORPHAN,
    InstanceRole.VM_STORAGE: InstanceInnerRole.ORPHAN,
    InstanceRole.VM_INSERT: InstanceInnerRole.ORPHAN,
    InstanceRole.VM_SELECT: InstanceInnerRole.ORPHAN,
    InstanceRole.VM_AUTH: InstanceInnerRole.ORPHAN,
}


def machine_type_to_cluster_type(machine_type: MachineType) -> ClusterType:
    for cluster_type in ClusterTypeMachineTypeDefine:
        if machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
            return cluster_type
