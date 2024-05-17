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

export interface MenuChild {
  name: string;
  id: string;
  parentId: string;
  dbConsoleValue: string;
}

export default [
  {
    name: t('集群维护'),
    id: 'manage',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('集群容量变更'),
        id: 'RedisCapacityChange',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.capacityChange',
      },
      {
        name: t('扩容接入层'),
        id: 'RedisProxyScaleUp',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.proxyScaleUp',
      },
      {
        name: t('缩容接入层'),
        id: 'RedisProxyScaleDown',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.proxyScaleDown',
      },
      {
        name: t('集群分片变更'),
        id: 'RedisClusterShardUpdate',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.clusterShardChange',
      },
      {
        name: t('集群类型变更'),
        id: 'RedisClusterTypeUpdate',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.clusterTypeChange',
      },
      {
        name: t('重建从库'),
        id: 'RedisDBCreateSlave',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.slaveRebuild',
      },
      {
        name: t('主从切换'),
        id: 'RedisMasterFailover',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.masterSlaveSwap',
      },
      {
        name: t('整机替换'),
        id: 'RedisDBReplace',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.dbReplace',
      },
      {
        name: t('版本升级'),
        id: 'RedisVersionUpgrade',
        parentId: 'manage',
        dbConsoleValue: 'redis.toolbox.versionUpgrade',
      },
    ],
  },
  {
    name: t('数据构造'),
    id: 'struct',
    icon: 'db-icon-copy',
    children: [
      {
        name: t('定点构造'),
        id: 'RedisDBStructure',
        parentId: 'struct',
        dbConsoleValue: 'redis.toolbox.rollback',
      },
      {
        name: t('构造实例'),
        id: 'RedisStructureInstance',
        parentId: 'struct',
        dbConsoleValue: 'redis.toolbox.rollbackRecord',
      },
      {
        name: t('以构造实例恢复'),
        id: 'RedisRecoverFromInstance',
        parentId: 'struct',
        dbConsoleValue: 'redis.toolbox.recoverFromInstance',
      },
    ],
  },
  {
    name: t('数据传输（DTS）'),
    id: 'dts',
    icon: 'db-icon-data',
    children: [
      {
        name: t('数据复制'),
        id: 'RedisDBDataCopy',
        parentId: 'dts',
        dbConsoleValue: 'redis.toolbox.dataCopy',
      },
      {
        name: t('数据复制记录'),
        id: 'RedisDBDataCopyRecord',
        parentId: 'dts',
        dbConsoleValue: 'redis.toolbox.dataCopyRecord',
      },
    ],
  },
];
