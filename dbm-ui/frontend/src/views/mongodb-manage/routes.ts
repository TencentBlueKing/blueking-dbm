import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';
const routes: RouteRecordRaw[] = [
  {
    name: 'mongodb',
    path: 'instance-view',
    meta: {
      navName: t('实例视图'),
    },
    component: () => import('@views/mongodb-manage/instance-list/index.vue'),
    children: [
      {
        name: 'instanceList',
        path: 'instance-list',
        meta: {
          navName: t('mongDB实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/instance-list/index.vue'),
      },
    ],
  },
];

export default function getRoutes(controller: Record<MongoFunctions | 'mongodb', boolean>) {
  if (controller.mongodb !== true) {
    return [];
  }

  return routes;
}
