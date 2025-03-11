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
import { registerBusinessModule, registerModule } from '@router';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export default function getRoutes() {
  registerModule([
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
  ]);
  registerBusinessModule([
    {
      path: 'alarm-events',
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
  ]);

  if (checkDbConsole('bizConfigManage.monitorStrategy')) {
    registerBusinessModule([
      {
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
      },
    ]);
  }

  if (checkDbConsole('bizConfigManage.alarmGroup')) {
    registerBusinessModule([
      {
        path: 'alarm-group',
        name: 'DBMonitorAlarmGroup',
        meta: {
          navName: t('告警组'),
        },
        component: () => import('@views/monitor-alarm/alarm-group/Index.vue'),
      },
    ]);
  }

  if (checkDbConsole('globalConfigManage.monitorStrategy')) {
    registerBusinessModule([
      {
        path: 'global-strategy',
        name: 'PlatGlobalStrategy',
        meta: {
          fullscreen: true,
          navName: t('全局策略'),
        },
        component: () => import('@views/monitor-alarm/global-strategy/Index.vue'),
      },
    ]);
  }
}
