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

import type { ToolboxTreeNode } from '@views/db-manage/common/toolbox-new/common/types';

import { t } from '@locales/index';

export const toolboxMenuList: ToolboxTreeNode[] = [
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.sqlExecute',
        desc: t('执行 DDL / DML 变更 SQL'),
        id: TicketTypes.MYSQL_IMPORT_SQLFILE,
        name: t('变更 SQL 执行'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dataExport',
        desc: t('把 DB 数据导出为文件'),
        id: TicketTypes.MYSQL_DUMP_DATA,
        name: t('数据导出'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.webconsole',
        desc: t('只读 client，连接 DB 查询'),
        id: 'MySQLWebconsole',
        name: 'Webconsole',
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbRename',
        desc: t('修改 DB 名称'),
        id: TicketTypes.MYSQL_RENAME_DATABASE,
        name: t('DB 重命名'),
      },
    ],
    icon: 'chaxunyubiangeng',
    id: 'sql',
    name: t('查询与变更'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.dbBackup',
        desc: t('整库数据备份'),
        id: TicketTypes.MYSQL_HA_FULL_BACKUP,
        name: t('全库备份'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbTableBackup',
        desc: t('指定库 / 表级备份'),
        id: TicketTypes.MYSQL_HA_DB_TABLE_BACKUP,
        name: t('库表备份'),
      },
    ],
    icon: 'baofen',
    id: 'copy',
    name: t('备份'),
  },
  {
    children: [
      {
        bind: [TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER, TicketTypes.MYSQL_FIXPOINT_NEW_CLUSTER],
        dbConsoleValue: 'mysql.toolbox.fixpoint',
        desc: t('在其它集群恢复源集群的数据'),
        id: TicketTypes.MYSQL_FIXPOINT_EXIST_CLUSTER,
        name: t('构造'),
      },
      {
        bind: [TicketTypes.MYSQL_FLASHBACK, TicketTypes.MYSQL_ROLLBACK],
        dbConsoleValue: 'mysql.toolbox.flashback',
        desc: t('在源集群回滚数据'),
        id: TicketTypes.MYSQL_ROLLBACK,
        name: t('回档'),
      },
    ],
    icon: 'data-recovery',
    id: 'fileback',
    name: t('数据恢复'),
  },
  {
    children: [
      {
        bind: [TicketTypes.MYSQL_HA_TRUNCATE_DATA, TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA],
        dbConsoleValue: 'mysql.toolbox.dbClear',
        desc: t('删除指定库表的数据'),
        id: TicketTypes.MYSQL_HA_TRUNCATE_DATA,
        name: t('清档'),
      },
    ],
    icon: 'shujuqingli',
    id: 'clear',
    name: t('数据清理'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.openareaTemplate',
        desc: t('按模板将源集群表结构、数据、权限克隆到目标集群'),
        id: TicketTypes.MYSQL_OPEN_AREA,
        name: t('开区模版'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dataMigrate',
        desc: t('跨集群复制 DB 数据'),
        id: TicketTypes.MYSQL_DATA_MIGRATE,
        name: t('DB 数据克隆'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dtsDataMigrate',
        desc: t('按库表将数据从源集群迁到目标集群，目标库与源库同名'),
        id: TicketTypes.MYSQL_DTS_DATA_MIGRATE,
        name: t('MySQL DTS 同名迁移'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dtsDataMigrate',
        desc: t('按整库指定目标库名，将数据从源集群迁到目标集群'),
        id: TicketTypes.MYSQL_DTS_DATA_MIGRATE_RENAME,
        name: t('MySQL DTS 库改名迁移'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.mergeDiskSpace',
        desc: t('合并前的空间占用评估'),
        id: 'MySQLMergeDiskSpace',
        name: t('DB 数据合并空间评估'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.clientPermissionClone',
        desc: t('复制客户端访问权限配置'),
        id: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
        name: t('客户端权限克隆'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.dbInstancePermissionClone',
        desc: t('复制实例级权限配置'),
        id: TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
        name: t('DB实例权限克隆'),
      },
    ],
    icon: 'clone',
    id: 'clone',
    name: t('克隆与开区'),
  },
  {
    children: [
      {
        children: [
          {
            dbConsoleValue: 'mysql.toolbox.slaveAdd',
            desc: t('为集群新增从库实例'),
            id: TicketTypes.MYSQL_ADD_SLAVE,
            name: t('添加从库'),
          },
          {
            dbConsoleValue: 'mysql.toolbox.masterSlaveClone',
            desc: t('迁移主从节点到新机器'),
            id: TicketTypes.MYSQL_MIGRATE_CLUSTER,
            name: t('迁移主从'),
          },
          {
            dbConsoleValue: 'mysql.toolbox.masterSlaveSwap',
            desc: t('主从角色互换'),
            id: TicketTypes.MYSQL_MASTER_SLAVE_SWITCH,
            name: t('主从互切'),
          },
          {
            dbConsoleValue: 'mysql.toolbox.checksum',
            desc: t('主从复制一致性检查与修复'),
            id: TicketTypes.MYSQL_CHECKSUM,
            name: t('数据校验修复'),
          },
          {
            bind: [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, TicketTypes.MYSQL_RESTORE_SLAVE],
            dbConsoleValue: 'mysql.toolbox.slaveRebuild',
            desc: t('重建 Slave 实例'),
            id: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
            isFix: true,
            name: t('重建从库'),
          },
          {
            bind: [TicketTypes.MYSQL_MASTER_FAIL_OVER, TicketTypes.MYSQL_INSTANCE_FAIL_OVER],
            dbConsoleValue: 'mysql.toolbox.instanceFailover',
            desc: t('主库故障时从库紧急升主'),
            id: TicketTypes.MYSQL_MASTER_FAIL_OVER,
            isFix: true,
            name: t('主库故障切换'),
          },
        ],
        icon: '',
        id: 'backend',
        name: '存储层',
      },
      {
        children: [
          {
            bind: [
              TicketTypes.MYSQL_PROXY_ADD,
              TicketTypes.MYSQL_PROXY_REDUCE,
              TicketTypes.MYSQL_PROXY_SWITCH,
              TicketTypes.MYSQL_PROXY_CONF_CHANGE,
              TicketTypes.MYSQL_PROXY_MIGRATE,
              TicketTypes.MYSQL_PROXY_MIGRATE_INS,
            ],
            dbConsoleValue: 'mysql.toolbox.proxyAdd',
            desc: t('对 Proxy 进行增减、替换、升降配、迁移'),
            id: TicketTypes.MYSQL_PROXY_ADD,
            name: t('Proxy 变更'),
          },
          {
            dbConsoleValue: 'mysql.toolbox.proxyRebuild',
            desc: t('Proxy 进程异常时在原主机重建实例'),
            id: TicketTypes.MYSQL_PROXY_REBUILD,
            isFix: true,
            name: t('Proxy 原地重建'),
          },
          {
            dbConsoleValue: 'mysql.toolbox.proxyRescue',
            desc: t('全部 Proxy 不可用时，在新机器重建'),
            id: TicketTypes.MYSQL_PROXY_RESCUE,
            isFix: true,
            name: t('Proxy 灾难重建'),
          },
        ],
        icon: '',
        id: 'proxy',
        name: 'Proxy',
      },
    ],
    icon: 'cluster',
    id: 'tendbha',
    name: t('主从'),
  },
  {
    children: [
      {
        dbConsoleValue: 'mysql.toolbox.migrateSingle',
        desc: t('单节点架构实例迁移到新机器'),
        id: TicketTypes.MYSQL_MIGRATE_SINGLE,
        name: t('单节点迁移'),
      },
    ],
    icon: 'node',
    id: 'tendbsingle',
    name: t('单节点'),
  },
  {
    children: [
      {
        bind: [TicketTypes.MYSQL_LOCAL_UPGRADE, TicketTypes.MYSQL_MIGRATE_UPGRADE, TicketTypes.MYSQL_PROXY_UPGRADE],
        dbConsoleValue: 'mysql.toolbox.versionUpgrade',
        desc: t('升级数据库版本'),
        id: TicketTypes.MYSQL_PROXY_UPGRADE,
        name: t('版本升级'),
      },
      {
        dbConsoleValue: 'mysql.toolbox.clusterStandardize',
        desc: t('标准化集群配置和周边工具'),
        id: TicketTypes.MYSQL_CLUSTER_STANDARDIZE,
        name: t('标准化'),
      },
    ],
    icon: 'resource',
    id: 'common',
    name: t('通用'),
  },
];
