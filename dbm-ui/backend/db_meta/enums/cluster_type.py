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


class ClusterType(str, StructuredEnum):
    TenDBSingle = EnumField("tendbsingle", _("tendbsingle"))
    TenDBHA = EnumField("tendbha", _("tendbha"))
    TenDBCluster = EnumField("tendbcluster", _("tendbcluster"))

    RedisCluster = EnumField("redis", _("Redis集群"))
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

    Es = EnumField("es", _("ES集群"))
    Kafka = EnumField("kafka", _("Kafka集群"))
    Hdfs = EnumField("hdfs", _("Hdfs集群"))
    Influxdb = EnumField("influxdb", _("Influxdb实例"))
    Pulsar = EnumField("pulsar", _("Pulsar集群"))

    MongoReplicaSet = EnumField("MongoReplicaSet", _("Mongo副本集"))
    MongoShardedCluster = EnumField("MongoShardedCluster", _("Mongo分片集群"))

    Riak = EnumField("riak", _("Riak集群"))
