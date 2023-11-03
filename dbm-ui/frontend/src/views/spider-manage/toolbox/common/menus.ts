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
    name: t('SQL任务'),
    id: 'spider_sql',
    icon: 'db-icon-mysql',
    children: [
      {
        name: t('变更SQL执行'),
        id: 'spiderSqlExecute',
        parentId: 'spider_sql',
      },
      {
        name: t('DB 重命名'),
        id: 'spiderDbRename',
        parentId: 'spider_sql',
      },
    ],
  },
  {
    name: t('集群维护'),
    id: 'spider_cluster_maintain',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('主从互切'),
        id: 'spiderMasterSlaveSwap',
        parentId: 'spider_cluster_maintain',
      },
      {
        name: t('主库故障切换'),
        id: 'spiderMasterFailover',
        parentId: 'spider_cluster_maintain',
      },
      {
        name: t('集群容量变更'),
        id: 'spiderCapacityChange',
        parentId: 'spider_cluster_maintain',
      },
      {
        name: t('扩容接入层'),
        id: 'SpiderProxyScaleUp',
        parentId: 'spider_cluster_maintain',
      },
      {
        name: t('缩容接入层'),
        id: 'SpiderProxyScaleDown',
        parentId: 'spider_cluster_maintain',
      },
    ],
  },
  {
    name: t('访问入口'),
    id: 'spider_entry',
    icon: 'db-icon-entry',
    children: [
      {
        name: t('部署只读接入层'),
        id: 'SpiderProxySlaveApply',
        parentId: 'spider_entry',
      },
    ],
  },
  {
    name: t('运维 Spider 管理'),
    id: 'spider_mnt',
    icon: 'db-icon-jiankong',
    children: [
      {
        name: t('添加运维节点'),
        id: 'spiderAddMnt',
        parentId: 'spider_mnt',
      },
    ],
  },
  {
    name: t('备份'),
    id: 'spider_copy',
    icon: 'db-icon-copy',
    children: [
      {
        name: t('库表备份'),
        id: 'spiderDbTableBackup',
        parentId: 'spider_copy',
      },
      {
        name: t('全库备份'),
        id: 'spiderDbBackup',
        parentId: 'spider_copy',
      },
    ],
  },
  {
    name: t('回档'),
    id: 'spider_fileback',
    icon: 'db-icon-rollback',
    children: [
      {
        name: t('定点构造'),
        id: 'spiderRollback',
        parentId: 'spider_fileback',
      },
      {
        name: t('构造实例'),
        id: 'spiderRollbackRecord',
        parentId: 'spider_fileback',
      },
      {
        name: t('闪回'),
        id: 'spiderFlashback',
        parentId: 'spider_fileback',
      },
    ],
  },
  {
    name: t('数据处理'),
    id: 'spider_data',
    icon: 'db-icon-data',
    children: [
      {
        name: t('清档'),
        id: 'spiderDbClear',
        parentId: 'spider_data',
      },
      {
        name: t('数据校验修复'),
        id: 'spiderChecksum',
        parentId: 'spider_data',
      },
    ],
  },
  {
    name: t('权限克隆'),
    id: 'spider_privilege',
    icon: 'db-icon-clone',
    children: [
      {
        name: t('客户端权限克隆'),
        id: 'spiderPrivilegeCloneClient',
        parentId: 'spider_privilege',
      },
      {
        name: t('DB实例权限克隆'),
        id: 'spiderPrivilegeCloneInst',
        parentId: 'spider_privilege',
      },
    ],
  },
  {
    name: t('克隆开区'),
    id: 'spider_openarea',
    icon: 'db-icon-clone',
    children: [
      {
        name: t('开区模版'),
        id: 'spiderOpenarea',
        parentId: 'spider_openarea',
      },
    ],
  },
];
