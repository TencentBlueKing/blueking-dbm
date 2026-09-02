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
        dbConsoleValue: 'tendbCluster.toolbox.sqlExecute',
        desc: t('执行 DDL / DML 变更 SQL'),
        id: TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
        name: t('变更 SQL 执行'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dataExport',
        desc: t('把 DB 数据导出为文件'),
        id: TicketTypes.TENDBCLUSTER_DUMP_DATA,
        name: t('数据导出'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.webconsole',
        desc: t('只读 client，连接 DB 查询'),
        id: 'SpiderWebconsole',
        name: 'Webconsole',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbRename',
        desc: t('修改 DB 名称'),
        id: TicketTypes.TENDBCLUSTER_RENAME_DATABASE,
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
        dbConsoleValue: 'tendbCluster.toolbox.dbBackup',
        desc: t('整库数据备份'),
        id: TicketTypes.TENDBCLUSTER_FULL_BACKUP,
        name: t('全库备份'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbTableBackup',
        desc: t('指定库 / 表级备份'),
        id: TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP,
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
        bind: [TicketTypes.TENDBCLUSTER_FIXPOINT_EXIST, TicketTypes.TENDBCLUSTER_FIXPOINT_NEW],
        dbConsoleValue: 'tendbCluster.toolbox.fixpoint',
        desc: t('在其它集群恢复源集群的数据'),
        id: TicketTypes.TENDBCLUSTER_FIXPOINT_EXIST,
        name: t('构造'),
      },
      {
        bind: [TicketTypes.TENDBCLUSTER_FLASHBACK, TicketTypes.TENDBCLUSTER_ROLLBACK],
        dbConsoleValue: 'tendbCluster.toolbox.flashback',
        desc: t('在源集群回滚数据'),
        id: TicketTypes.TENDBCLUSTER_ROLLBACK,
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
        dbConsoleValue: 'tendbCluster.toolbox.dbClear',
        desc: t('删除指定库表的数据'),
        id: TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE,
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
        dbConsoleValue: 'tendbCluster.toolbox.openareaTemplate',
        desc: t('按模板将源集群表结构、数据、权限克隆到目标集群'),
        id: TicketTypes.TENDBCLUSTER_OPEN_AREA,
        name: t('开区模版'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.clientPermissionClone',
        desc: t('复制客户端访问权限配置'),
        id: TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES,
        name: t('客户端权限克隆'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbInstancePermissionClone',
        desc: t('复制实例级权限配置'),
        id: TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES,
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
        bind: [
          TicketTypes.TENDBCLUSTER_SPIDER_CONF_UP_DOWN,
          TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
          TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
          TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES,
        ],
        dbConsoleValue: 'tendbCluster.toolbox.spiderChange',
        desc: t('对 Spider 进行增减、替换、升降配'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
        name: t('接入层变更'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.proxySlaveApply',
        desc: t('部署 Spider Slave'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY,
        name: t('部署只读接入层'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.removeReadonlyNode',
        desc: t('下架 Spider Slave'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY,
        name: t('下架只读接入层'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.addMnt',
        desc: t('部署 Spider Mnt'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY,
        name: t('添加运维节点'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.removeMNTNode',
        desc: t('下架 Spider Mnt'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY,
        name: t('下架运维节点'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.spiderRebuild',
        desc: t('Spider 进程异常时在原主机重建实例'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_REBUILD,
        isFix: true,
        name: t('接入层原地重建'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.spiderLayerDr',
        desc: t('全部 Spider 不可用时，在新机器重建'),
        id: TicketTypes.TENDBCLUSTER_SPIDER_LAYER_DR,
        isFix: true,
        name: t('接入层灾难重建'),
      },
    ],
    icon: 'proxy',
    id: 'proxy',
    name: '接入层',
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.masterSlaveSwap',
        desc: t('后端分片主从角色互换'),
        id: TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
        name: t('主从互切'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.masterSlaveClone',
        desc: t('迁移后端分片主从节点到新机器'),
        id: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
        name: t('迁移主从'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.capacityChange',
        desc: t('调整后端分片规格'),
        id: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
        name: t('集群容量变更'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.checksum',
        desc: t('主从复制一致性检查与修复'),
        id: TicketTypes.TENDBCLUSTER_CHECKSUM,
        name: t('数据校验修复'),
      },
      {
        bind: [TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE, TicketTypes.TENDBCLUSTER_RESTORE_SLAVE],
        dbConsoleValue: 'tendbCluster.toolbox.slaveRebuild',
        desc: t('重建后端分片的Slave 实例'),
        id: TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        isFix: true,
        name: t('重建从库'),
      },
      {
        bind: [TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER, TicketTypes.TENDBCLUSTER_INSTANCE_FAIL_OVER],
        dbConsoleValue: 'tendbCluster.toolbox.instanceFailover',
        desc: t('后端分片主库故障时从库紧急升主'),
        id: TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER,
        isFix: true,
        name: t('主库故障切换'),
      },
    ],
    icon: 'node',
    id: 'backend',
    name: '存储层',
  },
  {
    children: [
      {
        bind: [
          TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE,
          TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE,
          TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE,
          TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE,
        ],
        dbConsoleValue: 'tendbCluster.toolbox.versionUpgrade',
        desc: t('升级数据库版本'),
        id: TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE,
        name: t('版本升级'),
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.clusterStandardize',
        desc: t('标准化集群配置和周边工具'),
        id: TicketTypes.TENDBCLUSTER_CLUSTER_STANDARDIZE,
        name: t('标准化'),
      },
    ],
    icon: 'resource',
    id: 'common',
    name: t('通用'),
  },
];
