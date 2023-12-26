/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

import { t } from '@locales/index';

/**
 * 数据库类型
 */
export enum DBTypes {
  MYSQL = 'mysql',
  REDIS = 'redis',
  KAFKA = 'kafka',
  HDFS = 'hdfs',
  ES = 'es',
  PULSAR = 'pulsar',
  INFLUXDB = 'influxdb',
  SPIDER = 'spider',
}
export type DBTypesValues = `${DBTypes}`

/**
 * 集群类型
 */
export enum ClusterTypes {
  TENDBSINGLE = 'tendbsingle',
  TENDBHA = 'tendbha',
  TENDBCLUSTER = 'tendbcluster',
  TWEMPROXY_REDIS_INSTANCE = 'TwemproxyRedisInstance',
  PREDIXY_TENDISPLUS_CLUSTER = 'PredixyTendisplusCluster',
  TWEMPROXY_TENDIS_SSD_INSTANCE = 'TwemproxyTendisSSDInstance',
  ES = 'es',
  KAFKA = 'kafka',
  HDFS = 'hdfs',
  PULSAE = 'pulsar',
  INFLUXDB = 'influxdb',
  REDIS = 'redis',
  PREDIXY_REDIS_CLUSTER = 'PredixyRedisCluster',
  TWEMPROXY_TENDISPLUS_INSTANCE = 'TwemproxyTendisplusInstance',
  REDIS_INSTANCE = 'RedisInstance',
  TENDIS_SSD_INSTANCE = 'TendisSSDInstance',
  TENDIS_PLUS_INSTANCE = 'TendisplusInstance',
  REDIS_CLUSTER = 'RedisCluster',
  TENDIS_PLUS_CLUSTER = 'TendisplusCluster',
  MONGO_REPLICA_SET = 'MongoReplicaSet',
  MONGO_SHARED_CLUSTER = 'MongoShardedCluster',
  RIAK = 'riak',
}

// 机器类型
export enum MachineTypes {
  SPIDER = 'spider',
  REMOTE = 'remote',
  PROXY = 'proxy',
  BACKEND = 'backend',
  SINGLE = 'single',
  PREDIXY = 'predixy',
  TWEMPROXY = 'twemproxy',
  REDIS = 'redis',
  TENDISCACHE = 'tendiscache',
  TENDISSSD = 'tendisssd',
  TENDISPLUS = 'tendisplus',
  ES_DATANODE = 'es_datanode',
  ES_MASTER = 'es_master',
  ES_CLIENT = 'es_client',
  BROKER = 'broker',
  ZOOKEEPER = 'zookeeper',
  HDFS_MASTER = 'hdfs_master',
  HDFS_DATANODE = 'hdfs_datanode',
  MONGOS = 'mongos',
  MONGODB = 'mongodb',
  MONGO_CONFIG = 'mongo_config',
  INFLUXDB = 'influxdb',
  PULSAR_ZOOKEEPER = 'pulsar_zookeeper',
  PULSAR_BOOKKEEPER = 'pulsar_bookkeeper',
  PULSAR_BROKER = 'pulsar_broker',
  RIAK = 'riak',
}

export type ClusterTypesValues = keyof typeof clusterTypeInfos;

/**
 * 集群类型对应配置
 */
export const clusterTypeInfos = {
  [ClusterTypes.TENDBSINGLE]: {
    dbType: DBTypes.MYSQL,
  },
  [ClusterTypes.TENDBHA]: {
    dbType: DBTypes.MYSQL,
  },
  [ClusterTypes.TWEMPROXY_REDIS_INSTANCE]: {
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER]: {
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE]: {
    dbType: DBTypes.REDIS,
  },
  [ClusterTypes.ES]: {
    dbType: DBTypes.ES,
  },
  [ClusterTypes.KAFKA]: {
    dbType: DBTypes.KAFKA,
  },
  [ClusterTypes.HDFS]: {
    dbType: DBTypes.HDFS,
  },
  [ClusterTypes.INFLUXDB]: {
    dbType: DBTypes.INFLUXDB,
  },
  [ClusterTypes.PULSAE]: {
    dbType: DBTypes.PULSAR,
  },
  [ClusterTypes.TENDBCLUSTER]: {
    dbType: DBTypes.MYSQL,
  },
};
export type ClusterTypeInfos = keyof typeof clusterTypeInfos;

/**
 * 服务单据类型(与后端字段对应)
 */
export enum TicketTypes {
  MYSQL_SINGLE_APPLY = 'MYSQL_SINGLE_APPLY',
  MYSQL_HA_APPLY = 'MYSQL_HA_APPLY',
  MYSQL_EXCEL_AUTHORIZE_RULES = 'MYSQL_EXCEL_AUTHORIZE_RULES',
  MYSQL_AUTHORIZE_RULES = 'MYSQL_AUTHORIZE_RULES',
  MYSQL_HA_DISABLE = 'MYSQL_HA_DISABLE',
  MYSQL_HA_ENABLE = 'MYSQL_HA_ENABLE',
  MYSQL_HA_DESTROY = 'MYSQL_HA_DESTROY',
  MYSQL_SINGLE_DISABLE = 'MYSQL_SINGLE_DISABLE',
  MYSQL_SINGLE_ENABLE = 'MYSQL_SINGLE_ENABLE',
  MYSQL_SINGLE_DESTROY = 'MYSQL_SINGLE_DESTROY',
  MYSQL_INSTANCE_CLONE_RULES = 'MYSQL_INSTANCE_CLONE_RULES',
  MYSQL_CLIENT_CLONE_RULES = 'MYSQL_CLIENT_CLONE_RULES',
  MYSQL_RESTORE_LOCAL_SLAVE = 'MYSQL_RESTORE_LOCAL_SLAVE',
  MYSQL_HA_RENAME_DATABASE = 'MYSQL_HA_RENAME_DATABASE',
  MYSQL_ADD_SLAVE = 'MYSQL_ADD_SLAVE',
  MYSQL_HA_TRUNCATE_DATA = 'MYSQL_HA_TRUNCATE_DATA',
  MYSQL_CHECKSUM = 'MYSQL_CHECKSUM',
  TENDBCLUSTER_APPLY = 'TENDBCLUSTER_APPLY',
  REDIS_CLUSTER_APPLY = 'REDIS_CLUSTER_APPLY',
  REDIS_KEYS_EXTRACT = 'REDIS_KEYS_EXTRACT',
  REDIS_KEYS_DELETE = 'REDIS_KEYS_DELETE',
  REDIS_BACKUP = 'REDIS_BACKUP',
  REDIS_PURGE = 'REDIS_PURGE',
  REDIS_DESTROY = 'REDIS_DESTROY',
  REDIS_PROXY_OPEN = 'REDIS_PROXY_OPEN',
  REDIS_PROXY_CLOSE = 'REDIS_PROXY_CLOSE',
  REDIS_PLUGIN_DNS_BIND_CLB = 'REDIS_PLUGIN_DNS_BIND_CLB',
  REDIS_PLUGIN_DNS_UNBIND_CLB = 'REDIS_PLUGIN_DNS_UNBIND_CLB',
  REDIS_PLUGIN_CREATE_CLB = 'REDIS_PLUGIN_CREATE_CLB',
  REDIS_PLUGIN_DELETE_CLB = 'REDIS_PLUGIN_DELETE_CLB',
  REDIS_PLUGIN_CREATE_POLARIS = 'REDIS_PLUGIN_CREATE_POLARIS',
  REDIS_PLUGIN_DELETE_POLARIS = 'REDIS_PLUGIN_DELETE_POLARIS',
  ES_APPLY = 'ES_APPLY',
  ES_DISABLE = 'ES_DISABLE',
  ES_DESTROY = 'ES_DESTROY',
  ES_ENABLE = 'ES_ENABLE',
  ES_SCALE_UP = 'ES_SCALE_UP',
  ES_SHRINK = 'ES_SHRINK',
  KAFKA_APPLY = 'KAFKA_APPLY',
  KAFKA_ENABLE = 'KAFKA_ENABLE',
  KAFKA_DISABLE = 'KAFKA_DISABLE',
  KAFKA_DESTROY = 'KAFKA_DESTROY',
  KAFKA_SCALE_UP = 'KAFKA_SCALE_UP',
  KAFKA_SHRINK = 'KAFKA_SHRINK',
  HDFS_APPLY = 'HDFS_APPLY',
  HDFS_ENABLE = 'HDFS_ENABLE',
  HDFS_DISABLE = 'HDFS_DISABLE',
  HDFS_DESTROY = 'HDFS_DESTROY',
  HDFS_SCALE_UP = 'HDFS_SCALE_UP',
  HDFS_SHRINK = 'HDFS_SHRINK',
  ES_REPLACE = 'ES_REPLACE',
  HDFS_REPLACE = 'HDFS_REPLACE',
  KAFKA_REPLACE = 'KAFKA_REPLACE',
  KAFKA_REBOOT = 'KAFKA_REBOOT',
  ES_REBOOT = 'ES_REBOOT',
  HDFS_REBOOT = 'HDFS_REBOOT',
  MYSQL_PROXY_SWITCH = 'MYSQL_PROXY_SWITCH',
  MYSQL_HA_DB_TABLE_BACKUP = 'MYSQL_HA_DB_TABLE_BACKUP',
  MYSQL_MIGRATE_CLUSTER = 'MYSQL_MIGRATE_CLUSTER',
  MYSQL_MASTER_SLAVE_SWITCH = 'MYSQL_MASTER_SLAVE_SWITCH',
  MYSQL_PROXY_ADD = 'MYSQL_PROXY_ADD',
  MYSQL_MASTER_FAIL_OVER = 'MYSQL_MASTER_FAIL_OVER',
  MYSQL_IMPORT_SQLFILE = 'MYSQL_IMPORT_SQLFILE',
  MYSQL_FLASHBACK = 'MYSQL_FLASHBACK',
  MYSQL_ROLLBACK_CLUSTER = 'MYSQL_ROLLBACK_CLUSTER',
  MYSQL_RESTORE_SLAVE = 'MYSQL_RESTORE_SLAVE',
  MYSQL_HA_FULL_BACKUP = 'MYSQL_HA_FULL_BACKUP',
  PULSAR_APPLY = 'PULSAR_APPLY',
  INFLUXDB_APPLY = 'INFLUXDB_APPLY',
  INFLUXDB_DISABLE = 'INFLUXDB_DISABLE',
  INFLUXDB_REBOOT = 'INFLUXDB_REBOOT',
  INFLUXDB_REPLACE = 'INFLUXDB_REPLACE',
  INFLUXDB_ENABLE = 'INFLUXDB_ENABLE',
  INFLUXDB_DESTROY = 'INFLUXDB_DESTROY',
  PULSAR_REBOOT = 'PULSAR_REBOOT',
  PULSAR_ENABLE = 'PULSAR_ENABLE',
  PULSAR_DISABLE = 'PULSAR_DISABLE',
  PULSAR_DESTROY = 'PULSAR_DESTROY',
  PULSAR_REPLACE = 'PULSAR_REPLACE',
  PULSAR_SHRINK = 'PULSAR_SHRINK',
  PULSAR_SCALE_UP = 'PULSAR_SCALE_UP',
  REDIS_CLUSTER_CUTOFF = 'REDIS_CLUSTER_CUTOFF', // redis 整机替换
  REDIS_PROXY_SCALE_UP = 'PROXY_SCALE_UP', // redis 接入层扩容
  REDIS_PROXY_SCALE_DOWN = 'PROXY_SCALE_DOWN', // redis 接入层缩容
  REDIS_SCALE_UPDOWN = 'REDIS_SCALE_UPDOWN', // redis 集群容量变更
  REDIS_SCALE_UP = 'REDIS_SCALE_UP', // redis 存储层扩容
  REDIS_SCALE_DOWN = 'REDIS_SCALE_DOWN', // redis 存储层缩容
  REDIS_MASTER_SLAVE_SWITCH = 'REDIS_MASTER_SLAVE_SWITCH', // redis 主故障切换
  REDIS_SLOTS_MIGRATE = 'REDIS_SLOTS_MIGRATE', // redis slots 迁移
  REDIS_DATA_STRUCTURE = 'REDIS_DATA_STRUCTURE', // redis 定点构造
  REDIS_DATA_STRUCTURE_TASK_DELETE = 'REDIS_DATA_STRUCTURE_TASK_DELETE', // redis 构造销毁
  REDIS_CLUSTER_ADD_SLAVE = 'REDIS_CLUSTER_ADD_SLAVE', // redis 新建从库
  REDIS_CLUSTER_DATA_COPY = 'REDIS_CLUSTER_DATA_COPY', // redis 数据复制
  REDIS_CLUSTER_SHARD_NUM_UPDATE = 'REDIS_CLUSTER_SHARD_NUM_UPDATE', // redis 集群分片变更
  REDIS_CLUSTER_TYPE_UPDATE = 'REDIS_CLUSTER_TYPE_UPDATE', // redis 集群类型变更
  REDIS_DATACOPY_CHECK_REPAIR = 'REDIS_DATACOPY_CHECK_REPAIR', // redis 数据校验与修复
  REDIS_CLUSTER_ROLLBACK_DATA_COPY = 'REDIS_CLUSTER_ROLLBACK_DATA_COPY', // redis 数据回写
  TENDBCLUSTER_DISABLE = 'TENDBCLUSTER_DISABLE', // spider 集群禁用
  TENDBCLUSTER_ENABLE = 'TENDBCLUSTER_ENABLE', // spider 集群启用
  TENDBCLUSTER_DESTROY = 'TENDBCLUSTER_DESTROY', // spider 集群下架
  TENDBCLUSTER_SPIDER_SLAVE_DESTROY = 'TENDBCLUSTER_SPIDER_SLAVE_DESTROY', // spider 只读集群下架
  TENDBCLUSTER_SPIDER_REDUCE_MNT = 'TENDBCLUSTER_SPIDER_REDUCE_MNT', // spider 运维节点下架
  TENDBCLUSTER_SPIDER_ADD_NODES = 'TENDBCLUSTER_SPIDER_ADD_NODES', // Spider扩容接入层
  TENDBCLUSTER_SPIDER_REDUCE_NODES = 'TENDBCLUSTER_SPIDER_REDUCE_NODES', // Spider缩容接入层
  TENDBCLUSTER_SPIDER_SLAVE_APPLY = 'TENDBCLUSTER_SPIDER_SLAVE_APPLY', // Spider 部署只读接入层
  TENDBCLUSTER_SPIDER_MNT_APPLY = 'TENDBCLUSTER_SPIDER_MNT_APPLY', // Spider 添加运维节点
  TENDBCLUSTER_MASTER_SLAVE_SWITCH = 'TENDBCLUSTER_MASTER_SLAVE_SWITCH', // Spider remote 主从切换
  TENDBCLUSTER_RENAME_DATABASE = 'TENDBCLUSTER_RENAME_DATABASE', // Spider Tendbcluster 重命名
  TENDBCLUSTER_MASTER_FAIL_OVER = 'TENDBCLUSTER_MASTER_FAIL_OVER', // Spider remote主故障切换
  TENDBCLUSTER_DB_TABLE_BACKUP = 'TENDBCLUSTER_DB_TABLE_BACKUP', // Spider TenDBCluster 库表备份
  TENDBCLUSTER_FULL_BACKUP = 'TENDBCLUSTER_FULL_BACKUP', // Spider TenDBCluster 全备单据
  TENDBCLUSTER_NODE_REBALANCE = 'TENDBCLUSTER_NODE_REBALANCE', // Spider 集群remote节点扩缩容
  TENDBCLUSTER_ROLLBACK_CLUSTER = 'TENDBCLUSTER_ROLLBACK_CLUSTER', // Spider 定点回档
  TENDBCLUSTER_FLASHBACK = 'TENDBCLUSTER_FLASHBACK', // Spider 闪回
  TENDBCLUSTER_TRUNCATE_DATABASE = 'TENDBCLUSTER_TRUNCATE_DATABASE', // Spider tendbcluster 清档
  TENDBCLUSTER_SPIDER_MNT_DESTROY = 'TENDBCLUSTER_SPIDER_MNT_DESTROY', // Spider 运维节点下架
  TENDBCLUSTER_CHECKSUM = 'TENDBCLUSTER_CHECKSUM', // Spider checksum
  TENDBCLUSTER_CLIENT_CLONE_RULES = 'TENDBCLUSTER_CLIENT_CLONE_RULES', // Spider 客户端权限克隆
  TENDBCLUSTER_INSTANCE_CLONE_RULES = 'TENDBCLUSTER_INSTANCE_CLONE_RULES', // Spider DB 实例权限克隆
  TENDBCLUSTER_AUTHORIZE_RULES = 'TENDBCLUSTER_AUTHORIZE_RULES',
  TENDBCLUSTER_EXCEL_AUTHORIZE_RULES = 'TENDBCLUSTER_EXCEL_AUTHORIZE_RULES',
  TENDBCLUSTER_PARTITION = 'TENDBCLUSTER_PARTITION', // Spider 分区管理
  TENDBCLUSTER_IMPORT_SQLFILE = 'TENDBCLUSTER_IMPORT_SQLFILE', // Spider SQL变更执行
  TBINLOGDUMPER_INSTALL = 'TBINLOGDUMPER_INSTALL', // dumper 新建订阅
  TBINLOGDUMPER_SWITCH_NODES = 'TBINLOGDUMPER_SWITCH_NODES', // dumper 节点迁移
  TBINLOGDUMPER_REDUCE_NODES = 'TBINLOGDUMPER_REDUCE_NODES', // dumper 节点下架
  TBINLOGDUMPER_ENABLE_NODES = 'TBINLOGDUMPER_ENABLE_NODES', // dumper 节点启动
  TBINLOGDUMPER_DISABLE_NODES = 'TBINLOGDUMPER_DISABLE_NODES', // dumper 节点禁用
}
export type TicketTypesStrings = keyof typeof TicketTypes;

/**
 * mysql tickets type info
 */
export const mysqlType = {
  [TicketTypes.MYSQL_SINGLE_APPLY]: {
    id: TicketTypes.MYSQL_SINGLE_APPLY,
    name: t('单节点部署'),
    type: ClusterTypes.TENDBSINGLE,
    dbType: DBTypes.MYSQL,
  },
  [TicketTypes.MYSQL_HA_APPLY]: {
    id: TicketTypes.MYSQL_HA_APPLY,
    name: t('主从部署'),
    type: ClusterTypes.TENDBHA,
    dbType: DBTypes.MYSQL,
  },
  [TicketTypes.TENDBCLUSTER_APPLY]: {
    id: TicketTypes.TENDBCLUSTER_APPLY,
    name: t('TendbCluster分布式集群部署'),
    type: ClusterTypes.TENDBCLUSTER,
    dbType: DBTypes.MYSQL,
  },
};
export type MysqlTypeString = keyof typeof mysqlType;

/**
 * redis tickets type info
 */
export const redisType = {
  [TicketTypes.REDIS_CLUSTER_APPLY]: {
    id: TicketTypes.REDIS_CLUSTER_APPLY,
    name: t('Redis集群部署'),
    type: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
    dbType: DBTypes.REDIS,
  },
};

export const bigDataType = {
  [TicketTypes.ES_APPLY]: {
    id: TicketTypes.ES_APPLY,
    name: t('ES集群部署'),
    type: ClusterTypes.ES,
  },
  [TicketTypes.KAFKA_APPLY]: {
    id: TicketTypes.KAFKA_APPLY,
    name: t('Kafka集群部署'),
    type: ClusterTypes.KAFKA,
  },
  [TicketTypes.HDFS_APPLY]: {
    id: TicketTypes.HDFS_APPLY,
    name: t('HDFS集群部署'),
    type: ClusterTypes.HDFS,
  },
  [TicketTypes.PULSAR_APPLY]: {
    id: TicketTypes.PULSAR_APPLY,
    name: t('Pulsar集群部署'),
    type: ClusterTypes.PULSAE,
  },
  [TicketTypes.INFLUXDB_APPLY]: {
    id: TicketTypes.INFLUXDB_APPLY,
    name: t('InfluxDB集群部署'),
    type: ClusterTypes.INFLUXDB,
  },
};

/** all service tickets */
export const serviceTicketTypes = {
  ...mysqlType,
  ...redisType,
};
export type ServiceTicketTypeStrings = keyof typeof serviceTicketTypes;

/** 数据库配置层级 */
export enum ConfLevels {
  PLAT = 'plat',
  APP = 'app',
  MODULE = 'module',
  CLUSTER = 'cluster',
}
export type ConfLevelValues = `${ConfLevels}`;

/** 数据库配置层级 */
export const confLevelInfos = {
  [ConfLevels.PLAT]: {
    id: ConfLevels.PLAT,
    lockText: t('平台锁定'),
    tagText: t('平台配置'),
  },
  [ConfLevels.APP]: {
    id: ConfLevels.APP,
    lockText: t('业务锁定'),
    tagText: t('业务配置'),
  },
  [ConfLevels.MODULE]: {
    id: ConfLevels.MODULE,
    lockText: t('模块锁定'),
    tagText: t('模块配置'),
  },
  [ConfLevels.CLUSTER]: {
    id: ConfLevels.CLUSTER,
    lockText: t('集群锁定'),
    tagText: t('集群配置'),
  },
};

/**
 * 用户个人设置 keys
 */
export enum UserPersonalSettings {
  REDIS_TABLE_SETTINGS = 'REDIS_TABLE_SETTINGS',
  TENDBSINGLE_TABLE_SETTINGS = 'TENDBSINGLE_TABLE_SETTINGS',
  TENDBHA_TABLE_SETTINGS = 'TENDBHA_TABLE_SETTINGS',
  TENDBHA_INSTANCE_SETTINGS = 'TENDBHA_INSTANCE_SETTINGS',
  APP_FAVOR = 'APP_FAVOR',
  ACTIVATED_APP = 'ACTIVATED_APP',
  MYSQL_TOOLBOX_FAVOR = 'MYSQL_TOOLBOX_FAVOR_1',
  MYSQL_TOOLBOX_MENUS = 'MYSQL_TOOLBOX_MENUS_1',
  DBHA_SWITCH_EVENTS = 'DBHA_SWITCH_EVENTS',
  REDIS_TOOLBOX_FAVOR = 'REDIS_TOOLBOX_FAVOR_1',
  REDIS_TOOLBOX_MENUS = 'REDIS_TOOLBOX_MENUS_1',
  INFLUXDB_TABLE_SETTINGS = 'INFLUXDB_TABLE_SETTINGS',
  SPECIFICATION_TABLE_SETTINGS = 'SPECIFICATION_TABLE_SETTINGS',
  TENDBCLUSTER_TABLE_SETTINGS = 'TENDBCLUSTER_TABLE_SETTINGS',
  TENDBCLUSTER_INSTANCE_TABLE = 'TENDBCLUSTER_INSTANCE_TABLE',
  HDFS_TABLE_SETTINGS = 'HDFS_TABLE_SETTINGS',
  ES_TABLE_SETTINGS = 'ES_TABLE_SETTINGS',
  KAFKA_TABLE_SETTINGS = 'KAFKA_TABLE_SETTINGS',
  PULSAR_TABLE_SETTINGS = 'PULSAR_TABLE_SETTINGS',
  SPIDER_TOOLBOX_FAVOR = 'SPIDER_TOOLBOX_FAVOR_1',
  SPIDER_TOOLBOX_MENUS = 'SPIDER_TOOLBOX_MENUS_1',
  SERVICE_APPLY_FAVOR = 'SERVICE_APPLY_FAVOR'
}

/**
 * 用于列表界面计算table最大高度（该值包括导航/面包屑/容器边距/表格过滤操作高度）
 */
export enum OccupiedInnerHeight {
  WITH_PAGINATION = 218,
  NOT_PAGINATION = 202
}

/**
 * 集群实例状态
 */
export enum ClusterInstStatusKeys {
  RUNNING = 'running',
  UNAVAILABLE = 'unavailable',
  RESTORING = 'restoring',
}
export const clusterInstStatus = {
  [ClusterInstStatusKeys.RUNNING]: {
    theme: 'success',
    text: t('正常'),
    key: ClusterInstStatusKeys.RUNNING,
  },
  [ClusterInstStatusKeys.UNAVAILABLE]: {
    theme: 'danger',
    text: t('异常'),
    key: ClusterInstStatusKeys.UNAVAILABLE,
  },
  [ClusterInstStatusKeys.RESTORING]: {
    theme: 'loading',
    text: t('重建中'),
    key: ClusterInstStatusKeys.RESTORING,
  },
};
export type ClusterInstStatus = `${ClusterInstStatusKeys}`;

export enum PipelineStatus {
  READY = 'READY', // 准备中
  RUNNING = 'RUNNING', // 运行中
  FINISHED = 'FINISHED', // 完成
  FAILED = 'FAILED' // 失败
}


export enum LocalStorageKeys {
  REDIS_ROLLBACK_LIST = 'REDIS_ROLLBACK_LIST', // 跨页使用的回写数据列表
  REDIS_DB_REPLACE_MASTER_TIP = 'REDIS_DB_REPLACE_MASTER_TIP', // 整机替换弹窗中的master提示
  REDIS_DATA_CHECK_AND_REPAIR = 'REDIS_DATA_CHECK_AND_REPAIR', // 跨页使用的数据检验与修复的行数据
  REDIS_DB_DATA_RECORD_RECOPY = 'REDIS_DB_DATA_RECORD_RECOPY', // 跨页使用的数据复制记录
}

/**
 * 账号类型
 */
export enum AccountTypes {
  MYSQL = 'mysql',
  TENDBCLUSTER = 'tendbcluster',
}
export type AccountTypesValues = `${AccountTypes}`

/**
 * 要排除的系统库名称
 */
export const dbSysExclude = ['mysql', 'db_infobase', 'information_schema', 'performance_schema', 'sys', 'infodba_schema'];
