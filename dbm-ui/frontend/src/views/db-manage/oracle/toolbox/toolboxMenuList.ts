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

export const toolboxMenuList = [
  {
    children: [
      {
        dbConsoleValue: 'oracle.toolbox.sqlExecute',
        id: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
        name: t('变更SQL执行'),
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
        dbConsoleValue: 'oracle.toolbox.addSlave',
        desc: t('为所选上游实例新增 1 个从库'),
        id: TicketTypes.ORACLE_ADD_SLAVE,
        name: t('添加从库'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'oracle.toolbox.masterFailOver',
        desc: t('主库异常时强制提升从库为主，仅适用于主从集群'),
        id: TicketTypes.ORACLE_MASTER_FAIL_OVER,
        name: t('主库故障切换'),
        parentId: 'migrate',
      },
      {
        dbConsoleValue: 'oracle.toolbox.replaceHost',
        desc: t('替换所选主机，支持单节点以及主从集群的从库。'),
        id: TicketTypes.ORACLE_REPLACE_HOST,
        name: t('整机替换'),
        parentId: 'migrate',
      },
    ],
    icon: 'db-icon-cluster',
    id: 'migrate',
    name: t('集群维护'),
  },
];
