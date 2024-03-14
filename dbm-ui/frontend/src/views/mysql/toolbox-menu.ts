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
    name: t('SQL任务'),
    id: 'sql',
    icon: 'db-icon-mysql',
    children: [
      {
        name: t('变更SQL执行'),
        id: 'MySQLExecute',
        parentId: 'sql',
      },
      {
        name: t('DB重命名'),
        id: 'MySQLDBRename',
        parentId: 'sql',
      },
    ],
  },
  {
    name: t('备份'),
    id: 'copy',
    icon: 'db-icon-copy',
    children: [
      {
        name: t('库表备份'),
        id: 'MySQLDBTableBackup',
        parentId: 'copy',
      },
      {
        name: t('全库备份'),
        id: 'MySQLDBBackup',
        parentId: 'copy',
      },
    ],
  },
  {
    name: t('回档'),
    id: 'fileback',
    icon: 'db-icon-rollback',
    children: [
      {
        name: t('定点构造'),
        id: 'MySQLDBRollback',
        parentId: 'fileback',
      },
      {
        name: t('闪回'),
        id: 'MySQLDBFlashback',
        parentId: 'fileback',
      },
    ],
  },
  {
    name: t('权限克隆'),
    id: 'privilege',
    icon: 'db-icon-clone',
    children: [
      {
        name: t('客户端权限克隆'),
        id: 'MySQLPrivilegeCloneClient',
        parentId: 'privilege',
      },
      {
        name: t('DB实例权限克隆'),
        id: 'MySQLPrivilegeCloneInst',
        parentId: 'privilege',
      },
    ],
  },
  {
    name: t('集群维护'),
    id: 'migrate',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('重建从库'),
        id: 'MySQLSlaveRebuild',
        parentId: 'migrate',
      },
      {
        name: t('添加从库'),
        id: 'MySQLSlaveAdd',
        parentId: 'migrate',
      },
      {
        name: t('迁移主从'),
        id: 'MySQLMasterSlaveClone',
        parentId: 'migrate',
      },
      {
        name: t('主从互切'),
        id: 'MySQLMasterSlaveSwap',
        parentId: 'migrate',
      },
      {
        name: t('替换Proxy'),
        id: 'MySQLProxyReplace',
        parentId: 'migrate',
      },
      {
        name: t('添加Proxy'),
        id: 'MySQLProxyAdd',
        parentId: 'migrate',
      },
      {
        name: t('主库故障切换'),
        id: 'MySQLMasterFailover',
        parentId: 'migrate',
      },
    ],
  },
  {
    name: t('数据处理'),
    id: 'data',
    icon: 'db-icon-data',
    children: [
      {
        name: t('清档'),
        id: 'MySQLDBClear',
        parentId: 'data',
      },
      {
        name: t('数据校验修复'),
        id: 'MySQLChecksum',
        parentId: 'data',
      },
    ],
  },
  {
    name: t('克隆开区'),
    id: 'mysql_openarea',
    icon: 'db-icon-template',
    children: [
      {
        name: t('开区模版'),
        id: 'mysqlOpenareaTemplate',
        parentId: 'mysql_openarea',
      },
    ],
  },
];
