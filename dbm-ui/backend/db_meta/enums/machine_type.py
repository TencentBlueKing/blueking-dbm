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

from blue_krill.data_types.enum import EnumField, StructuredEnum


class MachineType(str, StructuredEnum):
    SPIDER = EnumField("spider", _("spider"))
    REMOTE = EnumField("remote", _("remote"))
    PROXY = EnumField("proxy", _("proxy"))
    BACKEND = EnumField("backend", _("backend"))
    SINGLE = EnumField("single", _("single"))

    PREDIXY = EnumField("predixy", _("predixy"))
    TWEMPROXY = EnumField("twemproxy", _("twemproxy"))
    REDIS = EnumField("redis", _("redis"))
    TENDISCACHE = EnumField("tendiscache", _("tendiscache"))
    TENDISSSD = EnumField("tendisssd", _("tendisssd"))
    TENDISPLUS = EnumField("tendisplus", _("tendisplus"))

    ES_DATANODE = EnumField("es_datanode", _("es_datanode"))
    ES_MASTER = EnumField("es_master", _("es_master"))
    ES_CLIENT = EnumField("es_client", _("es_client"))

    BROKER = EnumField("broker", _("broker"))
    ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))

    HDFS_MASTER = EnumField("hdfs_master", _("hdfs_master"))
    HDFS_DATANODE = EnumField("hdfs_datanode", _("hdfs_datanode"))

    MONGOS = EnumField("mongos", _("mongos"))  # mongos
    MONGODB = EnumField("mongodb", _("mongodb"))  # member of shardsvr or replicaset
    MONOG_CONFIG = EnumField("mongo_config", _("mongo_config"))  # member of shardedCluster's configsvr

    INFLUXDB = EnumField("influxdb", _("influxdb"))

    PULSAR_ZOOKEEPER = EnumField("pulsar_zookeeper", _("pulsar_zookeeper"))
    PULSAR_BOOKKEEPER = EnumField("pulsar_bookkeeper", _("pulsar_bookkeeper"))
    PULSAR_BROKER = EnumField("pulsar_broker", _("pulsar_broker"))

    RIAK = EnumField("riak", _("riak"))

    SQLSERVER_SINGLE = EnumField("sqlserver_single", _("sqlserver_single"))
    SQLSERVER_HA = EnumField("sqlserver_ha", _("sqlserver_ha"))
