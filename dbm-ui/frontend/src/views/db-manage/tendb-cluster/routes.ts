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
  component: () => import('@views/db-manage/tendb-cluster/instance-list/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('TendbCluster分布式集群_实例视图'),
  },
  name: 'tendbClusterInstance',
  path: 'instance-list',
};

const spiderPartitionManageRoute = {
  component: () => import('@views/db-manage/tendb-cluster/partition-manage/Index.vue'),
  meta: {
    navName: t('【TenDB Cluster】分区管理'),
  },
  name: 'spiderPartitionManage',
  path: 'partition-manage',
};

const permissionManageRoutes = [
  {
    component: () => import('@views/db-manage/tendb-cluster/permission/Index.vue'),
    meta: {
      navName: t('【TendbCluster】授权规则'),
    },
    name: 'spiderPermission',
    path: 'permission',
  },
  {
    component: () => import('@views/permission-retrieve/Index.vue'),
    meta: {
      navName: t('权限查询'),
    },
    name: 'SpiderPermissionRetrieve',
    path: 'permission-retrieve',
    props: { accountType: AccountTypes.TENDBCLUSTER },
  },
  {
    component: () => import('@views/whitelist/list/Index.vue'),
    meta: {
      navName: t('授权白名单'),
    },
    name: 'spiderWhitelist',
    path: 'whitelist',
  },
];

const spiderToolboxRoute = {
  children: [
    {
      component: () => import('@views/db-manage/tendb-cluster/sql-execute/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.sqlExecute',
        navName: t('SQL变更执行'),
      },
      name: 'spiderSqlExecute',
      path: 'sql-execute/:step?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/db-rename/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbRename',
        navName: t('DB 重命名'),
      },
      name: 'spiderDbRename',
      path: 'db-rename/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/master-slave-swap/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.masterSlaveSwap',
        navName: t('主从互切'),
      },
      name: 'spiderMasterSlaveSwap',
      path: 'master-slave-swap/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/master-failover/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.masterFailover',
        navName: t('主库故障切换'),
      },
      name: 'spiderMasterFailover',
      path: 'master-failover/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/capacity-change/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.capacityChange',
        navName: t('集群容量变更'),
      },
      name: 'spiderCapacityChange',
      path: 'capacity-change/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/proxy-scale-up/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxyScaleUp',
        navName: t('扩容接入层'),
      },
      name: 'SpiderProxyScaleUp',
      path: 'proxy-scale-up/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/proxy-scale-down/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxyScaleDown',
        navName: t('缩容接入层'),
      },
      name: 'SpiderProxyScaleDown',
      path: 'proxy-scale-down/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/proxy-slave-apply/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxySlaveApply',
        navName: t('部署只读接入层'),
      },
      name: 'SpiderProxySlaveApply',
      path: 'proxy-slave-apply/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/add-mnt/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.addMnt',
        navName: t('添加运维节点'),
      },
      name: 'spiderAddMnt',
      path: 'add-mnt/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/db-table-backup/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbTableBackup',
        navName: t('库表备份'),
      },
      name: 'spiderDbTableBackup',
      path: 'db-table-backup/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/db-backup/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbBackup',
        navName: t('全库备份'),
      },
      name: 'spiderDbBackup',
      path: 'db-backup/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/flashback/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.flashback',
        navName: t('闪回'),
      },
      name: 'spiderFlashback',
      path: 'flashback/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/TENDBCLUSTER_FLASHBACK/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.flashback',
        navName: t('闪回'),
      },
      name: 'TENDBCLUSTER_FLASHBACK',
      path: 'TENDBCLUSTER_FLASHBACK/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/rollback/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.rollback',
        navName: t('定点构造'),
      },
      name: 'spiderRollback',
      path: 'rollback/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/rollback-record/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.rollbackRecord',
        navName: t('构造实例'),
      },
      name: 'spiderRollbackRecord',
      path: 'rollback-record',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/db-clear/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbClear',
        navName: t('清档'),
      },
      name: 'spiderDbClear',
      path: 'db-clear/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/checksum/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.checksum',
        navName: t('数据校验修复'),
      },
      name: 'spiderChecksum',
      path: 'checksum/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-client/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.clientPermissionClone',
        navName: t('客户端权限克隆'),
      },
      name: 'spiderPrivilegeCloneClient',
      path: 'privilege-clone-client/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-inst/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbInstancePermissionClone',
        navName: t('DB 实例权限克隆'),
      },
      name: 'spiderPrivilegeCloneInst',
      path: 'privilege-clone-inst/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/openarea-template/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.openareaTemplat',
        navName: t('开区模版'),
      },
      name: 'spiderOpenareaTemplate',
      path: 'openarea-template',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/master-slave-clone/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.masterSlaveClone',
        navName: t('迁移主从'),
      },
      name: 'spiderMasterSlaveClone',
      path: 'master-slave-clone/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/slave-rebuild/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.slaveRebuild',
        navName: t('重建从库'),
      },
      name: 'spiderSlaveRebuild',
      path: 'slave-rebuild/:page?',
    },
    {
      component: () => import('@views/db-manage/tendb-cluster/webconsole/Index.vue'),
      meta: {
        dbConsole: 'tendbCluster.toolbox.webconsole',
        navName: 'Webconsole',
      },
      name: 'SpiderWebconsole',
      path: 'webconsole',
    },
  ],
  component: () => import('@views/db-manage/tendb-cluster/toolbox/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('Spider_工具箱'),
  },
  name: 'spiderToolbox',
  path: 'toolbox',
  redirect: {
    name: '',
  },
};

const renderRoutes = [
  {
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
        component: () => import('@views/db-manage/tendb-cluster/cluster-list/Index.vue'),
        meta: {
          fullscreen: true,
          navName: t('TendbCluster分布式集群_集群管理'),
        },
        name: 'tendbClusterList',
        path: 'cluster-list',
      },
      {
        component: () => import('@views/db-manage/tendb-cluster/openarea-template-create/Index.vue'),
        meta: {
          navName: t('新建开区模板'),
        },
        name: 'spiderOpenareaTemplateCreate',
        path: 'openarea-template-create',
      },
      {
        component: () => import('@views/db-manage/tendb-cluster/openarea-template-create/Index.vue'),
        meta: {
          navName: t('编辑开区模板'),
        },
        name: 'spiderOpenareaTemplateEdit',
        path: 'openarea-template-edit/:id',
      },
      {
        component: () => import('@views/db-manage/tendb-cluster/openarea-create/Index.vue'),
        meta: {
          navName: t('新建开区'),
        },
        name: 'spiderOpenareaCreate',
        path: 'openarea-create/:id',
      },
    ] as RouteRecordRaw[],
    component: () => import('@views/db-manage/tendb-cluster/Index.vue'),
    meta: {
      navName: t('Spider_集群管理'),
    },
    name: 'SpiderManage',
    path: 'tendb-cluster',
    redirect: {
      name: 'tendbClusterList',
    },
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
        children: toolboxRoutes,
        redirect: {
          name: toolboxRoutes[0].name,
        },
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
