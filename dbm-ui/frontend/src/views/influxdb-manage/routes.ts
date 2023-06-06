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

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'SelfServiceApplyInfluxDB',
    path: 'apply/influxdb',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请InfluxDB集群部署'),
      activeMenu: 'SelfServiceApply',
    },
    component: () => import('@views/influxdb-manage/apply/index.vue'),
  },
  {
    name: 'InfluxDBInstances',
    path: 'influxdb-instances/:groupId(\\d+)?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('InfluxDB实例管理'),
      isMenu: true,
    },
    component: () => import('@views/influxdb-manage/Index.vue'),
  },
  {
    name: 'InfluxDBInstDetails',
    path: 'influxdb-inst-details/:instId(\\d+)',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('InfluxDB实例详情'),
      isMenu: false,
      activeMenu: 'InfluxDBInstances',
    },
    component: () => import('@views/influxdb-manage/details/Details.vue'),
  },
  {
    name: 'SelfServiceApplyTenDB',
    path: 'apply/tendb',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请TenDB Cluster集群部署'),
      activeMenu: 'SelfServiceApply',
    },
    component: () => import('@views/tendb-manage/apply/index.vue'),
  },
];

export default routes;
