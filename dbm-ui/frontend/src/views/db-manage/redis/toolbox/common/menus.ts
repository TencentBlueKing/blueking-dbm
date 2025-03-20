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
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    children: [
      {
        id: 'RedisCapacityChange',
        name: t('集群容量变更'),
        parentId: 'manage',
      },
      {
        id: 'RedisProxyScaleUp',
        name: t('扩容接入层'),
        parentId: 'manage',
      },
      {
        id: 'RedisProxyScaleDown',
        name: t('缩容接入层'),
        parentId: 'manage',
      },
      {
        id: 'RedisClusterShardUpdate',
        name: t('集群分片变更'),
        parentId: 'manage',
      },
      {
        id: 'RedisClusterTypeUpdate',
        name: t('集群类型变更'),
        parentId: 'manage',
      },
      {
        id: 'RedisDBCreateSlave',
        name: t('重建从库'),
        parentId: 'manage',
      },
      {
        id: 'RedisMasterFailover',
        name: t('主从切换'),
        parentId: 'manage',
      },
      {
        id: 'RedisDBReplace',
        name: t('整机替换'),
        parentId: 'manage',
      },
    ],
    icon: 'db-icon-cluster',
    id: 'manage',
    name: t('集群维护'),
  },
  {
    children: [
      {
        id: 'RedisDBStructure',
        name: t('定点构造'),
        parentId: 'struct',
      },
      {
        id: 'RedisStructureInstance',
        name: t('构造实例'),
        parentId: 'struct',
      },
      {
        id: 'RedisRecoverFromInstance',
        name: t('以构造实例恢复'),
        parentId: 'struct',
      },
    ],
    icon: 'db-icon-copy',
    id: 'struct',
    name: t('数据构造'),
  },
  {
    children: [
      {
        id: 'RedisDBDataCopy',
        name: t('数据复制'),
        parentId: 'dts',
      },
      {
        id: 'RedisDBDataCopyRecord',
        name: t('数据复制记录'),
        parentId: 'dts',
      },
    ],
    icon: 'db-icon-data',
    id: 'dts',
    name: t('数据传输（DTS）'),
  },
];
