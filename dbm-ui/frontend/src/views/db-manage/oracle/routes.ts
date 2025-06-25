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
import type { RouteRecordRaw } from 'vue-router';

import type { OracleFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { DBTypes, TicketTypes } from '@common/const';

import { createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.ORACLE);

const singleRoutes: RouteRecordRaw[] = [
  {
    path: 'oraclesingle',
    name: 'oraclesingle',
    redirect: {
      name: 'OracleSingleClusterList',
    },
    component: () => import('@views/db-manage/oracle/Index.vue'),
    children: [
      {
        path: 'single-cluster-list',
        name: 'OracleSingleClusterList',
        meta: {
          fullscreen: true,
          navName: t('【Oracle】单节点集群管理'),
        },
        component: () => import('@views/db-manage/oracle/single-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'OracleSingleDetail',
        meta: {
          fullscreen: true,
          navName: t('【Oracle】单节点集群详情'),
        },
        component: () => import('@views/db-manage/oracle/single-cluster-detail/Index.vue'),
      },
    ],
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    path: 'oracleha',
    name: 'oracleha',
    redirect: {
      name: 'OracleHaClusterList',
    },
    component: () => import('@views/db-manage/oracle/Index.vue'),
    children: [
      {
        path: 'ha-cluster-list',
        name: 'OracleHaClusterList',
        meta: {
          fullscreen: true,
          navName: t('【Oracle】主从集群管理'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/oracle/ha-cluster-list/Index.vue'),
      },
      {
        path: 'detail/:clusterId',
        name: 'OracleHaDetail',
        meta: {
          fullscreen: true,
          navName: t('【Oracle】主从集群详情'),
        },
        component: () => import('@views/db-manage/oracle/ha-cluster-detail/Index.vue'),
      },
      {
        path: 'ha-instance-list',
        name: 'OracleHaInstanceList',
        meta: {
          fullscreen: true,
          navName: t('【Oracle】实例视图'),
        },
        component: () => import('@views/db-manage/oracle/ha-instance-list/Index.vue'),
      },
    ],
  },
];

const commonRouters: RouteRecordRaw[] = [
  {
    path: 'oracle',
    name: 'OracleManage',
    meta: {
      fullscreen: true,
      navName: t('【Oracle】主从集群管理'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'OracleHaClusterList',
    },
    component: () => import('@views/db-manage/oracle/Index.vue'),
    children: [],
  },
];

const toolboxRouters: RouteRecordRaw[] = [
  {
    path: 'toolbox',
    name: 'OracleToolbox',
    meta: {
      fullscreen: true,
      navName: t('Oracle 工具箱'),
    },
    redirect: {
      name: TicketTypes.ORACLE_EXEC_SCRIPT_APPLY,
    },
    component: () => import('@views/db-manage/oracle/toolbox/Index.vue'),
    children: [
      {
        path: 'toolbox-result/:ticketType?/:ticketId?',
        name: 'OracleToolboxResult',
        component: () => import('@views/db-manage/common/toolbox-result/Index.vue'),
      },
      createRouteItem(TicketTypes.ORACLE_EXEC_SCRIPT_APPLY, t('变更SQL执行')),
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<OracleFunctions, 'oracle'>('oracle');
  // 关闭 oracle 功能
  if (controller.oracle !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'OracleManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (controller.oracle_single_none) {
    renderRoutes.children?.push(...singleRoutes);
  }
  if (controller.oracle_primary_standby) {
    renderRoutes.children?.push(...haRoutes);
  }

  if (controller.toolbox) {
    renderRoutes.children?.push(...toolboxRouters);
  }

  return commonRouters;
}
