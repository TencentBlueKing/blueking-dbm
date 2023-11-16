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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType


class ClusterType(str, StructuredEnum):
    TenDBSingle = EnumField("tendbsingle", _("tendbsingle"))
    TenDBHA = EnumField("tendbha", _("tendbha"))
    TenDBCluster = EnumField("tendbcluster", _("tendbcluster"))

    RedisCluster = EnumField("redis", _("Redis集群"))
    TendisPredixyRedisCluster = EnumField("PredixyRedisCluster", _("Tendisplus集群"))
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

    @classmethod
    def db_type_to_cluster_type(cls, db_type):
        return {
            DBType.InfluxDB: [],
            DBType.MySQL: [cls.TenDBSingle, cls.TenDBHA],
            DBType.TenDBCluster: [cls.TenDBCluster],
            DBType.Redis: [
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
            ],
            DBType.Es: [cls.Es],
            DBType.Kafka: [cls.Kafka],
            DBType.Hdfs: [cls.Hdfs],
            DBType.Pulsar: [cls.Pulsar],
            DBType.MongoDB: [cls.MongoShardedCluster, cls.MongoReplicaSet],
            DBType.Riak: [cls.Riak],
        }.get(db_type)

    @classmethod
    def cluster_type_to_db_type(cls, cluster_type):
        if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
            db_type = DBType.MySQL.value
        elif cluster_type in [
            ClusterType.Es,
            ClusterType.Kafka,
            ClusterType.Hdfs,
            ClusterType.Pulsar,
            ClusterType.Influxdb,
            ClusterType.TenDBCluster,
        ]:
            db_type = cluster_type.lower()
        else:
            db_type = DBType.Redis.value

        return db_type
