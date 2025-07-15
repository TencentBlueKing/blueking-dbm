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

const { createRouteItem } = createToolboxRoute(DBTypes.TENDBCLUSTER);

import { t } from '@locales/index';

const tendbClusterInstanceRoute = {
  path: 'instance-list',
  name: 'tendbClusterInstance',
  meta: {
    fullscreen: true,
    navName: t('TendbCluster分布式集群_实例视图'),
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
    path: 'permission-retrieve',
    name: 'SpiderPermissionRetrieve',
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
    fullscreen: true,
    navName: t('Spider_工具箱'),
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
        dbConsole: 'tendbCluster.toolbox.sqlExecute',
        navName: t('SQL变更执行'),
      },
      component: () => import('@views/db-manage/tendb-cluster/sql-execute/Index.vue'),
    },
    createRouteItem(TicketTypes.TENDBCLUSTER_RENAME_DATABASE, t('DB 重命名'), {
      dbConsole: 'tendbCluster.toolbox.dbRename',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH, t('主从互切'), {
      dbConsole: 'tendbCluster.toolbox.masterSlaveSwap',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_INSTANCE_FAIL_OVER, t('主库故障切换'), {
      dbConsole: 'tendbCluster.toolbox.instanceFailover',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER, t('主库故障切换'), {
      dbConsole: 'tendbCluster.toolbox.masterFailover',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_NODE_REBALANCE, t('集群容量变更'), {
      dbConsole: 'tendbCluster.toolbox.capacityChange',
    }),
    {
      path: 'proxy-scale-up/:page?',
      name: 'SpiderProxyScaleUp',
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxyScaleUp',
        navName: t('扩容接入层'),
      },
      component: () => import('@views/db-manage/tendb-cluster/proxy-scale-up/Index.vue'),
    },
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES, t('缩容接入层'), {
      dbConsole: 'tendbCluster.toolbox.proxyScaleDown',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES, t('替换接入层'), {
      dbConsole: 'tendbCluster.toolbox.spiderSwitchNodes',
    }),
    {
      path: 'proxy-slave-apply/:page?',
      name: 'SpiderProxySlaveApply',
      meta: {
        dbConsole: 'tendbCluster.toolbox.proxySlaveApply',
        navName: t('部署只读接入层'),
      },
      component: () => import('@views/db-manage/tendb-cluster/proxy-slave-apply/Index.vue'),
    },
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY, t('添加运维节点'), {
      dbConsole: 'tendbCluster.toolbox.addMnt',
    }),
    {
      path: 'db-table-backup/:page?',
      name: 'spiderDbTableBackup',
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbTableBackup',
        navName: t('库表备份'),
      },
      component: () => import('@views/db-manage/tendb-cluster/db-table-backup/Index.vue'),
    },
    {
      path: 'db-backup/:page?',
      name: 'spiderDbBackup',
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbBackup',
        navName: t('全库备份'),
      },
      component: () => import('@views/db-manage/tendb-cluster/db-backup/Index.vue'),
    },
    // 库表闪回
    {
      path: 'flashback/:page?',
      name: 'spiderFlashback',
      meta: {
        dbConsole: 'tendbCluster.toolbox.flashback',
        navName: t('闪回'),
      },
      component: () => import('@views/db-manage/tendb-cluster/flashback/Index.vue'),
    },
    // 记录级闪回
    // 两个闪回两个路由，这里没问题
    createRouteItem(TicketTypes.TENDBCLUSTER_FLASHBACK, t('闪回'), {
      dbConsole: 'tendbCluster.toolbox.flashback',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER, t('定点构造'), {
      dbConsole: 'tendbCluster.toolbox.rollback',
    }),
    {
      path: 'rollback-record',
      name: 'spiderRollbackRecord',
      meta: {
        dbConsole: 'tendbCluster.toolbox.rollbackRecord',
        navName: t('构造实例'),
      },
      component: () => import('@views/db-manage/tendb-cluster/rollback-record/Index.vue'),
    },
    {
      path: 'db-clear/:page?',
      name: 'spiderDbClear',
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbClear',
        navName: t('清档'),
      },
      component: () => import('@views/db-manage/tendb-cluster/db-clear/Index.vue'),
    },
    {
      path: 'checksum/:page?',
      name: 'spiderChecksum',
      meta: {
        dbConsole: 'tendbCluster.toolbox.checksum',
        navName: t('数据校验修复'),
      },
      component: () => import('@views/db-manage/tendb-cluster/checksum/Index.vue'),
    },
    {
      path: 'privilege-clone-client/:page?',
      name: 'spiderPrivilegeCloneClient',
      meta: {
        dbConsole: 'tendbCluster.toolbox.clientPermissionClone',
        navName: t('客户端权限克隆'),
      },
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-client/Index.vue'),
    },
    {
      path: 'privilege-clone-inst/:page?',
      name: 'spiderPrivilegeCloneInst',
      meta: {
        dbConsole: 'tendbCluster.toolbox.dbInstancePermissionClone',
        navName: t('DB 实例权限克隆'),
      },
      component: () => import('@views/db-manage/tendb-cluster/privilege-clone-inst/Index.vue'),
    },
    {
      path: 'openarea-template',
      name: 'spiderOpenareaTemplate',
      meta: {
        dbConsole: 'tendbCluster.toolbox.openareaTemplat',
        navName: t('开区模版'),
      },
      component: () => import('@views/db-manage/tendb-cluster/openarea-template/Index.vue'),
    },
    createRouteItem(TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER, t('迁移主从'), {
      dbConsole: 'tendbCluster.toolbox.masterSlaveClone',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE, t('重建从库'), {
      dbConsole: 'tendbCluster.toolbox.slaveLocalRebuild',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_RESTORE_SLAVE, t('重建从库'), {
      dbConsole: 'tendbCluster.toolbox.slaveRebuild',
    }),
    {
      path: 'webconsole',
      name: 'SpiderWebconsole',
      meta: {
        dbConsole: 'tendbCluster.toolbox.webconsole',
        navName: 'Webconsole',
      },
      component: () => import('@views/db-manage/tendb-cluster/webconsole/Index.vue'),
    },
    {
      path: 'toolbox-result/:ticketType?/:ticketId?',
      name: 'TendbclusterToolboxResult',
      meta: {
        dbConsole: 'tendbCluster.toolbox.toolboxResult',
      },
      component: () => import('@views/db-manage/common/toolbox-result/Index.vue'),
    },
    createRouteItem(TicketTypes.TENDBCLUSTER_CLUSTER_STANDARDIZE, t('集群标准化'), {
      dbConsole: 'tendbCluster.toolbox.clusterStandardize',
    }),
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
      {
        path: 'cluster-list/:clusterId?',
        name: 'tendbClusterList',
        meta: {
          fullscreen: true,
          navName: t('TendbCluster分布式集群_集群管理'),
        },
        component: () => import('@views/db-manage/tendb-cluster/cluster-list/Index.vue'),
      },
      {
        path: 'cluster-detail/:clusterId',
        name: 'tendbClusterDetail',
        meta: {
          fullscreen: true,
          navName: t('TendbCluster分布式集群_集群详情'),
        },
        component: () => import('@views/db-manage/tendb-cluster/cluster-detail/Index.vue'),
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
      return !funControllerData[dbConsole] || (funControllerData[dbConsole] as { is_enabled: boolean }).is_enabled;
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
