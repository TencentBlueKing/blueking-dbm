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

import { AccountTypes, DBTypes, TicketTypes } from '@common/const';

import { checkDbConsole, createToolboxRoute } from '@utils';

import { t } from '@locales/index';

const { createRouteItem } = createToolboxRoute(DBTypes.TENDBCLUSTER);

const spiderSqlExecuteRoute = {
  path: 'sql-execute/:step?',
  name: 'spiderSqlExecute',
  meta: {
    navName: t('SQL变更执行'),
  },
  component: () => import('@views/db-manage/tendb-cluster/sql-execute/Index.vue'),
};

const spiderDbRenameRoute = createRouteItem(TicketTypes.TENDBCLUSTER_RENAME_DATABASE, t('DB重命名'));

const spiderMasterSlaveSwapRoute = createRouteItem(TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH, t('主从互切'));

const spiderMasterFailoverRoute = createRouteItem(TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER, t('主库故障切换'));

const spiderCapacityChangeRoute = createRouteItem(TicketTypes.TENDBCLUSTER_NODE_REBALANCE, t('集群容量变更'));

const spiderProxyScaleUpRoute = createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES, t('扩容接入层'));

const spiderProxyScaleDownRoute = createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES, t('缩容接入层'));

const spiderProxySlaveApplyRoute = createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY, t('部署只读接入层'));

const spiderAddMntRoute = createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY, t('添加运维节点'));

const spiderDbTableBackupRoute = createRouteItem(TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP, t('库表备份'));

const spiderDbBackupRoute = createRouteItem(TicketTypes.TENDBCLUSTER_FULL_BACKUP, t('全库备份'));

const spiderFlashbackRoute = createRouteItem(TicketTypes.TENDBCLUSTER_FLASHBACK, t('闪回'));

const spiderRollbackRoute = {
  path: 'rollback/:page?',
  name: 'spiderRollback',
  meta: {
    navName: t('定点构造'),
  },
  component: () => import('@views/db-manage/tendb-cluster/rollback/Index.vue'),
};

const spiderRollbackRecordRoute = {
  path: 'rollback-record',
  name: 'spiderRollbackRecord',
  meta: {
    navName: t('构造实例'),
  },
  component: () => import('@views/db-manage/tendb-cluster/rollback-record/Index.vue'),
};

const spiderDbClearRoute = createRouteItem(TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE, t('清档'));

const spiderChecksumRoute = createRouteItem(TicketTypes.TENDBCLUSTER_CHECKSUM, t('数据校验修复'));

const spiderPrivilegeCloneClientRoute = createRouteItem(
  TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES,
  t('客户端权限克隆'),
);

const spiderPrivilegeCloneInstRoute = createRouteItem(
  TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES,
  t('DB实例权限克隆'),
);

const spiderOpenareaTemplateRoute = {
  path: 'openarea-template',
  name: 'spiderOpenareaTemplate',
  meta: {
    navName: t('开区模版'),
  },
  component: () => import('@views/db-manage/tendb-cluster/openarea-template/Index.vue'),
};

const spiderMasterSlaveCloneRoute = createRouteItem(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER, t('迁移主从'));

const spiderSlaveRebuildRoute = createRouteItem(TicketTypes.TENDBCLUSTER_RESTORE_SLAVE, t('重建从库'));

const spiderWebconsoleRoute = {
  name: 'SpiderWebconsole',
  path: 'webconsole',
  meta: {
    navName: 'Webconsole',
  },
  component: () => import('@views/db-manage/tendb-cluster/webconsole/Index.vue'),
};

const toolboxDbConsoleRouteMap = {
  'tendbCluster.toolbox.sqlExecute': spiderSqlExecuteRoute,
  'tendbCluster.toolbox.dbRename': spiderDbRenameRoute,
  'tendbCluster.toolbox.rollback': spiderRollbackRoute,
  'tendbCluster.toolbox.rollbackRecord': spiderRollbackRecordRoute,
  'tendbCluster.toolbox.flashback': spiderFlashbackRoute,
  'tendbCluster.toolbox.dbTableBackup': spiderDbTableBackupRoute,
  'tendbCluster.toolbox.dbBackup': spiderDbBackupRoute,
  'tendbCluster.toolbox.clientPermissionClone': spiderPrivilegeCloneClientRoute,
  'tendbCluster.toolbox.dbInstancePermissionClone': spiderPrivilegeCloneInstRoute,
  'tendbCluster.toolbox.addMnt': spiderAddMntRoute,
  'tendbCluster.toolbox.proxySlaveApply': spiderProxySlaveApplyRoute,
  'tendbCluster.toolbox.masterSlaveSwap': spiderMasterSlaveSwapRoute,
  'tendbCluster.toolbox.masterFailover': spiderMasterFailoverRoute,
  'tendbCluster.toolbox.capacityChange': spiderCapacityChangeRoute,
  'tendbCluster.toolbox.proxyScaleDown': spiderProxyScaleDownRoute,
  'tendbCluster.toolbox.proxyScaleUp': spiderProxyScaleUpRoute,
  'tendbCluster.toolbox.dbClear': spiderDbClearRoute,
  'tendbCluster.toolbox.checksum': spiderChecksumRoute,
  'tendbCluster.toolbox.openareaTemplate': spiderOpenareaTemplateRoute,
  'tendbCluster.toolbox.slaveRebuild': spiderSlaveRebuildRoute,
  'tendbCluster.toolbox.masterSlaveClone': spiderMasterSlaveCloneRoute,
  'tendbCluster.toolbox.webconsole': spiderWebconsoleRoute,
};

const tendbClusterInstanceRoute = {
  name: 'tendbClusterInstance',
  path: 'instance-list',
  meta: {
    navName: t('TendbCluster分布式集群_实例视图'),
    fullscreen: true,
  },
  component: () => import('@views/db-manage/tendb-cluster/list-instance/Index.vue'),
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
  children: [] as RouteRecordRaw[],
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
        path: 'list',
        meta: {
          navName: t('TendbCluster分布式集群_集群管理'),
          fullscreen: true,
        },
        component: () => import('@views/db-manage/tendb-cluster/list/Index.vue'),
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
    Object.entries(toolboxDbConsoleRouteMap).forEach(([key, routeItem]) => {
      const dbConsoleValue = key as ExtractedControllerDataKeys;
      if (!funControllerData[dbConsoleValue] || funControllerData[dbConsoleValue].is_enabled) {
        spiderToolboxRoute.children!.push(routeItem);
        if (routeItem.name === 'spiderSqlExecute') {
          spiderToolboxRoute.redirect!.name = 'spiderSqlExecute';
        }
      }
    });

    if (!spiderToolboxRoute.redirect!.name) {
      spiderToolboxRoute.redirect!.name = (spiderToolboxRoute.children![0]?.name as string) ?? '';
    }

    renderRoutes[0].children.push(spiderToolboxRoute);
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
