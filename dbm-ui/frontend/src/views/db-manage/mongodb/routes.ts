import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { t } from '@locales/index';

export const mongoToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    component: () => import('@views/db-manage/mongodb/script-execute/Index.vue'),
    meta: {
      activeMenu: 'mongoToolbox',
      navName: t('变更脚本执行'),
    },
    name: 'MongoScriptExecute',
    path: 'script-execute/:step?',
  },
  {
    component: () => import('@views/db-manage/mongodb/shard-scale-up/Index.vue'),
    meta: {
      navName: t('扩容Shard节点数'),
    },
    name: 'MongoShardScaleUp',
    path: 'shard-scale-up/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/shard-scale-down/Index.vue'),
    meta: {
      navName: t('缩容Shard节点数'),
    },
    name: 'MongoShardScaleDown',
    path: 'shard-scale-down/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/capacity-change/Index.vue'),
    meta: {
      navName: t('集群容量变更'),
    },
    name: 'MongoCapacityChange',
    path: 'capacity-change/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/proxy-scale-up/Index.vue'),
    meta: {
      navName: t('扩容接入层'),
    },
    name: 'MongoProxyScaleUp',
    path: 'proxy-scale-up/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/proxy-scale-down/Index.vue'),
    meta: {
      navName: t('缩容接入层'),
    },
    name: 'MongoProxyScaleDown',
    path: 'proxy-scale-down/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/db-replace/Index.vue'),
    meta: {
      navName: t('整机替换'),
    },
    name: 'MongoDBReplace',
    path: 'db-replace/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/db-structure/Index.vue'),
    meta: {
      navName: t('定点构造'),
    },
    name: 'MongoDBStructure',
    path: 'db-structure/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/structure-instance/Index.vue'),
    meta: {
      navName: t('构造实例'),
    },
    name: 'MongoStructureInstance',
    path: 'structure-instance/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/db-table-backup/Index.vue'),
    meta: {
      navName: t('库表备份'),
    },
    name: 'MongoDbTableBackup',
    path: 'db-data-copy/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/db-backup/Index.vue'),
    meta: {
      navName: t('全库备份'),
    },
    name: 'MongoDbBackup',
    path: 'db-data-copy-record/:page?',
  },
  {
    component: () => import('@views/db-manage/mongodb/db-clear/Index.vue'),
    meta: {
      navName: t('清档'),
    },
    name: 'MongoDbClear',
    path: 'db-clear/:page?',
  },
];

const routes: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('@views/db-manage/mongodb/replica-set-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】副本集集群管理'),
        },
        name: 'MongoDBReplicaSetList',
        path: 'replica-set-list',
      },
      {
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】副本集集群实例视图'),
        },
        name: 'mongodbReplicaSetInstanceList',
        path: 'replica-set-instance-list',
      },
      {
        component: () => import('@views/db-manage/mongodb/shared-cluster-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】分片集群管理'),
        },
        name: 'MongoDBSharedClusterList',
        path: 'shared-cluster-list',
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
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】分片集群实例视图'),
        },
        name: 'mongodbShareClusterInstanceList',
        path: 'share-cluster-instance-list',
      },
      {
        component: () => import('@views/db-manage/mongodb/permission/Index.vue'),
        meta: {
          navName: t('【MongoDB】授权规则'),
        },
        name: 'MongodbPermission',
        path: 'permission',
      },
      {
        children: mongoToolboxChildrenRoutes,
        component: () => import('@views/db-manage/mongodb/toolbox/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('工具箱'),
        },
        name: 'MongoToolbox',
        path: 'toolbox',
        redirect: {
          name: 'MongoScriptExecute',
        },
      },
    ],
    component: () => import('@views/db-manage/mongodb/Index.vue'),
    meta: {
      navName: t('集群管理'),
    },
    name: 'MongoDBManage',
    path: 'mongodb',
    redirect: {
      name: 'MongoDBReplicaSetList',
    },
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MongoFunctions, 'mongodb'>('mongodb');
  return controller.mongodb ? routes : [];
}
