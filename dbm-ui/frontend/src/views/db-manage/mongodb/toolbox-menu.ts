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

export interface MenuChild {
  bind?: string[];
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.scriptExecute',
        id: 'MongoScriptExecute',
        name: t('变更脚本执行'),
        parentId: 'mongo_script',
      },
    ],
    icon: 'db-icon-mysql',
    id: 'mongo_script',
    name: t('脚本任务'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.shardScaleUp',
        id: TicketTypes.MONGODB_ADD_SHARD_NODES,
        name: t('扩容Shard节点数'),
        parentId: 'mongo_manage',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.shardScaleDown',
        id: TicketTypes.MONGODB_REDUCE_SHARD_NODES,
        name: t('缩容Shard节点数'),
        parentId: 'mongo_manage',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.scaleUpDown',
        id: TicketTypes.MONGODB_SCALE_UPDOWN,
        name: t('集群容量变更'),
        parentId: 'mongo_manage',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.proxyScaleUp',
        id: TicketTypes.MONGODB_ADD_MONGOS,
        name: t('扩容接入层'),
        parentId: 'mongo_manage',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.reduceMongos',
        id: TicketTypes.MONGODB_REDUCE_MONGOS,
        name: t('缩容接入层'),
        parentId: 'mongo_manage',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.cutoff',
        id: TicketTypes.MONGODB_CUTOFF,
        name: t('整机替换'),
        parentId: 'mongo_manage',
      },
    ],
    icon: 'db-icon-cluster',
    id: 'mongo_manage',
    name: t('集群维护'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.pitrRestore',
        id: TicketTypes.MONGODB_PITR_RESTORE,
        name: t('定点构造'),
        parentId: 'mongo_rollback',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.structureInstance',
        id: 'MongoStructureInstance',
        name: t('构造实例'),
        parentId: 'mongo_rollback',
      },
    ],
    icon: 'db-icon-copy',
    id: 'mongo_rollback',
    name: t('回档'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.dbTableBackup',
        id: TicketTypes.MONGODB_BACKUP,
        name: t('库表备份'),
        parentId: 'mongo_backup',
      },
      {
        dbConsoleValue: 'mongodb.toolbox.dbBackup',
        id: TicketTypes.MONGODB_FULL_BACKUP,
        name: t('全库备份'),
        parentId: 'mongo_backup',
      },
    ],
    icon: 'db-icon-copy',
    id: 'mongo_backup',
    name: t('备份'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.dbClear',
        id: TicketTypes.MONGODB_REMOVE_NS,
        name: t('清档'),
        parentId: 'mongo_data',
      },
    ],
    icon: 'db-icon-data',
    id: 'mongo_data',
    name: t('数据处理'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mongodb.toolbox.webconsole',
        id: 'MongodbWebconsole',
        name: 'Webconsole',
        parentId: 'redis_data_query',
      },
    ],
    icon: 'db-icon-search',
    id: 'mongo_data_query',
    name: t('数据查询'),
  },
];
