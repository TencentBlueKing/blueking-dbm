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
    id: 'sql',
    icon: 'db-icon-mysql',
    children: [
      {
        name: t('变更SQL执行'),
        id: 'spiderSqlExecute',
        parentId: 'sql',
      },
      {
        name: t('DB 重命名'),
        id: 'spiderDbRename',
        parentId: 'sql',
      },
    ],
  },
  {
    name: t('集群维护'),
    id: 'migrate',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('主从互切'),
        id: 'spiderMasterSlaveSwap',
        parentId: 'migrate',
      },
      {
        name: t('主库故障切换'),
        id: 'spiderMasterFailover',
        parentId: 'migrate',
      },
    ],
  },
  {
    name: t('运维 Spider 管理'),
    id: 'mnt',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('添加运维节点'),
        id: 'spiderAddMnt',
        parentId: 'mnt',
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
        id: 'spiderDbTableBackup',
        parentId: 'copy',
      },
      {
        name: t('全库备份'),
        id: 'spiderDbBackup',
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
        id: 'spiderRollback',
        parentId: 'fileback',
      },
      {
        name: t('闪回'),
        id: 'spiderFlashback',
        parentId: 'fileback',
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
        id: 'spiderDbClear',
        parentId: 'data',
      },
      {
        name: t('数据校验修复'),
        id: 'spiderChecksum',
        parentId: 'data',
      },
    ],
  },
  {
    name: t('权限管理'),
    id: 'privileges',
    icon: 'db-icon-cluster',
    children: [
      {
        name: t('授权白名单'),
        id: 'spiderWhitelist',
        parentId: 'privileges',
      },
    ],
  },
];
