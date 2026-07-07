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

import type { K8sFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    path: 'surrealdb',
    name: 'SurrealDBManage',
    meta: {
      navName: t('SurrealDB 集群'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'SurrealdbHaList',
    },
    component: () => import('@views/db-manage/surrealdb/Index.vue'),
    children: [
      {
        path: 'ha-list/:clusterId?',
        name: 'SurrealdbHaList',
        meta: {
          navName: t('SurrealDB 集群'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/surrealdb/ha-cluster-list/Index.vue'),
      },
      {
        path: 'ha-detail/:clusterId',
        name: 'SurrealdbHaDetail',
        meta: {
          fullscreen: true,
          navName: t('SurrealDB 主从 集群详情'),
        },
        component: () => import('@views/db-manage/surrealdb/ha-cluster-detail/Index.vue'),
      },
      {
        path: 'single-list/:clusterId?',
        name: 'SurrealdbSingleList',
        meta: {
          navName: t('SurrealDB 单节点'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/surrealdb/single-cluster-list/Index.vue'),
      },
      {
        path: 'single-detail/:clusterId',
        name: 'SurrealdbSingleDetail',
        meta: {
          fullscreen: true,
          navName: t('SurrealDB 单节点 集群详情'),
        },
        component: () => import('@views/db-manage/surrealdb/single-cluster-detail/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<K8sFunctions, 'k8s'>('k8s');
  return controller.k8s_surrealdb ? routes : [];
}
