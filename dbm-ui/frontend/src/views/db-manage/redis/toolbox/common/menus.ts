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
      },
      {
        name: t('扩容接入层'),
        id: 'RedisProxyScaleUp',
        parentId: 'manage',
      },
      {
        name: t('缩容接入层'),
        id: 'RedisProxyScaleDown',
        parentId: 'manage',
      },
      {
        name: t('集群分片变更'),
        id: 'RedisClusterShardUpdate',
        parentId: 'manage',
      },
      {
        name: t('集群类型变更'),
        id: 'RedisClusterTypeUpdate',
        parentId: 'manage',
      },
      {
        name: t('重建从库'),
        id: 'RedisDBCreateSlave',
        parentId: 'manage',
      },
      {
        name: t('主从切换'),
        id: 'RedisMasterFailover',
        parentId: 'manage',
      },
      {
        name: t('整机替换'),
        id: 'RedisDBReplace',
        parentId: 'manage',
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
      },
      {
        name: t('构造实例'),
        id: 'RedisStructureInstance',
        parentId: 'struct',
      },
      {
        name: t('以构造实例恢复'),
        id: 'RedisRecoverFromInstance',
        parentId: 'struct',
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
      },
      {
        name: t('数据复制记录'),
        id: 'RedisDBDataCopyRecord',
        parentId: 'dts',
      },
    ],
  },
];
