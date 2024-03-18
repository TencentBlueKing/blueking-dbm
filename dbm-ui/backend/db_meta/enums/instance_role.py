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


class InstanceRole(str, StructuredEnum):
    # 单节点
    ORPHAN = EnumField("orphan", _("orphan"))

    # 主备
    BACKEND_MASTER = EnumField("backend_master", _("backend_master"))
    BACKEND_REPEATER = EnumField("backend_repeater", _("backend_repeater"))
    BACKEND_SLAVE = EnumField("backend_slave", _("backend_slave"))

    # tendbcluster 集群
    REMOTE_MASTER = EnumField("remote_master", _("remote_master"))
    REMOTE_REPEATER = EnumField("remote_repeater", _("remote_repeater"))
    REMOTE_SLAVE = EnumField("remote_slave", _("remote_slave"))

    REDIS_PROXY = EnumField("proxy", _("redis_proxy"))
    REDIS_MASTER = EnumField("redis_master", _("redis_master"))
    REDIS_SLAVE = EnumField("redis_slave", _("redis_slave"))

    ES_DATANODE_HOT = EnumField("es_datanode_hot", _("es_datanode_hot"))
    ES_DATANODE_COLD = EnumField("es_datanode_cold", _("es_datanode_cold"))
    ES_MASTER = EnumField("es_master", _("es_master"))
    ES_CLIENT = EnumField("es_client", _("es_client"))

    # kafka
    BROKER = EnumField("broker", _("broker"))
    ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))

    HDFS_NAME_NODE = EnumField("hdfs_namenode", _("hdfs_namenode"))
    HDFS_ZOOKEEPER = EnumField("hdfs_zookeeper", _("hdfs_zookeeper"))
    HDFS_JOURNAL_NODE = EnumField("hdfs_journalnode", _("hdfs_journalnode"))
    HDFS_DATA_NODE = EnumField("hdfs_datanode", _("hdfs_datanode"))

    INFLUXDB = EnumField("influxdb", _("influxdb"))

    PULSAR_BOOKKEEPER = EnumField("pulsar_bookkeeper", _("pulsar_bookkeeper"))
    PULSAR_ZOOKEEPER = EnumField("pulsar_zookeeper", _("pulsar_zookeeper"))
    PULSAR_BROKER = EnumField("pulsar_broker", _("pulsar_broker"))

    MONGO_M1 = EnumField("mongo_m1", _("mongo_m1"))
    MONGO_M2 = EnumField("mongo_m2", _("mongo_m2"))
    MONGO_M3 = EnumField("mongo_m3", _("mongo_m3"))
    MONGO_M4 = EnumField("mongo_m4", _("mongo_m4"))
    MONGO_M5 = EnumField("mongo_m5", _("mongo_m5"))
    MONGO_M6 = EnumField("mongo_m6", _("mongo_m6"))
    MONGO_M7 = EnumField("mongo_m7", _("mongo_m7"))
    MONGO_M8 = EnumField("mongo_m8", _("mongo_m8"))
    MONGO_M9 = EnumField("mongo_m9", _("mongo_m9"))
    MONGO_M10 = EnumField("mongo_m10", _("mongo_m10"))
    MONGO_BACKUP = EnumField("mongo_backup", _("mongo_backup"))

    RIAK_NODE = EnumField("riak_node", _("riak_node"))


class TenDBClusterSpiderRole(str, StructuredEnum):
    # 主集群的接入层
    SPIDER_MASTER = EnumField("spider_master", _("spider_master"))
    # 从集群的接入层
    SPIDER_SLAVE = EnumField("spider_slave", _("spider_slave"))
    # 运维节点
    SPIDER_MNT = EnumField("spider_mnt", _("spider_mnt"))
    SPIDER_SLAVE_MNT = EnumField("spider_slave_mnt", _("spider_slave_mnt"))
