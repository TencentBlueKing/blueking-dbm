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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from blue_krill.data_types.enum import EnumField, StructuredEnum


class ClusterType(str, StructuredEnum):
    TenDBSingle = EnumField("tendbsingle", _("tendbsingle"))
    TenDBHA = EnumField("tendbha", _("tendbha"))
    TenDBCluster = EnumField("tendbcluster", _("tendbcluster"))

    RedisCluster = EnumField("redis", _("Redis"))
    TendisPredixyRedisCluster = EnumField("PredixyRedisCluster", _("Redis集群"))
    TendisPredixyTendisplusCluster = EnumField("PredixyTendisplusCluster", _("Tendisplus存储版集群"))
    TendisTwemproxyRedisInstance = EnumField("TwemproxyRedisInstance", _("TendisCache集群"))
    TwemproxyTendisSSDInstance = EnumField("TwemproxyTendisSSDInstance", _("TendisSSD集群"))
    TendisTwemproxyTendisplusIns = EnumField("TwemproxyTendisplusInstance", _("Tendis存储版集群"))
    TendisRedisInstance = EnumField("RedisInstance", _("RedisCache主从版"))
    TendisTendisSSDInstance = EnumField("TendisSSDInstance", _("TendisSSD主从版"))
    TendisTendisplusInsance = EnumField("TendisplusInstance", _("Tendisplus主从版"))
    TendisRedisCluster = EnumField("RedisCluster", _("RedisCluster集群"))
    TendisTendisplusCluster = EnumField("TendisplusCluster", _("TendisplusCluster集群"))

    #  GetTendisType 获取redis类型,返回RedisInstance or TendisplusInstance or TendisSSDInstance
    TendisplusInstance = EnumField("TendisplusInstance", _("Tendisplus存储版集群 GetTendisType 获取redis类型值"))
    RedisInstance = EnumField("RedisInstance", _("TendisCache集群 GetTendisType 获取redis类型值"))
    TendisSSDInstance = EnumField("TendisSSDInstance", _("TendisSSD集群 GetTendisType 获取redis类型值"))

    Es = EnumField("es", _("ES集群"))
    Kafka = EnumField("kafka", _("Kafka集群"))
    Hdfs = EnumField("hdfs", _("Hdfs集群"))
    Influxdb = EnumField("influxdb", _("Influxdb实例"))
    Pulsar = EnumField("pulsar", _("Pulsar集群"))
    Dbmon = EnumField("dbmon", _("redis监控"))

    MongoReplicaSet = EnumField("MongoReplicaSet", _("Mongo副本集"))
    MongoShardedCluster = EnumField("MongoShardedCluster", _("Mongo分片集群"))

    Riak = EnumField("riak", _("Riak集群"))

    SqlserverSingle = EnumField("sqlserver_single", _("sqlserver单节点版"))
    SqlserverHA = EnumField("sqlserver_ha", _("sqlserver主从版"))

    @classmethod
    def db_type_cluster_types_map(cls) -> Dict[str, List]:
        """
        :return: key为数据库类型的字符串，value为群类型列表
        """
        return {
            DBType.InfluxDB.value: [ClusterType.Influxdb],
            DBType.MySQL.value: [cls.TenDBSingle, cls.TenDBHA],
            DBType.TenDBCluster.value: [cls.TenDBCluster],
            DBType.Redis.value: [
                cls.RedisCluster,
                cls.TendisPredixyRedisCluster,
                cls.TendisPredixyTendisplusCluster,
                cls.TendisTwemproxyRedisInstance,
                cls.TwemproxyTendisSSDInstance,
                cls.TendisTwemproxyTendisplusIns,
                cls.TendisRedisInstance,
                cls.TendisTendisSSDInstance,
                cls.TendisTendisplusInsance,
                cls.TendisRedisCluster,
                cls.TendisTendisplusCluster,
                cls.TendisplusInstance,
                cls.RedisInstance,
                cls.TendisSSDInstance,
            ],
            DBType.Es.value: [cls.Es],
            DBType.Kafka.value: [cls.Kafka],
            DBType.Hdfs.value: [cls.Hdfs],
            DBType.Pulsar.value: [cls.Pulsar],
            DBType.MongoDB.value: [cls.MongoShardedCluster, cls.MongoReplicaSet],
            DBType.Riak.value: [cls.Riak],
            DBType.Sqlserver.value: [cls.SqlserverHA, cls.SqlserverSingle],
        }

    @classmethod
    def db_type_to_cluster_types(cls, db_type: str) -> List[str]:
        """
        根据数据库类型获取数据库集群类型列表
        """
        db_type_cluster_types_map = cls.db_type_cluster_types_map()
        return db_type_cluster_types_map.get(db_type)

    @classmethod
    def cluster_type_to_db_type(cls, cluster_type):
        for db_type, cluster_types in cls.db_type_cluster_types_map().items():
            if cluster_type in cluster_types:
                return db_type
        raise ValueError(f"cluster_type:{cluster_type} dose not define db type")

    @classmethod
    def redis_cluster_types(cls):
        return [
            cls.RedisCluster,
            cls.TendisPredixyRedisCluster,
            cls.TendisPredixyTendisplusCluster,
            cls.TendisTwemproxyRedisInstance,
            cls.TwemproxyTendisSSDInstance,
            cls.TendisTwemproxyTendisplusIns,
            cls.TendisRedisInstance,
            cls.TendisTendisSSDInstance,
            cls.TendisTendisplusInsance,
            cls.TendisRedisCluster,
            cls.TendisTendisplusCluster,
        ]
