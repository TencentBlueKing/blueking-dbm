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
  createRouteItem(TicketTypes.MONGODB_ADD_SHARD_NODES, t('扩容Shard节点数')),
  createRouteItem(TicketTypes.MONGODB_REDUCE_SHARD_NODES, t('缩容Shard节点数')),
  createRouteItem(TicketTypes.MONGODB_SCALE_UPDOWN, t('集群容量变更')),
  createRouteItem(TicketTypes.MONGODB_ADD_MONGOS, t('扩容接入层')),
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
  createRouteItem(TicketTypes.MONGODB_BACKUP, t('库表备份')),
  // {
  //   name: 'MongoDbBackup',
  //   path: 'db-data-copy-record/:page?',
  //   meta: {
  //     navName: t('全库备份'),
  //   },
  //   component: () => import('@views/db-manage/mongodb/db-backup/Index.vue'),
  // },
  createRouteItem(TicketTypes.MONGODB_FULL_BACKUP, t('全库备份')),
  createRouteItem(TicketTypes.MONGODB_REMOVE_NS, t('清档')),
  {
    path: 'webconsole',
    name: 'MongodbWebconsole',
    meta: {
      navName: 'Webconsole',
    },
    component: () => import('@views/db-manage/mongodb/webconsole/Index.vue'),
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
      name: 'MongoDBReplicaSet',
    },
    component: () => import('@views/db-manage/mongodb/Index.vue'),
    children: [
      {
        path: 'replica-set',
        name: 'MongoDBReplicaSet',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】副本集集群管理'),
        },
        redirect: {
          name: 'MongoDBReplicaSetList',
        },
        component: () => import('@views/db-manage/mongodb/Index.vue'),
        children: [
          {
            path: 'list/:clusterId?',
            name: 'MongoDBReplicaSetList',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】副本集集群管理'),
            },
            component: () => import('@views/db-manage/mongodb/replica-set-list/Index.vue'),
          },
          {
            path: 'detail/:clusterId',
            name: 'MongoDBReplicaSetDetail',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】副本集详细'),
            },
            component: () => import('@views/db-manage/mongodb/replica-set-detail/Index.vue'),
          },
          {
            path: 'instance-list',
            name: 'mongodbReplicaSetInstanceList',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】副本集集群实例视图'),
            },
            component: () => import('@views/db-manage/mongodb/instance-list/Index.vue'),
          },
        ],
      },
      {
        path: 'shared-cluster',
        name: 'MongoDBSharedCluster',
        meta: {
          fullscreen: true,
          navName: t('【MongoDB】分片集群管理'),
        },
        redirect: {
          name: 'MongoDBSharedClusterList',
        },
        component: () => import('@views/db-manage/mongodb/Index.vue'),
        children: [
          {
            path: 'list/:clusterId?',
            name: 'MongoDBSharedClusterList',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】分片集群管理'),
            },
            component: () => import('@views/db-manage/mongodb/shared-cluster-list/Index.vue'),
          },
          {
            path: 'detail/:clusterId',
            name: 'MongoDBSharedClusterDetail',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】分片集群详情'),
            },
            component: () => import('@views/db-manage/mongodb/shared-cluster-detail/Index.vue'),
          },
          {
            path: 'instance-list',
            name: 'mongodbShareClusterInstanceList',
            meta: {
              fullscreen: true,
              navName: t('【MongoDB】分片集群实例视图'),
            },
            component: () => import('@views/db-manage/mongodb/instance-list/Index.vue'),
          },
        ],
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
        children: [
          ...mongoToolboxChildrenRoutes,
          {
            path: 'toolbox-result/:ticketType?/:ticketId?',
            name: 'MongodbToolboxResult',
            component: () => import('@views/db-manage/common/toolbox-result/Index.vue'),
          },
        ],
      },
    ],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MongoFunctions, 'mongodb'>('mongodb');
  return controller.mongodb ? routes : [];
}
