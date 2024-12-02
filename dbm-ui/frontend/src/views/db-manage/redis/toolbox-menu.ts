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

export interface MenuItem {
  name: string;
  id: string;
  icon: string;
  children: MenuChild[];
}

export interface MenuChild {
  name: string;
  id: string;
  parentId: string;
  dbConsoleValue: string;
}

export default [
  {
    id: 'common-menu',
    title: t('通用'),
    titleTooltip: t('支持所有架构类型'),
    menuList: [
      {
        name: t('通用维护'),
        id: 'common-manage',
        icon: 'db-icon-cluster',
        children: [
          {
            name: t('重建从库'),
            id: 'RedisDBCreateSlave',
            parentId: 'common-manage',
            dbConsoleValue: 'redis.toolbox.slaveRebuild',
          },
          {
            name: t('主从切换'),
            id: 'RedisMasterFailover',
            parentId: 'common-manage',
            dbConsoleValue: 'redis.toolbox.masterSlaveSwap',
          },
          {
            name: t('整机替换'),
            id: 'RedisDBReplace',
            parentId: 'common-manage',
            dbConsoleValue: 'redis.toolbox.dbReplace',
          },
          {
            name: t('版本升级'),
            id: 'RedisVersionUpgrade',
            parentId: 'common-manage',
            dbConsoleValue: 'redis.toolbox.versionUpgrade',
          },
          {
            name: t('安装 Module'),
            id: 'RedisInstallModule',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.installModule',
          },
        ],
      },
      {
        name: t('数据构造'),
        id: 'common-struct',
        icon: 'db-icon-copy',
        children: [
          {
            name: t('定点构造'),
            id: 'RedisDBStructure',
            parentId: 'common-struct',
            dbConsoleValue: 'redis.toolbox.rollback',
          },
          {
            name: t('构造实例'),
            id: 'RedisStructureInstance',
            parentId: 'common-struct',
            dbConsoleValue: 'redis.toolbox.rollbackRecord',
          },
          {
            name: t('以构造实例恢复'),
            id: 'RedisRecoverFromInstance',
            parentId: 'common-struct',
            dbConsoleValue: 'redis.toolbox.recoverFromInstance',
          },
        ],
      },
      {
        name: t('数据传输（DTS）'),
        id: 'common-dts',
        icon: 'db-icon-data',
        children: [
          {
            name: t('数据复制'),
            id: 'RedisDBDataCopy',
            parentId: 'common-dts',
            dbConsoleValue: 'redis.toolbox.dataCopy',
          },
          {
            name: t('数据复制记录'),
            id: 'RedisDBDataCopyRecord',
            parentId: 'common-dts',
            dbConsoleValue: 'redis.toolbox.dataCopyRecord',
          },
        ],
      },
      {
        name: t('数据查询'),
        id: 'redis_data_query',
        icon: 'db-icon-search',
        children: [
          {
            name: 'Webconsole',
            id: 'RedisWebconsole',
            parentId: 'redis_data_query',
            dbConsoleValue: 'redis.toolbox.webconsole',
          },
        ],
      },
    ],
  },
  {
    id: 'cluster-menu',
    title: t('集群'),
    titleTooltip: t('仅支持 TendisCache，TendisSSD，Tendisplus，RedisCluster 类型'),
    menuList: [
      {
        name: t('集群维护'),
        id: 'cluster-manage',
        icon: 'db-icon-cluster',
        children: [
          {
            name: t('扩容接入层'),
            id: 'RedisProxyScaleUp',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.proxyScaleUp',
          },
          {
            name: t('缩容接入层'),
            id: 'RedisProxyScaleDown',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.proxyScaleDown',
          },
          {
            name: t('集群容量变更'),
            id: 'RedisCapacityChange',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.capacityChange',
          },
          {
            name: t('集群分片变更'),
            id: 'RedisClusterShardUpdate',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.clusterShardChange',
          },
          {
            name: t('集群类型变更'),
            id: 'RedisClusterTypeUpdate',
            parentId: 'cluster-manage',
            dbConsoleValue: 'redis.toolbox.clusterTypeChange',
          },
        ],
      },
    ],
  },
];
