import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'mongodb',
    path: 'mongodb-manage',
    meta: {
      navName: t('集群管理'),
    },
    component: () => import('@views/mongodb-manage/mongodb-instance/index.vue'),
    children: [
      {
        name: 'mongodbInstance',
        path: 'mongodb-instance',
        meta: {
          navName: t('mongDB实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/mongodb-instance/index.vue'),
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
