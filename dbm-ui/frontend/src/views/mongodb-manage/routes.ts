import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

export const mongoToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    path: 'script-execute/:step?',
    name: 'MongoScriptExecute',
    meta: {
      navName: t('变更脚本执行'),
      activeMenu: 'mongoToolbox',
    },
    component: () => import('@views/mongodb-manage/script-execute/Index.vue'),
  },
  {
    name: 'MongoShardScaleUp',
    path: 'shard-scale-up/:page?',
    meta: {
      navName: t('扩容Shard节点数'),
    },
    component: () => import('@views/mongodb-manage/shard-scale-up/Index.vue'),
  },
  {
    name: 'MongoShardScaleDown',
    path: 'shard-scale-down/:page?',
    meta: {
      navName: t('缩容Shard节点数'),
    },
    component: () => import('@views/mongodb-manage/shard-scale-down/Index.vue'),
  },
  {
    name: 'MongoCapacityChange',
    path: 'capacity-change/:page?',
    meta: {
      navName: t('集群容量变更'),
    },
    component: () => import('@views/mongodb-manage/capacity-change/Index.vue'),
  },
  {
    name: 'MongoProxyScaleUp',
    path: 'proxy-scale-up/:page?',
    meta: {
      navName: t('扩容接入层'),
    },
    component: () => import('@views/mongodb-manage/proxy-scale-up/Index.vue'),
  },
  {
    name: 'MongoProxyScaleDown',
    path: 'proxy-scale-down/:page?',
    meta: {
      navName: t('缩容接入层'),
    },
    component: () => import('@views/mongodb-manage/proxy-scale-down/Index.vue'),
  },
  {
    name: 'MongoDBReplace',
    path: 'db-replace/:page?',
    meta: {
      navName: t('整机替换'),
    },
    component: () => import('@views/mongodb-manage/db-replace/Index.vue'),
  },
  {
    name: 'MongoDBStructure',
    path: 'db-structure/:page?',
    meta: {
      navName: t('定点构造'),
    },
    component: () => import('@views/mongodb-manage/db-structure/Index.vue'),
  },
  {
    name: 'MongoStructureInstance',
    path: 'structure-instance/:page?',
    meta: {
      navName: t('构造实例'),
    },
    component: () => import('@views/mongodb-manage/structure-instance/Index.vue'),
  },
  {
    name: 'MongoDbTableBackup',
    path: 'db-data-copy/:page?',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/mongodb-manage/db-table-backup/Index.vue'),
  },
  {
    name: 'MongoDbBackup',
    path: 'db-data-copy-record/:page?',
    meta: {
      navName: t('全库备份'),
    },
    component: () => import('@views/mongodb-manage/db-backup/Index.vue'),
  },
  {
    path: 'db-clear/:page?',
    name: 'MongoDbClear',
    meta: {
      navName: t('清档'),
    },
    component: () => import('@views/mongodb-manage/db-clear/Index.vue'),
  },
];

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
    component: () => import('@views/mongodb-manage/Index.vue'),
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
      {
        name: 'MongoToolbox',
        path: 'toolbox',
        redirect: {
          name: 'MongoScriptExecute',
        },
        meta: {
          navName: t('工具箱'),
          fullscreen: true,
        },
        component: () => import('@views/mongodb-manage/toolbox/Index.vue'),
        children: mongoToolboxChildrenRoutes,
      },
    ],
  },
];

export default function getRoutes(controller: Record<MongoFunctions | 'mongodb', boolean>) {
  if (!controller.mongodb) {
    return [];
  }
  return routes;
}
