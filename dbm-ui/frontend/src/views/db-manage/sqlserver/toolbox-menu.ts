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
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    children: [
      {
        id: 'sqlServerExecute',
        name: t('变更SQL执行'),
        parentId: 'sql',
      },
      {
        id: TicketTypes.SQLSERVER_DBRENAME,
        name: t('DB重命名'),
        parentId: 'sql',
      },
    ],
    icon: 'db-icon-mysql',
    id: 'sql',
    name: t('SQL任务'),
  },
  {
    children: [
      {
        id: TicketTypes.SQLSERVER_BACKUP_DBS,
        name: t('库表备份'),
        parentId: 'copy',
      },
    ],
    icon: 'db-icon-copy',
    id: 'copy',
    name: t('备份'),
  },
  {
    children: [
      {
        id: TicketTypes.SQLSERVER_ROLLBACK,
        name: t('定点构造'),
        parentId: 'fileback',
      },
    ],
    icon: 'db-icon-rollback',
    id: 'fileback',
    name: t('回档'),
  },
  {
    children: [
      {
        id: TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE,
        name: t('重建从库'),
        parentId: 'migrate',
      },
      {
        id: TicketTypes.SQLSERVER_ADD_SLAVE,
        name: t('添加从库'),
        parentId: 'migrate',
      },
      {
        id: 'sqlServerMasterSlaveSwap',
        name: t('主从互切'),
        parentId: 'migrate',
      },
      {
        id: 'sqlServerMasterFailover',
        name: t('主库故障切换'),
        parentId: 'migrate',
      },
    ],
    icon: 'db-icon-cluster',
    id: 'migrate',
    name: t('集群维护'),
  },
  {
    children: [
      {
        id: TicketTypes.SQLSERVER_FULL_MIGRATE,
        name: t('数据迁移'),
        parentId: 'data',
      },
      {
        id: 'sqlServerDataMigrateRecord',
        name: t('迁移记录'),
        parentId: 'data',
      },
      {
        id: TicketTypes.SQLSERVER_CLEAR_DBS,
        name: t('清档'),
        parentId: 'data',
      },
    ],
    icon: 'db-icon-data',
    id: 'data',
    name: t('数据处理'),
  },
];
