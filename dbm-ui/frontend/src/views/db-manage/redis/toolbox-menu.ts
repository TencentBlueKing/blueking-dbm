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

import { TicketTypes } from '@common/const';

import { t } from '@locales/index';

export interface MenuItem {
  children: MenuChild[];
  icon: string;
  id: string;
  name: string;
}

export interface MenuChild {
  bind?: string[];
  dbConsoleValue: string;
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    id: 'common-menu',
    menuList: [
      {
        children: [
          {
            bind: [TicketTypes.REDIS_KEYS_EXTRACT, TicketTypes.REDIS_KEYS_DELETE],
            dbConsoleValue: 'redis.toolbox.keyExtract',
            id: TicketTypes.REDIS_KEYS_EXTRACT,
            name: t('Key 操作'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.backup',
            id: TicketTypes.REDIS_BACKUP,
            name: t('备份'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.purge',
            id: TicketTypes.REDIS_PURGE,
            name: t('清档'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.slaveRebuild',
            id: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
            name: t('重建从库'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.masterSlaveSwap',
            id: TicketTypes.REDIS_MASTER_SLAVE_SWITCH,
            name: t('主从切换'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.dbReplace',
            id: TicketTypes.REDIS_CLUSTER_CUTOFF,
            name: t('整机替换'),
            parentId: 'common-manage',
          },
          {
            bind: [TicketTypes.REDIS_CLUSTER_INS_MIGRATE, TicketTypes.REDIS_SINGLE_INS_MIGRATE],
            dbConsoleValue: 'redis.toolbox.migrate',
            id: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
            name: t('迁移'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.versionUpgrade',
            id: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
            name: t('版本升级'),
            parentId: 'common-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.installModule',
            id: TicketTypes.REDIS_CLUSTER_LOAD_MODULES,
            name: t('安装 Module'),
            parentId: 'cluster-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.clusterReinstallDbmon',
            id: TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON,
            name: t('集群标准化'),
            parentId: 'cluster-manage',
          },
        ],
        icon: 'db-icon-cluster',
        id: 'common-manage',
        name: t('通用维护'),
      },
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.rollback',
            id: 'RedisDBStructure',
            name: t('定点构造'),
            parentId: 'common-struct',
          },
          {
            dbConsoleValue: 'redis.toolbox.rollbackRecord',
            id: 'RedisStructureInstance',
            name: t('构造实例'),
            parentId: 'common-struct',
          },
          {
            dbConsoleValue: 'redis.toolbox.recoverFromInstance',
            id: 'RedisRecoverFromInstance',
            name: t('以构造实例恢复'),
            parentId: 'common-struct',
          },
        ],
        icon: 'db-icon-copy',
        id: 'common-struct',
        name: t('数据构造'),
      },
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.dataCopy',
            id: TicketTypes.REDIS_CLUSTER_DATA_COPY,
            name: t('数据复制'),
            parentId: 'common-dts',
          },
          {
            dbConsoleValue: 'redis.toolbox.dataCopyRecord',
            id: 'RedisDBDataCopyRecord',
            name: t('数据复制记录'),
            parentId: 'common-dts',
          },
        ],
        icon: 'db-icon-data',
        id: 'common-dts',
        name: t('数据传输（DTS）'),
      },
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.hotKey',
            id: TicketTypes.REDIS_HOT_KEY_ANALYSIS,
            name: t('热 Key 分析'),
            parentId: 'redis_data_query',
          },
          {
            dbConsoleValue: 'redis.toolbox.hotKeyList',
            id: 'RedisHotKeyList',
            name: t('热 Key 分析报告'),
            parentId: 'redis_data_query',
          },
        ],
        icon: 'db-icon-search',
        id: 'redis_analyse',
        name: t('分析'),
      },
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.queryAccessSource',
            id: 'RedisQueryAccessSource',
            name: t('查询访问来源'),
            parentId: 'redis_data_query',
          },
          {
            dbConsoleValue: 'redis.toolbox.webconsole',
            id: 'RedisWebconsole',
            name: 'Webconsole',
            parentId: 'redis_data_query',
          },
        ],
        icon: 'db-icon-search',
        id: 'redis_data_query',
        name: t('数据查询'),
      },
    ],
    title: t('通用'),
    titleTooltip: t('支持所有架构类型'),
  },
  {
    id: 'cluster-menu',
    menuList: [
      {
        children: [
          {
            dbConsoleValue: 'redis.toolbox.proxyScaleUp',
            id: TicketTypes.REDIS_PROXY_SCALE_UP,
            name: t('扩容接入层'),
            parentId: 'cluster-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.proxyScaleDown',
            id: TicketTypes.REDIS_PROXY_SCALE_DOWN,
            name: t('缩容接入层'),
            parentId: 'cluster-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.capacityChange',
            id: TicketTypes.REDIS_SCALE_UPDOWN,
            name: t('集群容量变更'),
            parentId: 'cluster-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.clusterShardChange',
            id: TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE,
            name: t('集群分片变更'),
            parentId: 'cluster-manage',
          },
          {
            dbConsoleValue: 'redis.toolbox.clusterTypeChange',
            id: TicketTypes.REDIS_CLUSTER_TYPE_UPDATE,
            name: t('集群类型变更'),
            parentId: 'cluster-manage',
          },
        ],
        icon: 'db-icon-cluster',
        id: 'cluster-manage',
        name: t('集群维护'),
      },
    ],
    title: t('集群'),
    titleTooltip: t('仅支持 TendisCache，TendisSSD，Tendisplus，RedisCluster 类型'),
  },
];
