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

import FunctionControllModel, {
  type ExtractedControllerDataKeys,
  type MySQLFunctions,
} from '@services/model/function-controller/functionController';

import { AccountTypes } from '@common/const';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const tendbClusterInstanceRoute = {
  name: 'tendbClusterInstance',
  path: 'instance-list',
  meta: {
    navName: t('TendbCluster分布式集群_实例视图'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/tendb-cluster/instance-list/Index.vue'),
};

const spiderPartitionManageRoute = {
  path: 'partition-manage',
  name: 'spiderPartitionManage',
  meta: {
    navName: t('【TenDB Cluster】分区管理'),
  },
  component: () => import('@views/db-manage/tendb-cluster/partition-manage/Index.vue'),
};

const permissionManageRoutes = [
  {
    path: 'permission',
    name: 'spiderPermission',
    meta: {
      navName: t('【TendbCluster】授权规则'),
    },
    component: () => import('@views/db-manage/tendb-cluster/permission/Index.vue'),
  },
  {
    name: 'SpiderPermissionRetrieve',
    path: 'permission-retrieve',
    meta: {
      navName: t('权限查询'),
    },
    props: { accountType: AccountTypes.TENDBCLUSTER },
    component: () => import('@views/permission-retrieve/Index.vue'),
  },
  {
    path: 'whitelist',
    name: 'spiderWhitelist',
    meta: {
      navName: t('授权白名单'),
    },
    component: () => import('@views/whitelist/list/Index.vue'),
  },
];

const spiderToolboxRoute = {
  path: 'toolbox',
  name: 'spiderToolbox',
  meta: {
    navName: t('Spider_工具箱'),
    fullscreen: true,
  },
  redirect: {
    name: '',
  },
  component: () => import('@views/db-manage/tendb-cluster/toolbox/Index.vue'),
  children: [
    {
      path: 'sql-execute/:step?',
      name: 'spiderSqlExecute',
      meta: {
        navName: t('SQL变更执行'),
        dbConsole: 'tendbCluster.toolbox.sqlExecute',
      },
      component: () => import('@views/db-manage/tendb-cluster/sql-execute/Index.vue'),
    },
    {
      path: 'db-rename/:page?',
      name: 'spiderDbRename',
      meta: {
        navName: t('DB 重命名'),
        dbConsole: 'tendbCluster.toolbox.dbRename',
      },
      component: () => import('@views/db-manage/tendb-cluster/db-rename/Index.vue'),
    },
    {
      path: 'master-slave-swap/:page?',
      name: 'spiderMasterSlaveSwap',
      meta: {
        navName: t('主从互切'),
        dbConsole: 'tendbCluster.toolbox.masterSlaveSwap',
      },
      component: () => import('@views/db-manage/tendb-cluster/master-slave-swap/Index.vue'),
    },
    {
      path: 'master-failover/:page?',
      name: 'spiderMasterFailover',
      meta: {
        navName: t('主库故障切换'),
        dbConsole: 'tendbCluster.toolbox.masterFailover',
      },
      component: () => import('@views/db-manage/tendb-cluster/master-failover/Index.vue'),
    },
    {
      path: 'capacity-change/:page?',
      name: 'spiderCapacityChange',
      meta: {
        navName: t('集群容量变更'),
        dbConsole: 'tendbCluster.toolbox.capacityChange',
      },
      component: () => import('@views/db-manage/tendb-cluster/capacity-change/Index.vue'),
    },
    {
      name: 'SpiderProxyScaleUp',
      path: 'proxy-scale-up/:page?',
      meta: {
        navName: t('扩容接入层'),
        dbConsole: 'tendbCluster.toolbox.proxyScaleUp',
      },
      component: () => import('@views/db-manage/tendb-cluster/proxy-scale-up/Index.vue'),
    },
    {
      name: 'SpiderProxyScaleDown',
      path: 'proxy-scale-down/:page?',
      meta: {
        navName: t('缩容接入层'),
        dbConsole: 'tendbCluster.toolbox.proxyScaleDown',
      },
      component: () => import('@views/db-manage/tendb-cluster/proxy-scale-down/Index.vue'),
    },
    {
      name: 'SpiderProxySlaveApply',
      path: 'proxy-slave-apply/:page?',
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxySlaveApply',
        navName: t('部署只读接入层'),
      },
      component: () => import('@views/db-manage/tendb-cluster/proxy-slave-apply/Index.vue'),
    },
    {
      path: 'add-mnt/:page?',
      name: 'spiderAddMnt',
      meta: {
        navName: t('添加运维节点'),
        dbConsole: 'tendbCluster.toolbox.addMnt',
      },
      component: () => import('@views/db-manage/tendb-cluster/add-mnt/Index.vue'),
    },
    {
      path: 'db-table-backup/:page?',
      name: 'spiderDbTableBackup',
      meta: {
        navName: t('库表备份'),
        dbConsole: 'tendbCluster.toolbox.dbTableBackup',
      },
      component: () => import('@views/db-manage/tendb-cluster/db-table-backup/Index.vue'),
    },
    {
      path: 'db-backup/:page?',
      name: 'spiderDbBackup',
      meta: {
        navName: t('全库备份'),
        dbConsole: 'tendbCluster.toolbox.dbBackup',
      },
      component: () => import('@views/db-manage/tendb-cluster/db-backup/Index.vue'),
    },
    {
      path: 'flashback/:page?',
      name: 'spiderFlashback',
      meta: {
        navName: t('闪回'),
        dbConsole: 'tendbCluster.toolbox.flashback',
      },
      component: () => import('@views/db-manage/tendb-cluster/flashback/Index.vue'),
    },
    {
      path: 'TENDBCLUSTER_FLASHBACK/:page?',
      name: 'TENDBCLUSTER_FLASHBACK',
      meta: {
        navName: t('闪回'),
        dbConsole: 'tendbCluster.toolbox.flashback',
      },
      component: () => import('@views/db-manage/tendb-cluster/TENDBCLUSTER_FLASHBACK/Index.vue'),
    },
    {
      path: 'rollback/:page?',
      name: 'spiderRollback',
      meta: {
        navName: t('定点构造'),
        dbConsole: 'tendbCluster.toolbox.rollback',
      },
      component: () => import('@views/db-manage/tendb-cluster/rollback/Index.vue'),
    },
    {
      path: 'rollback-record',
      name: 'spiderRollbackRecord',
      meta: {
        navName: t('构造实例'),
        dbConsole: 'tendbCluster.toolbox.rollbackRecord',
      },
      component: () => import('@views/db-manage/tendb-cluster/rollback-record/Index.vue'),
    },
    {
      path: 'db-clear/:page?',
      name: 'spiderDbClear',
      meta: {
        navName: t('清档'),
        dbConsole: 'tendbCluster.toolbox.dbClear',
      },
      component: () => import('@views/db-manage/tendb-cluster/db-clear/Index.vue'),
    },
    {
      path: 'checksum/:page?',
      name: 'spiderChecksum',
      meta: {
        navName: t('数据校验修复'),
        dbConsole: 'tendbCluster.toolbox.checksum',
      },
      component: () => import('@views/db-manage/tendb-cluster/checksum/Index.vue'),
    },
    {
      path: 'privilege-clone-client/:page?',
      name: 'spiderPrivilegeCloneClient',
      meta: {
        navName: t('客户端权限克隆'),
        dbConsole: 'tendbCluster.toolbox.clientPermissionClone',
      },
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-client/Index.vue'),
    },
    {
      path: 'privilege-clone-inst/:page?',
      name: 'spiderPrivilegeCloneInst',
      meta: {
        navName: t('DB 实例权限克隆'),
        dbConsole: 'tendbCluster.toolbox.dbInstancePermissionClone',
      },
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-inst/Index.vue'),
    },
    {
      path: 'openarea-template',
      name: 'spiderOpenareaTemplate',
      meta: {
        navName: t('开区模版'),
        dbConsole: 'tendbCluster.toolbox.openareaTemplat',
      },
      component: () => import('@views/db-manage/tendb-cluster/openarea-template/Index.vue'),
    },
    {
      path: 'master-slave-clone/:page?',
      name: 'spiderMasterSlaveClone',
      meta: {
        navName: t('迁移主从'),
        dbConsole: 'tendbCluster.toolbox.masterSlaveClone',
      },
      component: () => import('@views/db-manage/tendb-cluster/master-slave-clone/Index.vue'),
    },
    {
      path: 'slave-rebuild/:page?',
      name: 'spiderSlaveRebuild',
      meta: {
        navName: t('重建从库'),
        dbConsole: 'tendbCluster.toolbox.slaveRebuild',
      },
      component: () => import('@views/db-manage/tendb-cluster/slave-rebuild/Index.vue'),
    },
    {
      name: 'SpiderWebconsole',
      path: 'webconsole',
      meta: {
        navName: 'Webconsole',
        dbConsole: 'tendbCluster.toolbox.webconsole',
      },
      component: () => import('@views/db-manage/tendb-cluster/webconsole/Index.vue'),
    },
  ],
};

const renderRoutes = [
  {
    path: 'tendb-cluster',
    name: 'SpiderManage',
    meta: {
      navName: t('Spider_集群管理'),
    },
    redirect: {
      name: 'tendbClusterList',
    },
    component: () => import('@views/db-manage/tendb-cluster/Index.vue'),
    children: [
      // {
      //   name: 'createSpiderModule',
      //   path: 'create-module/:bizId(\\d+)',
      //   meta: {
      //     navName: t('新建模块'),
      //   },
      //   component: () => import('@views/db-manage/tendb-cluster/apply/CreateModule.vue'),
      // },
      {
        name: 'tendbClusterList',
        path: 'cluster-list',
        meta: {
          navName: t('TendbCluster分布式集群_集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/tendb-cluster/cluster-list/Index.vue'),
      },
      {
        path: 'openarea-template-create',
        name: 'spiderOpenareaTemplateCreate',
        meta: {
          navName: t('新建开区模板'),
        },
        component: () => import('@views/db-manage/tendb-cluster/openarea-template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'spiderOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/db-manage/tendb-cluster/openarea-template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'spiderOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/db-manage/tendb-cluster/openarea-create/Index.vue'),
      },
    ] as RouteRecordRaw[],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const mysqlController = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');

  if (mysqlController.tendbcluster_toolbox) {
    const toolboxRoutes = spiderToolboxRoute.children.filter((item) => {
      const dbConsole = item.meta.dbConsole as ExtractedControllerDataKeys;
      return !funControllerData[dbConsole] || funControllerData[dbConsole].is_enabled;
    });

    if (toolboxRoutes.length > 0) {
      renderRoutes[0].children.push({
        ...spiderToolboxRoute,
        redirect: {
          name: toolboxRoutes[0].name,
        },
        children: toolboxRoutes,
      });
    }
  }

  if (checkDbConsole('tendbCluster.instanceManage')) {
    renderRoutes[0].children.push(tendbClusterInstanceRoute);
  }

  if (checkDbConsole('tendbCluster.partitionManage')) {
    renderRoutes[0].children.push(spiderPartitionManageRoute);
  }

  if (checkDbConsole('tendbCluster.permissionManage')) {
    renderRoutes[0].children.push(...permissionManageRoutes);
  }

  return renderRoutes;
}
