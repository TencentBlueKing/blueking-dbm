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

import { MainViewRouteNames } from './common/const';
import { getRouteChildren } from './common/getRouteChildren';

const mainViewChildren = getRouteChildren();

export const serviceRoutes = [
  {
    name: MainViewRouteNames.SelfService,
    path: '/self-service',
    redirect: {
      name: 'SelfServiceApply',
    },
    meta: {
      navName: t('服务自助'),
    },
    component: () => import('@views/main-views/pages/Services.vue'),
    children: [
      ...mainViewChildren[MainViewRouteNames.SelfService],
      {
        name: 'EsApply',
        path: 'es',
        meta: {
          routeParentName: MainViewRouteNames.SelfService,
          navName: t('申请ES集群部署'),
          activeMenu: 'SelfServiceApply',
        },
        component: () => import('@views/es-manage/apply/Index.vue'),
      },
      {
        name: 'HdfsApply',
        path: 'hdfs',
        meta: {
          routeParentName: MainViewRouteNames.SelfService,
          navName: t('申请HDFS集群部署'),
          activeMenu: 'SelfServiceApply',
        },
        component: () => import('@views/hdfs-manage/apply/Index.vue'),
      },
      {
        name: 'KafkaApply',
        path: 'kafka',
        meta: {
          routeParentName: MainViewRouteNames.SelfService,
          navName: t('申请Kafka集群部署'),
          activeMenu: 'SelfServiceApply',
        },
        component: () => import('@views/kafka-manage/apply/Index.vue'),
      },
      {
        name: 'PulsarApply',
        path: 'pulsar',
        meta: {
          routeParentName: MainViewRouteNames.SelfService,
          navName: t('申请Pulsar集群部署'),
          activeMenu: 'SelfServiceApply',
        },
        component: () => import('@views/pulsar-manage/apply/index.vue'),
      },
    ],
  },
];

export const databaseRoutes = [
  {
    name: MainViewRouteNames.Database,
    path: '/database/:bizId(\\d+)',
    redirect: {
      name: 'DatabaseTendbsingle',
    },
    meta: {
      navName: t('数据库管理'),
    },
    component: () => import('@views/main-views/pages/Database.vue'),
    children: mainViewChildren[MainViewRouteNames.Database],
  },
];

export const platformRoutes = [
  {
    name: MainViewRouteNames.Platform,
    path: '/platform',
    redirect: {
      name: 'PlatConf',
    },
    meta: {
      navName: t('平台管理'),
    },
    component: () => import('@views/main-views/pages/Platform.vue'),
    children: mainViewChildren[MainViewRouteNames.Platform],
  },
];

export default [...serviceRoutes, ...databaseRoutes, ...platformRoutes];
