import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { DBTypes, TicketTypes } from '@common/const';

import { createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.MONGODB);

export const mongoToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    path: 'script-execute/:step?',
    name: 'MongoScriptExecute',
    meta: {
      activeMenu: 'mongoToolbox',
      navName: t('变更脚本执行'),
    },
    component: () => import('@views/db-manage/mongodb/script-execute/Index.vue'),
  },
  {
    path: 'shard-scale-up/:page?',
    name: 'MongoShardScaleUp',
    meta: {
      navName: t('扩容Shard节点数'),
    },
    component: () => import('@views/db-manage/mongodb/shard-scale-up/Index.vue'),
  },
  {
    path: 'shard-scale-down/:page?',
    name: 'MongoShardScaleDown',
    meta: {
      navName: t('缩容Shard节点数'),
    },
    component: () => import('@views/db-manage/mongodb/shard-scale-down/Index.vue'),
  },
  {
    path: 'capacity-change/:page?',
    name: 'MongoCapacityChange',
    meta: {
      navName: t('集群容量变更'),
    },
    component: () => import('@views/db-manage/mongodb/capacity-change/Index.vue'),
  },
  {
    path: 'proxy-scale-up/:page?',
    name: 'MongoProxyScaleUp',
    meta: {
      navName: t('扩容接入层'),
    },
    component: () => import('@views/db-manage/mongodb/proxy-scale-up/Index.vue'),
  },
  createRouteItem(TicketTypes.MONGODB_REDUCE_MONGOS, t('缩容接入层')),
  createRouteItem(TicketTypes.MONGODB_CUTOFF, t('整机替换')),
  createRouteItem(TicketTypes.MONGODB_PITR_RESTORE, t('定点构造')),
  {
    path: 'structure-instance/:page?',
    name: 'MongoStructureInstance',
    meta: {
      navName: t('构造实例'),
    },
    component: () => import('@views/db-manage/mongodb/structure-instance/Index.vue'),
  },
  {
    path: 'db-data-copy/:page?',
    name: 'MongoDbTableBackup',
    meta: {
      navName: t('库表备份'),
    },
    component: () => import('@views/db-manage/mongodb/db-table-backup/Index.vue'),
  },
  {
    path: 'db-data-copy-record/:page?',
    name: 'MongoDbBackup',
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
    path: 'mongodb',
    name: 'MongoDBManage',
    meta: {
      navName: t('集群管理'),
    },
    redirect: {
      name: 'MongoDBReplicaSetList',
    },
    component: () => import('@views/db-manage/mongodb/Index.vue'),
    children: [
      {
        path: 'replica-set-list',
        name: 'MongoDBReplicaSetList',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】副本集集群管理'),
        },
        component: () => import('@views/db-manage/mongodb/replica-set-list/Index.vue'),
      },
      {
        path: 'replica-set-instance-list',
        name: 'mongodbReplicaSetInstanceList',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】副本集集群实例视图'),
        },
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
      },
      {
        path: 'shared-cluster-list',
        name: 'MongoDBSharedClusterList',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】分片集群管理'),
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
        path: 'share-cluster-instance-list',
        name: 'mongodbShareClusterInstanceList',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】分片集群实例视图'),
        },
        component: () => import('@views/db-manage/mongodb/instance-list/index.vue'),
      },
      {
        path: 'permission',
        name: 'MongodbPermission',
        meta: {
          navName: t('【MongoDB】授权规则'),
        },
        component: () => import('@views/db-manage/mongodb/permission/Index.vue'),
      },
      {
        path: 'toolbox',
        name: 'MongoToolbox',
        meta: {
          fullscreen: true,
          navName: t('工具箱'),
        },
        redirect: {
          name: 'MongoScriptExecute',
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
