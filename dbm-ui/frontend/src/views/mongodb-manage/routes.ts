import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

const routes: RouteRecordRaw[] = [
  {
    name: 'MongoDBManage',
    path: 'mongodb-manage',
    meta: {
      navName: t('集群管理'),
    },
    redirect: {
      name: 'MongoDBReplicaSetList',
    },
    component: () => import('@views/mongodb-manage/index.vue'),
    children: [
      {
        name: 'MongoDBReplicaSetList',
        path: 'replica-set-list',
        meta: {
          navName: t('【MongDB】副本集集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/replica-set-list/Index.vue'),
      },
      {
        name: 'MongoDBSharedClusterList',
        path: 'shared-cluster-list',
        meta: {
          navName: t('【MongDB】分片集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/shared-cluster-list/Index.vue'),
      },
      {
        name: 'mongodbInstance',
        path: 'mongodb-instance',
        meta: {
          navName: t('mongDB实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/mongodb-instance/index.vue'),
      },
      {
        name: 'MongodbPermission',
        path: 'permission',
        meta: {
          navName: t('【MongDB】授权规则'),
        },
        component: () => import('@views/mongodb-manage/permission/Index.vue'),
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
