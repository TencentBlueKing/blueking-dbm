import type { RouteRecordRaw } from 'vue-router';

import type { MongoFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.MONGODB);

export const mongoToolboxChildrenRoutes: RouteRecordRaw[] = [
  createRouteItem(TicketTypes.MONGODB_EXEC_SCRIPT_APPLY, t('变更脚本执行')),
  createRouteItem(TicketTypes.MONGODB_ADD_SHARD, t('分片集群增加分片数')),
  createRouteItem(TicketTypes.MONGODB_REPLICA_ADD_SHARD_NODES, t('扩容Shard节点数')),
  createRouteItem(TicketTypes.MONGODB_SHARD_ADD_SHARD_NODES, t('扩容Shard节点数')),
  createRouteItem(TicketTypes.MONGODB_REDUCE_SHARD_NODES, t('缩容Shard节点数')),
  createRouteItem(TicketTypes.MONGODB_SCALE_UPDOWN, t('集群容量变更')),
  createRouteItem(TicketTypes.MONGODB_ADD_MONGOS, t('扩容接入层')),
  createRouteItem(TicketTypes.MONGODB_REDUCE_MONGOS, t('缩容接入层')),
  createRouteItem(TicketTypes.MONGODB_INSTANCE_FIX_STATUS, t('节点状态修复')),
  createRouteItem(TicketTypes.MONGODB_REPLICASET_CUTOFF, t('整机替换')),
  createRouteItem(TicketTypes.MONGODB_SHARD_CUTOFF, t('整机替换')),
  createRouteItem(TicketTypes.MONGODB_PITR_RESTORE, t('定点构造')),
  createRouteItem(TicketTypes.MONGODB_BACKUP, t('库表备份')),
  createRouteItem(TicketTypes.MONGODB_FULL_BACKUP, t('全库备份')),
  createRouteItem(TicketTypes.MONGODB_REMOVE_NS, t('清档')),
  createRouteItem(TicketTypes.MONGODB_REPLICASET_MIGRATE, t('迁移')),
  createRouteItem(TicketTypes.MONGODB_SHARD_MIGRATE, t('迁移')),
  createRouteItem(TicketTypes.MONGODB_DATA_EXPORT, t('数据导出')),
  {
    path: 'structure-instance/:page?',
    name: 'MongoStructureInstance',
    meta: {
      navName: t('构造实例'),
    },
    component: () => import('@views/db-manage/mongodb/structure-instance/Index.vue'),
  },
  {
    path: 'webconsole',
    name: 'MongodbWebconsole',
    meta: {
      navName: 'Webconsole',
    },
    component: () => import('@views/db-manage/mongodb/webconsole/Index.vue'),
  },
  {
    path: 'query-access-source',
    name: 'MongodbQueryAccessSource',
    meta: {
      navName: t('查询访问来源'),
    },
    component: () => import('@views/db-manage/mongodb/query-access-source/Index.vue'),
  },
];

const mongodbToolboxRouters: RouteRecordRaw[] = [
  {
    path: 'toolbox',
    name: 'MongoToolbox',
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    redirect: {
      name: TicketTypes.MONGODB_EXEC_SCRIPT_APPLY,
    },
    component: () => import('@views/db-manage/mongodb/toolbox/Index.vue'),
    children: [...mongoToolboxChildrenRoutes],
  },
];

const replicaSetListRouters: RouteRecordRaw[] = [
  {
    path: 'replica-set',
    name: 'MongoDBReplicaSet',
    meta: {
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
    ],
  },
];

const replicaSetInstanceRouters: RouteRecordRaw[] = [
  {
    path: 'instance-list',
    name: 'mongodbReplicaSetInstanceList',
    meta: {
      navName: t('【MongoDB】副本集集群实例视图'),
    },
    component: () => import('@views/db-manage/mongodb/replica-set-instance-list/Index.vue'),
  },
];

const sharedClusterListRouters: RouteRecordRaw[] = [
  {
    path: 'shared-cluster',
    name: 'MongoDBSharedCluster',
    meta: {
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
    ],
  },
];

const sharedClusterInstanceRouters: RouteRecordRaw[] = [
  {
    path: 'instance-list',
    name: 'mongodbShareClusterInstanceList',
    meta: {
      navName: t('【MongoDB】分片集群实例视图'),
    },
    component: () => import('@views/db-manage/mongodb/shared-cluster-instance-list/Index.vue'),
  },
];

const permissionManageRoutes: RouteRecordRaw[] = [
  {
    path: 'permission',
    name: 'MongodbPermission',
    meta: {
      navName: t('【MongoDB】授权规则'),
    },
    component: () => import('@views/db-manage/mongodb/permission/Index.vue'),
  },
];

const commonRouters: RouteRecordRaw[] = [
  {
    path: 'mongodb',
    name: 'MongoDBManage',
    meta: {
      dbType: DBTypes.MONGODB,
      navName: t('集群管理'),
    },
    redirect: {
      name: 'MongoDBReplicaSet',
    },
    component: () => import('@views/db-manage/mongodb/Index.vue'),
    children: [],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MongoFunctions, 'mongodb'>('mongodb');
  // 关闭 mongodb 功能
  if (controller.mongodb !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'MongoDBManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (controller.replicaSetList) {
    if (checkDbConsole('mongodb.replicaSetInstanceManage')) {
      replicaSetListRouters[0].children?.push(...replicaSetInstanceRouters);
    }
    renderRoutes.children?.push(...replicaSetListRouters);
  }

  if (controller.sharedClusterList) {
    if (checkDbConsole('mongodb.sharedClusterInstanceManage')) {
      sharedClusterListRouters[0].children?.push(...sharedClusterInstanceRouters);
    }
    renderRoutes.children?.push(...sharedClusterListRouters);
  }

  if (checkDbConsole('mongodb.permissionManage')) {
    renderRoutes.children?.push(...permissionManageRoutes);
  }

  if (controller.toolbox) {
    renderRoutes.children?.push(...mongodbToolboxRouters);
  }

  return commonRouters;
}
