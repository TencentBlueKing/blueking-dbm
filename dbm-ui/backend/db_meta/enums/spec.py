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
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from blue_krill.data_types.enum import EnumField, StructuredEnum

# 兼容原来的字段，spec_cluster_type就是db_type
SpecClusterType = DBType


class SpecMachineType(str, StructuredEnum):
    PROXY = EnumField("proxy", _("proxy"))
    BACKEND = EnumField("backend", _("backend"))

    # redis主从、redis集群的后端规格同tendis cache一致
    TendisTwemproxyRedisInstance = EnumField("TwemproxyRedisInstance", _("TendisCache集群"))
    TendisPredixyTendisplusCluster = EnumField("PredixyTendisplusCluster", _("Tendisplus存储版集群"))
    TwemproxyTendisSSDInstance = EnumField("TwemproxyTendisSSDInstance", _("TendisSSD集群"))

    # RedisCluster这个Key不参与规格过滤，只在部署方案的时候生效
    TendisPredixyRedisCluster = EnumField("PredixyRedisCluster", _("RedisCluster集群"))

    ES_DATANODE = EnumField("es_datanode", _("es_datanode"))
    ES_MASTER = EnumField("es_master", _("es_master"))
    ES_CLIENT = EnumField("es_client", _("es_client"))

    BROKER = EnumField("broker", _("broker"))
    ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))

    HDFS_MASTER = EnumField("hdfs_master", _("hdfs_master"))
    HDFS_DATANODE = EnumField("hdfs_datanode", _("hdfs_datanode"))

    PULSAR_ZOOKEEPER = EnumField("pulsar_zookeeper", _("pulsar_zookeeper"))
    PULSAR_BOOKKEEPER = EnumField("pulsar_bookkeeper", _("pulsar_bookkeeper"))
    PULSAR_BROKER = EnumField("pulsar_broker", _("pulsar_broker"))

    RIAK = EnumField("riak", _("riak"))

    SQLSERVER = EnumField("sqlserver", _("sqlserver"))

    MONGOS = EnumField("mongos", _("mongos"))
    MONGODB = EnumField("mongodb", _("mongodb"))
    MONOG_CONFIG = EnumField("mongo_config", _("mongo_config"))

    DORIS_FOLLOWER = EnumField("doris_follower", _("doris_follower"))
    DORIS_OBSERVER = EnumField("doris_observer", _("doris_observer"))
    DORIS_BACKEND = EnumField("doris_backend", _("doris_backend"))
