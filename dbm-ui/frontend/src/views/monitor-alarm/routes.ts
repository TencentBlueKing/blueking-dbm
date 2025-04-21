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
import { type RouteRecordRaw } from 'vue-router';

import { registerBusinessModule, registerModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export default function getRoutes() {
  const alarmGlobalRoutes: RouteRecordRaw[] = [
    {
      path: 'alarm-events-todo',
      name: 'AlarmEventsTodo',
      meta: {
        fullscreen: true,
        navName: t('告警事件待办'),
      },
      component: () => import('@views/monitor-alarm/alarm-events-todo/Index.vue'),
    },
    {
      path: 'alarm-events-global',
      name: 'AlarmEventsGlobal',
      meta: {
        fullscreen: true,
        navName: t('告警事件'),
      },
      component: () => import('@views/monitor-alarm/alarm-events/Index.vue'),
    },
  ];

  if (checkDbConsole('globalConfigManage.monitorStrategy')) {
    alarmGlobalRoutes.push({
      path: 'global-strategy',
      name: 'PlatGlobalStrategy',
      meta: {
        fullscreen: true,
        navName: t('全局策略'),
      },
      component: () => import('@views/monitor-alarm/global-strategy/Index.vue'),
    });
  }
  registerModule(alarmGlobalRoutes);

  const alarmManageBizRoute: RouteRecordRaw = {
    path: 'alarm-manage',
    name: 'AlarmManage',
    meta: {
      navName: t('告警'),
    },
    component: () => import('@views/monitor-alarm/Index.vue'),
    children: [
      {
        path: 'list',
        name: 'AlarmEvents',
        meta: {
          fullscreen: true,
          navName: t('告警事件'),
        },
        component: () => import('@views/monitor-alarm/alarm-events/Index.vue'),
      },
      {
        path: 'alarm-shield',
        name: 'AlarmShield',
        meta: {
          fullscreen: true,
          navName: t('告警屏蔽'),
        },
        component: () => import('@views/monitor-alarm/alarm-shield/Index.vue'),
      },
    ],
  };

  if (checkDbConsole('bizConfigManage.monitorStrategy')) {
    alarmManageBizRoute.children!.push({
      path: 'monitor-strategy',
      name: 'DBMonitorStrategy',
      meta: {
        fullscreen: true,
        navName: t('监控策略'),
        tags: [
          {
            text: t('业务'),
            theme: 'info',
          },
        ],
      },
      component: () => import('@views/monitor-alarm/monitor-strategy/Index.vue'),
    });
  }

  if (checkDbConsole('bizConfigManage.alarmGroup')) {
    alarmManageBizRoute.children!.push({
      path: 'alarm-group',
      name: 'DBMonitorAlarmGroup',
      meta: {
        navName: t('告警组'),
      },
      component: () => import('@views/monitor-alarm/alarm-group/Index.vue'),
    });
  }

  registerBusinessModule([alarmManageBizRoute]);
}
