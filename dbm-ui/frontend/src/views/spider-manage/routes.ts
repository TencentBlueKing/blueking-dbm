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

import { t } from '@locales/index';

export const spiderToolboxChildrenRoutes: RouteRecordRaw[] = [
  {
    path: 'sql-execute/:step?',
    name: 'spiderSqlExecute',
    meta: {
      navName: t('SQL变更执行'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/sql-execute/Index.vue'),
  },
  {
    path: 'db-rename/:page?',
    name: 'spiderDbRename',
    meta: {
      navName: t('DB 重命名'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/db-rename/Index.vue'),
  },
  {
    path: 'master-slave-swap/:page?',
    name: 'spiderMasterSlaveSwap',
    meta: {
      navName: t('主从互切'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/master-slave-swap/Index.vue'),
  },
  {
    path: 'master-failover/:page?',
    name: 'spiderMasterFailover',
    meta: {
      navName: t('主库故障切换'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/master-failover/Index.vue'),
  },
  {
    path: 'capacity-change/:page?',
    name: 'spiderCapacityChange',
    meta: {
      navName: t('集群容量变更'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/capacity-change/Index.vue'),
  },
  {
    name: 'SpiderProxyScaleUp',
    path: 'proxy-scale-up/:page?',
    meta: {
      navName: t('扩容接入层'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/proxy-scale-up/Index.vue'),
  },
  {
    name: 'SpiderProxyScaleDown',
    path: 'proxy-scale-down/:page?',
    meta: {
      navName: t('缩容接入层'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/proxy-scale-down/Index.vue'),
  },
  {
    name: 'SpiderProxySlaveApply',
    path: 'proxy-slave-apply/:page?',
    meta: {
      navName: t('部署只读接入层'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/proxy-slave-apply/Index.vue'),
  },
  {
    path: 'add-mnt/:page?',
    name: 'spiderAddMnt',
    meta: {
      navName: t('添加运维节点'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/add-mnt/Index.vue'),
  },
  {
    path: 'db-table-backup/:page?',
    name: 'spiderDbTableBackup',
    meta: {
      navName: t('库表备份'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/db-table-backup/Index.vue'),
  },
  {
    path: 'db-backup/:page?',
    name: 'spiderDbBackup',
    meta: {
      navName: t('全库备份'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/db-backup/Index.vue'),
  },
  {
    path: 'flashback/:page?',
    name: 'spiderFlashback',
    meta: {
      navName: t('闪回'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/flashback/Index.vue'),
  },
  {
    path: 'rollback/:page?',
    name: 'spiderRollback',
    meta: {
      navName: t('定点构造'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/rollback/Index.vue'),
  },
  {
    path: 'rollback-record',
    name: 'spiderRollbackRecord',
    meta: {
      navName: t('构造实例'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/rollback-record/Index.vue'),
  },
  {
    path: 'db-clear/:page?',
    name: 'spiderDbClear',
    meta: {
      navName: t('清档'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/db-clear/Index.vue'),
  },
  {
    path: 'checksum/:page?',
    name: 'spiderChecksum',
    meta: {
      navName: t('数据校验修复'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/checksum/Index.vue'),
  },
  {
    path: 'privilege-clone-client/:page?',
    name: 'spiderPrivilegeCloneClient',
    meta: {
      navName: t('客户端权限克隆'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/privilege-clone-client/Index.vue'),
  },
  {
    path: 'privilege-clone-inst/:page?',
    name: 'spiderPrivilegeCloneInst',
    meta: {
      navName: t('DB 实例权限克隆'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/privilege-clone-inst/Index.vue'),
  },
  {
    path: 'openarea-template',
    name: 'spiderOpenareaTemplate',
    meta: {
      navName: t('开区模版'),
      activeMenu: 'spiderToolbox',
    },
    component: () => import('@views/spider-manage/openarea-template/Index.vue'),
  },
];

const renderRoutes: RouteRecordRaw[] = [
  {
    path: 'spider-manage',
    name: 'SpiderManage',
    meta: {
      navName: t('Spider_集群管理'),
    },
    redirect: {
      name: 'tendbClusterList',
    },
    component: () => import('@views/spider-manage/Index.vue'),
    children: [
      {
        name: 'createSpiderModule',
        path: 'create-module/:bizId(\\d+)',
        meta: {
          navName: t('新建模块'),
        },
        component: () => import('@views/spider-manage/apply/CreateModule.vue'),
      },
      {
        name: 'tendbClusterList',
        path: 'list',
        meta: {
          navName: t('TendbCluster分布式集群_集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/spider-manage/list/Index.vue'),
      },
      {
        name: 'tendbClusterInstance',
        path: 'list-instance',
        meta: {
          navName: t('TendbCluster分布式集群_实例视图'),
          fullscreen: true,
        },
        component: () => import('@views/spider-manage/list-instance/Index.vue'),
      },
      {
        path: 'partition-manage',
        name: 'spiderPartitionManage',
        meta: {
          navName: t('【TenDB Cluster】分区管理'),
        },
        component: () => import('@views/spider-manage/partition-manage/Index.vue'),
      },
      {
        path: 'permission',
        name: 'spiderPermission',
        meta: {
          navName: t('授权规则'),
        },
        component: () => import('@views/spider-manage/permission/Index.vue'),
      },
      // {
      //   path: 'permission-list',
      //   name: 'spiderPermissionList',
      //   meta: {
      //     navName: t('授权列表'),
      //   },
      //   component: () => import('@views/spider-manage/permission-list/Index.vue'),
      // },
      {
        path: 'whitelist',
        name: 'spiderWhitelist',
        meta: {
          navName: t('授权白名单'),
        },
        component: () => import('@views/whitelist/list/Index.vue'),
      },
      {
        path: 'toolbox',
        name: 'spiderToolbox',
        meta: {
          navName: t('Spider_工具箱'),
          fullscreen: true,
        },
        redirect: {
          name: 'spiderSqlExecute',
        },
        component: () => import('@views/spider-manage/toolbox/Index.vue'),
        children: spiderToolboxChildrenRoutes,
      },
      {
        path: 'openarea-template-create',
        name: 'spiderOpenareaTemplateCreate',
        meta: {
          navName: t('新建开区模板'),
        },
        component: () => import('@views/spider-manage/openarea-template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'spiderOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/spider-manage/openarea-template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'spiderOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/spider-manage/openarea-create/Index.vue'),
      },
    ],
  },
];

export default function getRoutes() {
  return renderRoutes;
}
