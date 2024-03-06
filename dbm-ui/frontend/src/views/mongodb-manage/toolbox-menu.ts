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
  name: string,
  id: string,
  parentId: string
}

export default [
  {
    name: t('脚本任务'),
    id: 'mongo_script',
    icon: 'db-icon-mysql',
    children: [
      {
        name: t('变更脚本执行'),
        id: 'MongoScriptExecute',
        parentId: 'mongo_script',
      },
    ],
  },
  {
    name: t('集群维护'),
    id: 'mongo_manage',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('扩容Shard节点数'),
        id: 'MongoShardScaleUp',
        parentId: 'mongo_manage',
      },
      {
        name: t('缩容Shard节点数'),
        id: 'MongoShardScaleDown',
        parentId: 'mongo_manage',
      },
      {
        name: t('集群容量变更'),
        id: 'MongoCapacityChange',
        parentId: 'mongo_manage',
      },
      {
        name: t('扩容接入层'),
        id: 'MongoProxyScaleUp',
        parentId: 'mongo_manage',
      },
      {
        name: t('缩容接入层'),
        id: 'MongoProxyScaleDown',
        parentId: 'mongo_manage',
      },
      {
        name: t('整机替换'),
        id: 'MongoDBReplace',
        parentId: 'mongo_manage',
      },
    ],
  },
  {
    name: t('回档'),
    id: 'mongo_rollback',
    icon: 'db-icon-copy',
    children: [
      {
        name: t('定点构造'),
        id: 'MongoDBStructure',
        parentId: 'mongo_rollback',
      },
      {
        name: t('构造实例'),
        id: 'MongoStructureInstance',
        parentId: 'mongo_rollback',
      },
    ],
  },
  {
    name: t('备份'),
    id: 'mongo_backup',
    icon: 'db-icon-copy',
    children: [
      {
        name: t('库表备份'),
        id: 'MongoDbTableBackup',
        parentId: 'mongo_backup',
      },
      {
        name: t('全库备份'),
        id: 'MongoDbBackup',
        parentId: 'mongo_backup',
      },
    ],
  },
  {
    name: t('数据处理'),
    id: 'mongo_data',
    icon: 'db-icon-data',
    children: [
      {
        name: t('清档'),
        id: 'MongoDbClear',
        parentId: 'mongo_data',
      },
    ],
  },
];
