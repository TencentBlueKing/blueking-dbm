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
  bind?: string[]
  dbConsoleValue: string;
  id: string;
  name: string;
  parentId: string;
}

export default [
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.sqlExecute',
        id: 'spiderSqlExecute',
        name: t('变更SQL执行'),
        parentId: 'spider_sql',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbRename',
        id: TicketTypes.TENDBCLUSTER_RENAME_DATABASE,
        name: t('DB 重命名'),
        parentId: 'spider_sql',
      },
    ],
    icon: 'db-icon-mysql',
    id: 'spider_sql',
    name: t('SQL任务'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.masterSlaveSwap',
        id: TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
        name: t('主从互切'),
        parentId: 'spider_cluster_maintain',
      },
      {
        bind: [TicketTypes.TENDBCLUSTER_INSTANCE_FAIL_OVER, TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER],
        dbConsoleValue: 'tendbCluster.toolbox.instanceFailover',
        id: TicketTypes.TENDBCLUSTER_INSTANCE_FAIL_OVER,
        name: t('主库故障切换'),
        parentId: 'spider_cluster_maintain',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.capacityChange',
        id: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
        name: t('集群容量变更'),
        parentId: 'spider_cluster_maintain',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.proxyScaleUp',
        id: 'SpiderProxyScaleUp',
        name: t('扩容接入层'),
        parentId: 'spider_cluster_maintain',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.proxyScaleDown',
        id: TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
        name: t('缩容接入层'),
        parentId: 'spider_cluster_maintain',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.switchNodes',
        id: TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES,
        name: t('替换接入层'),
        parentId: 'spider_cluster_maintain',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.masterSlaveClone',
        id: TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER,
        name: t('迁移主从'),
        parentId: 'spider_cluster_maintain',
      },
      {
        bind: [TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE, TicketTypes.TENDBCLUSTER_RESTORE_SLAVE],
        id: TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
        name: t('重建从库'),
        parentId: 'spider_cluster_maintain',
      },
    ],
    icon: 'db-icon-cluster',
    id: 'spider_cluster_maintain',
    name: t('集群维护'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.proxySlaveApply',
        id: 'SpiderProxySlaveApply',
        name: t('部署只读接入层'),
        parentId: 'spider_entry',
      },
    ],
    icon: 'db-icon-entry',
    id: 'spider_entry',
    name: t('访问入口'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.addMnt',
        id: TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY,
        name: t('添加运维节点'),
        parentId: 'spider_mnt',
      },
    ],
    icon: 'db-icon-jiankong',
    id: 'spider_mnt',
    name: t('运维节点管理'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbTableBackup',
        id: 'spiderDbTableBackup',
        name: t('库表备份'),
        parentId: 'spider_copy',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbBackup',
        id: 'spiderDbBackup',
        name: t('全库备份'),
        parentId: 'spider_copy',
      },
    ],
    icon: 'db-icon-copy',
    id: 'spider_copy',
    name: t('备份'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.rollback',
        id: TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER,
        name: t('定点构造'),
        parentId: 'spider_fileback',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.rollbackRecord',
        id: 'spiderRollbackRecord',
        name: t('构造实例'),
        parentId: 'spider_fileback',
      },
      {
        bind: ['spiderFlashback', TicketTypes.TENDBCLUSTER_FLASHBACK],
        dbConsoleValue: 'tendbCluster.toolbox.flashback',
        id: 'spiderFlashback',
        name: t('闪回'),
        parentId: 'spider_fileback',
      },
    ],
    icon: 'db-icon-rollback',
    id: 'spider_fileback',
    name: t('回档'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbClear',
        id: 'spiderDbClear',
        name: t('清档'),
        parentId: 'spider_data',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.checksum',
        id: 'spiderChecksum',
        name: t('数据校验修复'),
        parentId: 'spider_data',
      },
    ],
    icon: 'db-icon-data',
    id: 'spider_data',
    name: t('数据处理'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.clientPermissionClone',
        id: 'spiderPrivilegeCloneClient',
        name: t('客户端权限克隆'),
        parentId: 'spider_privilege',
      },
      {
        dbConsoleValue: 'tendbCluster.toolbox.dbInstancePermissionClone',
        id: 'spiderPrivilegeCloneInst',
        name: t('DB实例权限克隆'),
        parentId: 'spider_privilege',
      },
    ],
    icon: 'db-icon-clone',
    id: 'spider_privilege',
    name: t('权限克隆'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.openareaTemplate',
        id: 'spiderOpenareaTemplate',
        name: t('开区模版'),
        parentId: 'spider_openarea',
      },
    ],
    icon: 'db-icon-template',
    id: 'spider_openarea',
    name: t('克隆开区'),
  },
  {
    children: [
      {
        dbConsoleValue: 'tendbCluster.toolbox.webconsole',
        id: 'SpiderWebconsole',
        name: 'Webconsole',
        parentId: 'spider_data_query',
      },
    ],
    icon: 'db-icon-search',
    id: 'spider_data_query',
    name: t('数据查询'),
  },
];
