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
  dbConsoleValue: string;
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.sqlExecute',
        id: 'MySQLExecute',
        name: t('变更SQL执行'),
        parentId: 'sql',
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbRename',
        id: TicketTypes.MYSQL_RENAME_DATABASE,
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
        dbConsoleValue: 'mysql.toolbox.dbTableBackup',
        id: 'MySQLDBTableBackup',
        name: t('库表备份'),
        parentId: 'copy',
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbBackup',
        id: 'MySQLDBBackup',
        name: t('全库备份'),
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
        dbConsoleValue: 'mysql.toolbox.rollback',
        id: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
        name: t('定点构造'),
        parentId: 'fileback',
      },
      {
        bind: ['MySQLDBFlashback', TicketTypes.MYSQL_FLASHBACK],
        dbConsoleValue: 'mysql.toolbox.flashback',
        id: 'MySQLDBFlashback',
        name: t('闪回'),
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
        dbConsoleValue: 'mysql.toolbox.clientPermissionClone',
        id: 'MySQLPrivilegeCloneClient',
        name: t('客户端权限克隆'),
        parentId: 'privilege',
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbInstancePermissionClone',
        id: 'MySQLPrivilegeCloneInst',
        name: t('DB实例权限克隆'),
        parentId: 'privilege',
      },
    ],
    icon: 'db-icon-clone',
    id: 'privilege',
    name: t('权限克隆'),
  },
  {
    children: [
      {
        bind: [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, TicketTypes.MYSQL_RESTORE_SLAVE],
        dbConsoleValue: 'mysql.toolbox.slaveRebuild',
        id: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
        name: t('重建从库'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.slaveAdd',
        id: TicketTypes.MYSQL_ADD_SLAVE,
        name: t('添加从库'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.masterSlaveClone',
        id: TicketTypes.MYSQL_MIGRATE_CLUSTER,
        name: t('迁移主从'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.masterSlaveSwap',
        id: TicketTypes.MYSQL_MASTER_SLAVE_SWITCH,
        name: t('主从互切'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.proxyReplace',
        id: TicketTypes.MYSQL_PROXY_SWITCH,
        name: t('替换Proxy'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.proxyReduce',
        id: TicketTypes.MYSQL_PROXY_REDUCE,
        name: t('缩容Proxy'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.proxyAdd',
        id: TicketTypes.MYSQL_PROXY_ADD,
        name: t('添加Proxy'),
        parentId: 'migrate',
      },
      {
        bind: [TicketTypes.MYSQL_MASTER_FAIL_OVER, TicketTypes.MYSQL_INSTANCE_FAIL_OVER],
        dbConsoleValue: 'mysql.toolbox.instanceFailover',
        id: TicketTypes.MYSQL_MASTER_FAIL_OVER,
        name: t('主库故障切换'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.versionUpgrade',
        id: TicketTypes.MYSQL_PROXY_UPGRADE,
        name: t('版本升级'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'mysql.toolbox.clusterStandardize',
        id: TicketTypes.MYSQL_CLUSTER_STANDARDIZE,
        name: t('集群标准化'),
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
        dbConsoleValue: 'mysql.toolbox.dbClear',
        id: 'MySQLDBClear',
        name: t('清档'),
        parentId: 'data',
      },
      {
        dbConsoleValue: 'mysql.toolbox.checksum',
        id: 'MySQLChecksum',
        name: t('数据校验修复'),
        parentId: 'data',
      },
      {
        dbConsoleValue: 'mysql.toolbox.dataMigrate',
        id: 'MySQLDataMigrate',
        name: t('DB克隆'),
        parentId: 'data',
      },
    ],
    icon: 'db-icon-data',
    id: 'data',
    name: t('数据处理'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.openareaTemplate',
        id: 'MySQLOpenareaTemplate',
        name: t('开区模版'),
        parentId: 'mysql_openarea',
      },
    ],
    icon: 'db-icon-template',
    id: 'mysql_openarea',
    name: t('克隆开区'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.webconsole',
        id: 'MySQLWebconsole',
        name: 'Webconsole',
        parentId: 'mysql_data_query',
      },
    ],
    icon: 'db-icon-search',
    id: 'mysql_data_query',
    name: t('数据查询'),
  },
];
