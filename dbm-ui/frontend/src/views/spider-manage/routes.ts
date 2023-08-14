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

import type { RouteRecordRaw } from 'vue-router';

import { MainViewRouteNames } from '@views/main-views/common/const';

import { t } from '@locales/index';

export const spiderToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    path: 'sql-execute/:page?',
    name: 'spiderSqlExecute',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('SQL变更执行'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'sql',
    },
    component: () => import('@views/spider-manage/sql-execute/Index.vue'),
  },
  {
    path: 'db-rename/:page?',
    name: 'spiderDbRename',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('DB 重命名'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'sql',
    },
    component: () => import('@views/spider-manage/db-rename/Index.vue'),
  },
  {
    path: 'master-slave-swap/:page?',
    name: 'spiderMasterSlaveSwap',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('主从互切'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'migrate',
    },
    component: () => import('@views/spider-manage/master-slave-swap/Index.vue'),
  },
  {
    path: 'master-failover/:page?',
    name: 'spiderMasterFailover',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('主库故障切换'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'migrate',
    },
    component: () => import('@views/spider-manage/master-failover/Index.vue'),
  },
  {
    path: 'capacity-change/:page?',
    name: 'spiderCapacityChange',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('集群容量变更'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'migrate',
    },
    component: () => import('@views/spider-manage/capacity-change/Index.vue'),
  },
  {
    name: 'SpiderProxyScaleUp',
    path: 'proxy-scale-up/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('扩容接入层'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'migrate',
    },
    component: () => import('@views/spider-manage/proxy-scale-up/Index.vue'),
  },
  {
    name: 'SpiderProxyScaleDown',
    path: 'proxy-scale-down/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('缩容接入层'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'migrate',
    },
    component: () => import('@views/spider-manage/proxy-scale-down/Index.vue'),
  },
  {
    name: 'SpiderProxySlaveApply',
    path: 'proxy-slave-apply/:page?',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('部署只读接入层'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'entry',
    },
    component: () => import('@views/spider-manage/proxy-slave-apply/Index.vue'),
  },
  {
    path: 'add-mnt/:page?',
    name: 'spiderAddMnt',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('添加运维节点'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'mnt',
    },
    component: () => import('@views/spider-manage/add-mnt/Index.vue'),
  },
  {
    path: 'db-table-backup/:page?',
    name: 'spiderDbTableBackup',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('库表备份'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'copy',
    },
    component: () => import('@views/spider-manage/db-table-backup/Index.vue'),
  },
  {
    path: 'db-backup/:page?',
    name: 'spiderDbBackup',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('全库备份'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'copy',
    },
    component: () => import('@views/spider-manage/db-backup/Index.vue'),
  },
  {
    path: 'flashback/:page?',
    name: 'spiderFlashback',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('闪回'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'fileback',
    },
    component: () => import('@views/spider-manage/flashback/Index.vue'),
  },
  {
    path: 'rollback/:page?',
    name: 'spiderRollback',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('定点构造'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'fileback',
    },
    component: () => import('@views/spider-manage/rollback/Index.vue'),
  },
  {
    path: 'db-clear/:page?',
    name: 'spiderDbClear',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('清档'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'data',
    },
    component: () => import('@views/spider-manage/db-clear/Index.vue'),
  },
  {
    path: 'checksum/:page?',
    name: 'spiderChecksum',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('数据校验修复'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'data',
    },
    component: () => import('@views/spider-manage/checksum/Index.vue'),
  },
  {
    path: 'privilege-clone-client/:page?',
    name: 'spiderPrivilegeCloneClient',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('客户端权限克隆'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'privilege',
    },
    component: () => import('@views/spider-manage/privilege-clone-client/Index.vue'),
  },
  {
    path: 'privilege-clone-inst/:page?',
    name: 'spiderPrivilegeCloneInst',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('DB 实例权限克隆'),
      isMenu: true,
      activeMenu: 'spiderToolbox',
      submenuId: 'privilege',
    },
    component: () => import('@views/spider-manage/privilege-clone-inst/Index.vue'),
  },
];

const renderRoutes: RouteRecordRaw[] = [
  {
    name: 'spiderApply',
    path: 'apply/spider',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('申请TendbCluster分布式集群部署'),
    },
    component: () => import('@views/spider-manage/apply/Index.vue'),
  },
  {
    name: 'createSpiderModule',
    path: 'apply/create-module/:bizId(\\d+)',
    meta: {
      routeParentName: MainViewRouteNames.SelfService,
      navName: t('新建模块'),
      isMenu: true,
    },
    component: () => import('@views/spider-manage/apply/CreateModule.vue'),
  },
  {
    path: 'spider-manage',
    name: 'SpiderManage',
    meta: {
      routeParentName: MainViewRouteNames.Database,
      navName: t('Spider_集群管理'),
      isMenu: true,
    },
    redirect: {
      name: 'tendbClusterManage',
    },
    component: () => import('@views/spider-manage/Index.vue'),
    children: [
      {
        name: 'tendbClusterManage',
        path: 'tendbcluster',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('TendbCluster分布式集群_集群管理'),
          isMenu: true,
          submenuId: 'tendb-cluster-manage',
        },
        component: () => import('@views/spider-manage/cluster-manage/cluster/MainView.vue'),
      },
      {
        name: 'tendbClusterInstanceView',
        path: 'tendbcluster-instance',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('TendbCluster分布式集群_实例视图'),
          isMenu: true,
          submenuId: 'tendb-cluster-manage',
        },
        component: () => import('@views/spider-manage/cluster-manage/instance/InstanceView.vue'),
      },
      {
        path: 'partition-manage',
        name: 'spiderPartitionManage',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('【TenDB Cluster】分区管理'),
          isMenu: true,
        },
        component: () => import('@views/spider-manage/partition-manage/Index.vue'),
      },
      {
        path: 'toolbox',
        name: 'spiderToolbox',
        meta: {
          routeParentName: MainViewRouteNames.Database,
          navName: t('Spider_工具箱'),
          isMenu: true,
        },
        redirect: {
          name: 'spiderSqlExecute',
        },
        component: () => import('@views/spider-manage/toolbox/Index.vue'),
        children: spiderToolboxChildrenRoutes,
      },
    ],
  },
];

export default function getRoutes() {
  return renderRoutes;
}
