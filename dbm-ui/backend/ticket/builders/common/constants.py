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

ES_MASTER_NEED = 3

HDFS_DATANODE_MIN = 2
HDFS_NAMENODE_NEED = 2
HDFS_ZK_JN_NEED = 3

KAFKA_ZOOKEEPER_NEED = 3
KAFKA_BROKER_MIN = 1

PULSAR_BOOKKEEPER_MIN = 2
PULSAR_ZOOKEEPER_NEED = 3
PULSAR_BROKER_MIN = 1
PULSAR_REPLICATION_NUM_MIN = 2

REDIS_PROXY_MIN = 2

MYSQL_BINLOG_ROLLBACK = "/home/mysql/dba-toolkit/mysqlbinlog_rollback"

MYSQL_CHECKSUM_TABLE = "checksum_history"


class BigDataRole(object):
    class Es(str, StructuredEnum):
        HOT = EnumField("hot", _("hot"))
        COLD = EnumField("cold", _("cold"))
        CLIENT = EnumField("client", _("client"))
        MASTER = EnumField("master", _("master"))

    class Hdfs(str, StructuredEnum):
        DATANODE = EnumField("datanode", _("datanode"))
        NAMENODE = EnumField("namenode", _("namenode"))
        # 目前来说ZooKeeper/JournalNode的单据参数角色是zookeeper
        ZK_JN = EnumField("zookeeper", _("zookeeper"))

    class Kafka(str, StructuredEnum):
        ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))
        BROKER = EnumField("broker", _("broker"))

    class Pulsar(str, StructuredEnum):
        BOOKKEEPER = EnumField("bookkeeper", _("bookkeeper"))
        ZOOKEEPER = EnumField("zookeeper", _("zookeeper"))
        BROKER = EnumField("broker", _("broker"))


class RedisRole(str, StructuredEnum):
    MASTER = EnumField("master", _("master"))
    SLAVE = EnumField("slave", _("slave"))
    PROXY = EnumField("proxy", _("proxy"))


class MySQLBackupSource(str, StructuredEnum):
    """
    库备份源的类型
    """

    LOCAL = EnumField("local", _("本地"))
    REMOTE = EnumField("remote", _("远程"))


class MySQLChecksumTicketMode(str, StructuredEnum):
    """
    数据校验后修复执行类型
    """

    AUTO = EnumField("auto", _("自动修复"))
    MANUAL = EnumField("manual", _("人工确认"))


class MySQLDataRepairTriggerMode(str, StructuredEnum):
    """
    数据修复触发类型
    """

    MANUAL = EnumField("manual", _("手动提单修复"))
    ROUTINE = EnumField("routine", _("例行校验修复"))


class FixpointRollbackType(str, StructuredEnum):
    """
    定点回档类型
    """

    REMOTE_AND_TIME = EnumField("REMOTE_AND_TIME", _("远程备份 + 时间"))
    REMOTE_AND_BACKUPID = EnumField("REMOTE_AND_BACKUPID", _("远程备份 + backupid"))
    LOCAL_AND_TIME = EnumField("LOCAL_AND_TIME", _("本地备份 + 时间"))
    LOCAL_AND_BACKUPID = EnumField("LOCAL_AND_BACKUPID", _("本地备份 + backupid"))
