import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

export const mongoToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    path: 'script-execute/:step?',
    name: 'MongoScriptExecute',
    meta: {
      navName: t('变更脚本执行'),
      activeMenu: 'mongoToolbox',
    },
    component: () => import('@views/db-manage/mongodb/script-execute/Index.vue'),
  },
  {
    name: 'MongoShardScaleUp',
    path: 'shard-scale-up/:page?',
    meta: {
      navName: t('扩容Shard节点数'),
    },
    component: () => import('@views/db-manage/mongodb/shard-scale-up/Index.vue'),
  },
  {
    name: 'MongoShardScaleDown',
    path: 'shard-scale-down/:page?',
    meta: {
      navName: t('缩容Shard节点数'),
    },
    component: () => import('@views/db-manage/mongodb/shard-scale-down/Index.vue'),
  },
  {
    name: 'MongoCapacityChange',
    path: 'capacity-change/:page?',
    meta: {
      navName: t('集群容量变更'),
    },
    component: () => import('@views/db-manage/mongodb/capacity-change/Index.vue'),
  },
  {
    name: 'MongoProxyScaleUp',
    path: 'proxy-scale-up/:page?',
    meta: {
      navName: t('扩容接入层'),
    },
    component: () => import('@views/db-manage/mongodb/proxy-scale-up/Index.vue'),
  },
  {
    name: 'MongoProxyScaleDown',
    path: 'proxy-scale-down/:page?',
    meta: {
      navName: t('缩容接入层'),
    },
    component: () => import('@views/db-manage/mongodb/proxy-scale-down/Index.vue'),
  },
  {
    name: 'MongoDBReplace',
    path: 'db-replace/:page?',
    meta: {
      navName: t('整机替换'),
    },
    component: () => import('@views/db-manage/mongodb/db-replace/Index.vue'),
  },
  {
    name: 'MongoDBStructure',
    path: 'db-structure/:page?',
    meta: {
      navName: t('定点构造'),
    },
    component: () => import('@views/db-manage/mongodb/db-structure/Index.vue'),
  },
  {
    name: 'MongoStructureInstance',
    path: 'structure-instance/:page?',
    meta: {
      navName: t('构造实例'),
    },
    component: () => import('@views/db-manage/mongodb/structure-instance/Index.vue'),
  },
  {
    name: 'MongoDbTableBackup',
    path: 'db-data-copy/:page?',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/db-manage/mongodb/db-table-backup/Index.vue'),
  },
  {
    name: 'MongoDbBackup',
    path: 'db-data-copy-record/:page?',
    meta: {
      navName: t('全库备份'),
    },
    component: () => import('@views/db-manage/mongodb/db-backup/Index.vue'),
  },
  {
    path: 'db-clear/:page?',
    name: 'MongoDbClear',
    meta: {
      navName: t('清档'),
    },
    component: () => import('@views/db-manage/mongodb/db-clear/Index.vue'),
  },
];

const routes: RouteRecordRaw[] = [
  {
    name: 'MongoDBManage',
    path: 'mongodb',
    meta: {
      navName: t('集群管理'),
    },
    redirect: {
      name: 'MongoDBReplicaSetList',
    },
    component: () => import('@views/db-manage/mongodb/Index.vue'),
    children: [
      {
        name: 'MongoDBReplicaSetList',
        path: 'replica-set-list',
        meta: {
          navName: t('【MongoDB】副本集集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/mongodb/replica-set-list/Index.vue'),
      },
      {
        name: 'mongodbReplicaSetInstanceList',
        path: 'replica-set-instance-list',
        meta: {
          navName: t('【MongoDB】副本集集群实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
      },
      {
        name: 'MongoDBSharedClusterList',
        path: 'shared-cluster-list',
        meta: {
          navName: t('【MongoDB】分片集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/mongodb/shared-cluster-list/Index.vue'),
      },
      // {
      //   name: 'mongodbInstance',
      //   path: 'mongodb-instance',
      //   meta: {
      //     navName: t('【MongoDB】实例视图'),
      //     fullscreen: true,
      //   },
      //   component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
      // },
      {
        name: 'mongodbShareClusterInstanceList',
        path: 'share-cluster-instance-list',
        meta: {
          navName: t('【MongoDB】分片集群实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
      },
      {
        name: 'MongodbPermission',
        path: 'permission',
        meta: {
          navName: t('【MongoDB】授权规则'),
        },
        component: () => import('@views/db-manage/mongodb/permission/Index.vue'),
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
        component: () => import('@views/db-manage/mongodb/toolbox/Index.vue'),
        children: mongoToolboxChildrenRoutes,
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MongoFunctions, 'mongodb'>('mongodb');
  return controller.mongodb ? routes : [];
}
