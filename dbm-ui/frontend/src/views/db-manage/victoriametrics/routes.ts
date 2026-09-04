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
    path: 'victoriametrics',
    name: 'VictoriaMetricsManage',
    meta: {
      navName: t('VictoriaMetrics'),
      skeleton: 'clusterList',
    },
    redirect: {
      name: 'VictoriametricsStandardList',
    },
    component: () => import('@views/db-manage/victoriametrics/Index.vue'),
    children: [
      {
        path: 'standard-list/:clusterId?',
        name: 'VictoriametricsStandardList',
        meta: {
          navName: t('VictoriaMetrics 标准集群'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/victoriametrics/standard-cluster-list/Index.vue'),
      },
      {
        path: 'standard-detail/:clusterId',
        name: 'VictoriametricsStandardDetail',
        meta: {
          fullscreen: true,
          navName: t('VictoriaMetrics 标准集群详情'),
        },
        component: () => import('@views/db-manage/victoriametrics/standard-cluster-detail/Index.vue'),
      },
      {
        path: 'query-list/:clusterId?',
        name: 'VictoriametricsQueryList',
        meta: {
          navName: t('VictoriaMetrics 查询集群'),
          skeleton: 'clusterList',
        },
        component: () => import('@views/db-manage/victoriametrics/query-cluster-list/Index.vue'),
      },
      {
        path: 'query-detail/:clusterId',
        name: 'VictoriametricsQueryDetail',
        meta: {
          fullscreen: true,
          navName: t('VictoriaMetrics 查询集群详情'),
        },
        component: () => import('@views/db-manage/victoriametrics/query-cluster-detail/Index.vue'),
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<K8sFunctions, 'k8s'>('k8s');
  return controller.k8s_victoriametrics ? routes : [];
}
