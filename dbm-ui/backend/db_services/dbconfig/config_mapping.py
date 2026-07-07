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

from backend.components.dbconfig.constants import ConfFile, ConfType
from backend.db_meta.enums import ClusterType

# conf_file 中依赖版本号的动态占位符
SPIDER_VERSION = "spider_version"
DB_VERSION = "db_version"

# 集群版本在模块配置文件中
CLUSTER_VERSION_MODULE = [ClusterType.TenDBCluster, ClusterType.SqlserverHA, ClusterType.SqlserverSingle]

# 组件配置项
COMPONENT_CONFIG_ITEMS = {
    # ----- MySQL (tendbsingle / tendbha) -----
    ClusterType.TenDBSingle: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.MYSQL_MONITOR: [ConfFile.ITEMS_CONFIG],
        ConfType.BACKUP: [ConfFile.DBBACKUP_INI, ConfFile.DBBACKUP_OPTIONS, ConfFile.BINLOG_ROTATE],
        # TODO: 暂时屏蔽 BACKUP_CLIENT，后续应该要作为通用的配置单独开发
        # ConfType.BACKUP_CLIENT: [ConfFile.COSINFO],
    },
    ClusterType.TenDBHA: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.MYSQL_MONITOR: [ConfFile.ITEMS_CONFIG],
        ConfType.BACKUP: [ConfFile.DBBACKUP_INI, ConfFile.DBBACKUP_OPTIONS, ConfFile.BINLOG_ROTATE],
        ConfType.CHECKSUM: [ConfFile.CHECKSUM],
        # ConfType.BACKUP_CLIENT: [ConfFile.COSINFO],
    },
    # ----- MySQL (tendbcluster), 多了 Spider 接入层参数 -----
    ClusterType.TenDBCluster: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [SPIDER_VERSION],
        ConfType.MYSQL_MONITOR: [ConfFile.ITEMS_CONFIG],
        ConfType.BACKUP: [ConfFile.DBBACKUP_INI, ConfFile.DBBACKUP_OPTIONS, ConfFile.BINLOG_ROTATE],
        ConfType.CHECKSUM: [ConfFile.CHECKSUM],
        # ConfType.BACKUP_CLIENT: [ConfFile.COSINFO],
    },
    # ----- Redis: TwemproxyRedisInstance / TwemproxyTendisSSDInstance -----
    ClusterType.TendisTwemproxyRedisInstance: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [ConfFile.TWEMPROXY],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    ClusterType.TwemproxyTendisSSDInstance: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [ConfFile.TWEMPROXY],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    # ----- Redis: PredixyRedisCluster / PredixyTendisplusCluster / PredixyTendisplusInstance -----
    ClusterType.TendisPredixyRedisCluster: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [ConfFile.PREDIXY],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    ClusterType.TendisPredixyTendisplusCluster: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [ConfFile.PREDIXY],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    ClusterType.TendisPredixyTendisplusInstance: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.PROXY: [ConfFile.PREDIXY],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    # ----- Redis: RedisInstance (无 Proxy) -----
    ClusterType.TendisRedisInstance: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.CONFIG: [
            ConfFile.FULLBACKUP,
            ConfFile.BINLOGBACKUP,
            ConfFile.KEYMOD,
            ConfFile.MAXMEMORY_SET,
        ],
    },
    # ----- ES -----
    ClusterType.Es: {ConfType.DBCONF: [DB_VERSION], ConfType.DEPLOY: [DB_VERSION]},
    # ----- Kafka -----
    ClusterType.Kafka: {
        ConfType.DBCONF: [DB_VERSION],
    },
    # ----- HDFS -----
    ClusterType.Hdfs: {
        ConfType.DBCONF: [DB_VERSION],
    },
    # ----- Pulsar -----
    ClusterType.Pulsar: {
        ConfType.DBCONF: [DB_VERSION],
    },
    # ----- Doris -----
    ClusterType.Doris: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.DORIS_RUNTIME_CONFIG: [DB_VERSION],
    },
    # ----- MongoDB -----
    ClusterType.MongoReplicaSet: {
        ConfType.DBCONF: [ConfFile.MONGOD],
        ConfType.CONFIG: [ConfFile.BACKUP, ConfFile.MONITOR],
    },
    ClusterType.MongoShardedCluster: {
        ConfType.DBCONF: [ConfFile.SHARDSVR, ConfFile.CONFIGSVR, ConfFile.MONGOS],
        ConfType.CONFIG: [ConfFile.BACKUP, ConfFile.MONITOR],
    },
    # ----- SQLServer -----
    ClusterType.SqlserverSingle: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.BACKUP: [ConfFile.DBBACKUP_CONF],
        ConfType.ALARM: [ConfFile.ALARM_CONF],
    },
    ClusterType.SqlserverHA: {
        ConfType.DBCONF: [DB_VERSION],
        ConfType.BACKUP: [ConfFile.DBBACKUP_CONF],
        ConfType.ALARM: [ConfFile.ALARM_CONF],
    },
}


# 组件配置对应的命名空间
COMPONENT_CONFIG_NAMESPACE = {
    ClusterType.SqlserverSingle: {
        ConfType.BACKUP: "sqlservercomm",
        ConfType.ALARM: "sqlservercomm",
    },
    ClusterType.SqlserverHA: {
        ConfType.BACKUP: "sqlservercomm",
        ConfType.ALARM: "sqlservercomm",
    },
}
