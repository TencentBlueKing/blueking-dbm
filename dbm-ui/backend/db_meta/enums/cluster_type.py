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

from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE, DBType
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class ClusterType(StrStructuredEnum):
    TenDBSingle = EnumField("tendbsingle", _("MySQL单节点集群"))
    TenDBHA = EnumField("tendbha", _("MySQL高可用集群"))
    TenDBCluster = EnumField("tendbcluster", _("TendbCluster集群"))
    # 仅用于TBinlogDumper实例的管控
    TBinlogDumper = EnumField("tbinlogdumper", _("TBinlogDumper"))
    # MySQL DTS 集群
    MySQLDTS = EnumField("mysqldts", _("MySQLDTS"))

    RedisCluster = EnumField("redis", _("Redis"))
    TendisPredixyRedisCluster = EnumField("PredixyRedisCluster", _("RedisCluster集群"))
    TendisPredixyTendisplusCluster = EnumField("PredixyTendisplusCluster", _("Tendisplus存储版集群"))
    TendisPredixyTendisplusInstance = EnumField("PredixyTendisplusInstance", _("TendisPlus 标准版"))
    TendisTwemproxyRedisInstance = EnumField("TwemproxyRedisInstance", _("TendisCache集群"))
    TwemproxyTendisSSDInstance = EnumField("TwemproxyTendisSSDInstance", _("TendisSSD集群"))
    TendisTwemproxyTendisplusIns = EnumField("TwemproxyTendisplusInstance", _("Tendis存储版集群"))
    TendisRedisInstance = EnumField("RedisInstance", _("RedisCache主从版"))
    TendisTendisSSDInstance = EnumField("TendisSSDInstance", _("TendisSSD主从版"))
    TendisTendisplusInsance = EnumField("TendisplusInstance", _("Tendisplus主从版"))
    TendisRedisCluster = EnumField("RedisCluster", _("RedisCluster集群"))
    TendisTendisplusCluster = EnumField("TendisplusCluster", _("TendisplusCluster集群"))

    #  GetTendisType 获取redis类型,返回RedisInstance or TendisplusInstance or TendisSSDInstance
    TendisplusInstance = EnumField("TendisplusInstance", _("Tendisplus存储版集群"))
    RedisInstance = EnumField("RedisInstance", _("TendisCache集群"))
    TendisSSDInstance = EnumField("TendisSSDInstance", _("TendisSSD集群"))

    Es = EnumField("es", _("ES集群"))
    Kafka = EnumField("kafka", _("Kafka集群"))
    Hdfs = EnumField("hdfs", _("Hdfs集群"))
    Influxdb = EnumField("influxdb", _("Influxdb实例"))
    Pulsar = EnumField("pulsar", _("Pulsar集群"))
    Doris = EnumField("doris", _("Doris集群"))
    Vm = EnumField("vm", _("vm集群"))

    Dbmon = EnumField("dbmon", _("redis监控"))

    MongoReplicaSet = EnumField("MongoReplicaSet", _("Mongo副本集"))
    MongoShardedCluster = EnumField("MongoShardedCluster", _("Mongo分片集群"))

    Riak = EnumField("riak", _("Riak集群"))
    SqlserverSingle = EnumField("sqlserver_single", _("sqlserver单节点版"))
    SqlserverHA = EnumField("sqlserver_ha", _("sqlserver主从版"))

    OraclePrimaryStandby = EnumField("oracle_primary_standby", _("oracle主从版"))
    OracleSingleNone = EnumField("oracle_single_none", _("oracle单节点版"))

    # k8s集群 HA/Single 拆分
    K8sSurrealdbHa = EnumField("k8s_surrealdb_ha", _("k8s SurrealDB集群版"))
    K8sSurrealdbSingle = EnumField("k8s_surrealdb_single", _("k8s SurrealDB单机版"))
    K8sVictoriametricsHa = EnumField("k8s_victoriametrics_ha", _("k8s VictoriaMetrics集群版"))
    K8sRisingwaveHa = EnumField("k8s_risingwave_ha", _("k8s Risingwave集群版"))
    K8sGreptimedbHa = EnumField("k8s_greptimedb_ha", _("k8s GreptimeDB集群版"))
    K8sMilvusHa = EnumField("k8s_milvus_ha", _("k8s Milvus集群版"))
    K8sQdrantHa = EnumField("k8s_qdrant_ha", _("k8s Qdrant集群版"))

    @classmethod
    def db_type_cluster_types_map(cls) -> Dict:
        """
        :return: key为数据库类型的字符串，value为群类型列表
        """
        return {
            DBType.InfluxDB.value: [ClusterType.Influxdb],
            DBType.MySQL.value: [cls.TenDBSingle, cls.TenDBHA, cls.MySQLDTS],
            DBType.TenDBCluster.value: [cls.TenDBCluster],
            DBType.Redis.value: [
                cls.RedisCluster,
                cls.TendisPredixyRedisCluster,
                cls.TendisPredixyTendisplusCluster,
                cls.TendisPredixyTendisplusInstance,
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
            DBType.Doris.value: [cls.Doris],
            DBType.Vm.value: [cls.Vm],
            DBType.Oracle.value: [cls.OraclePrimaryStandby, cls.OracleSingleNone],
            DBType.K8sSurrealdb.value: [cls.K8sSurrealdbHa, cls.K8sSurrealdbSingle],
            DBType.K8sVictoriametrics.value: [cls.K8sVictoriametricsHa],
            DBType.K8sRisingwave.value: [cls.K8sRisingwaveHa],
            DBType.K8sMilvus.value: [cls.K8sMilvusHa],
            DBType.K8sQdrant.value: [cls.K8sQdrantHa],
            DBType.K8sGreptimedb.value: [cls.K8sGreptimedbHa],
        }

    @classmethod
    def db_type_to_cluster_types(cls, db_type: str) -> List[str]:
        """
        根据数据库类型获取数据库集群类型列表
        """
        db_type_cluster_types_map = cls.db_type_cluster_types_map()
        return db_type_cluster_types_map.get(db_type)

    @classmethod
    def k8s_container_cluster_type_values(cls) -> frozenset:
        """K8s 容器类集群的 cluster_type 取值（与扁平化后的 DBType 一一对应）。"""
        return frozenset(
            t.value
            for t in (
                cls.K8sSurrealdbHa,
                cls.K8sSurrealdbSingle,
                cls.K8sVictoriametricsHa,
                cls.K8sRisingwaveHa,
                cls.K8sMilvusHa,
                cls.K8sQdrantHa,
                cls.K8sGreptimedbHa,
            )
        )

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
            cls.TendisPredixyTendisplusInstance,
            cls.TendisTwemproxyRedisInstance,
            cls.TwemproxyTendisSSDInstance,
            cls.TendisTwemproxyTendisplusIns,
            cls.TendisRedisInstance,
            cls.TendisTendisSSDInstance,
            cls.TendisTendisplusInsance,
            cls.TendisRedisCluster,
            cls.TendisTendisplusCluster,
        ]

    @classmethod
    def is_mongodb(cls, cluster_type: str):
        """is_mongodb 判断是否为Mongo集群类型"""
        return cluster_type in cls.db_type_cluster_types_map()[DBType.MongoDB.value]

    @classmethod
    def is_redis_cluster_type(cls, cluster_type: str):
        """is_redis 判断是否为Redis集群类型"""
        return cluster_type in cls.db_type_cluster_types_map()[DBType.Redis.value]

    @classmethod
    def is_ssd_redis(cls, cluster_type: str):
        """is_ssd_redis 判断是否为SSD Redis集群类型. 关键字为SSD,TendisPlus"""
        return cluster_type in [
            cls.TwemproxyTendisSSDInstance.value,
            cls.TendisTendisSSDInstance.value,
            cls.TendisPredixyTendisplusCluster.value,
            cls.TendisPredixyTendisplusInstance.value,
            cls.TendisTwemproxyTendisplusIns.value,
        ]

    @classmethod
    def is_memory_redis(cls, cluster_type: str):
        """is_memory_redis 判断是否为内存Redis集群类型"""
        return cluster_type in [
            cls.TendisTwemproxyRedisInstance.value,
            cls.RedisInstance.value,
            cls.TendisPredixyRedisCluster.value,
            cls.TendisRedisInstance.value,
            cls.TendisRedisCluster.value,
        ]

    @classmethod
    def get_domain_prefix_map(cls):
        """集群域名不带模块的信息的域名前缀， 新增集群类型是需加上"""
        return {
            cls.TwemproxyTendisSSDInstance.value: "ssd",
            cls.TendisPredixyRedisCluster.value: "rediscluster",
            cls.TendisTwemproxyRedisInstance.value: "cache",
            cls.TendisTwemproxyTendisplusIns.value: "tendisplus",
            cls.TendisPredixyTendisplusCluster.value: "tendisplus",
            cls.TendisPredixyTendisplusInstance.value: "tendisplus",
            cls.TendisRedisInstance.value: "ins",
            cls.TenDBCluster.value: "spider",
            cls.MongoReplicaSet.value: "m1",
            cls.MongoShardedCluster.value: "mongos",
            cls.Es.value: "es",
            cls.Hdfs.value: "hdfs",
            cls.Pulsar.value: "pulsar",
            cls.Kafka.value: "kafka",
            cls.Doris.value: "doris",
            cls.K8sQdrantHa.value: "qdrant",
            cls.K8sSurrealdbSingle: "surrealdb",
            cls.K8sSurrealdbHa: "surrealdb",
        }

    @classmethod
    def get_domain_template_map(cls):
        """集群域名带模型信息的域名模板映射， 新增集群类型时需加上"""

        return {
            ClusterType.TenDBHA: MASTER_DOMAIN_INITIAL_VALUE,
            ClusterType.TenDBSingle: MASTER_DOMAIN_INITIAL_VALUE,
            ClusterType.SqlserverHA: MASTER_DOMAIN_INITIAL_VALUE,
            ClusterType.SqlserverSingle: MASTER_DOMAIN_INITIAL_VALUE,
            ClusterType.Riak: "riak.{cluster_name}-{db_module_name}.{db_app_abbr}.db",
        }
