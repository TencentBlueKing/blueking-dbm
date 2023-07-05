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
}
export type DBTypesValues = `${DBTypes}`

/**
 * 集群类型
 */
export enum ClusterTypes {
  TENDBSINGLE = 'tendbsingle',
  TENDBHA = 'tendbha',
  TWEMPROXY_REDIS_INSTANCE = 'TwemproxyRedisInstance',
  PREDIXY_TENDISPLUS_CLUSTER = 'PredixyTendisplusCluster',
  TWEMPROXY_TENDIS_SSD_INSTANCE = 'TwemproxyTendisSSDInstance',
  ES = 'es',
  KAFKA = 'kafka',
  HDFS = 'hdfs',
  PULSAE = 'pulsar',
  INFLUXDB = 'influxdb',
  REDIS = 'redis',
}
export type ClusterTypesValues = `${ClusterTypes}`;

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
  REDIS_CLUSTER_APPLY = 'REDIS_CLUSTER_APPLY',
  REDIS_KEYS_EXTRACT = 'REDIS_KEYS_EXTRACT',
  REDIS_KEYS_DELETE = 'REDIS_KEYS_DELETE',
  REDIS_BACKUP = 'REDIS_BACKUP',
  REDIS_PURGE = 'REDIS_PURGE',
  REDIS_DESTROY = 'REDIS_DESTROY',
  REDIS_PROXY_OPEN = 'REDIS_PROXY_OPEN',
  REDIS_PROXY_CLOSE = 'REDIS_PROXY_CLOSE',
  REDIS_CLUSTER_SLAVE_CUTOFF = 'REDIS_CLUSTER_SLAVE_CUTOFF', // 整机替换
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
  PROXY_SCALE_UP = 'PROXY_SCALE_UP', // 接入层扩容
  PROXY_SCALE_DOWN = 'PROXY_SCALE_DOWN', // 接入层缩容
  REDIS_SCALE_UP = 'REDIS_SCALE_UP', // 存储层扩容
  REDIS_SCALE_DOWN = 'REDIS_SCALE_DOWN', // 存储层缩容
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
    name: t('高可用部署'),
    type: ClusterTypes.TENDBHA,
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
  MYSQL_TOOLBOX_FAVOR = 'MYSQL_TOOLBOX_FAVOR',
  MYSQL_TOOLBOX_MENUS = 'MYSQL_TOOLBOX_MENUS',
  DBHA_SWITCH_EVENTS = 'DBHA_SWITCH_EVENTS',
  REDIS_TOOLBOX_FAVOR = 'REDIS_TOOLBOX_FAVOR',
  REDIS_TOOLBOX_MENUS = 'REDIS_TOOLBOX_MENUS',
  INFLUXDB_TABLE_SETTINGS = 'INFLUXDB_TABLE_SETTINGS',
  SPECIFICATION_TABLE_SETTINGS = 'SPECIFICATION_TABLE_SETTINGS',
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

