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
    createRouteItem(TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE, t('变更SQL执行'), {}, { params: '/:step?' }),
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
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES, t('添加 Spider'), {
      dbConsole: 'tendbCluster.toolbox.proxyScaleUp',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES, t('减少 Spider'), {
      dbConsole: 'tendbCluster.toolbox.proxyScaleDown',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_CONF_UP_DOWN, t('Spider 升降配'), {
      dbConsole: 'tendbCluster.toolbox.spiderConfUpDown',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES, t('替换 Spider'), {
      dbConsole: 'tendbCluster.toolbox.switchNodes',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY, t('部署只读接入层'), {
      dbConsole: 'tendbCluster.toolbox.proxySlaveApply',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY, t('添加运维节点'), {
      dbConsole: 'tendbCluster.toolbox.addMnt',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_REMOTE_UPGRADE, t('版本升级'), {
      dbConsole: 'tendbCluster.toolbox.remoteUpgrade',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_LOCAL_UPGRADE, t('版本升级'), {
      dbConsole: 'tendbCluster.toolbox.localUpgrade',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_SPIDER_UPGRADE, t('版本升级'), {
      dbConsole: 'tendbCluster.toolbox.spiderUpgrade',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_MIGRATE_UPGRADE, t('版本升级'), {
      dbConsole: 'tendbCluster.toolbox.migateUpgrade',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP, t('库表备份'), {
      dbConsole: 'tendbCluster.toolbox.dbTableBackup',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_FULL_BACKUP, t('全库备份'), {
      dbConsole: 'tendbCluster.toolbox.dbBackup',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_FLASHBACK, t('回档'), {
      dbConsole: 'tendbCluster.toolbox.flashback',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_ROLLBACK, t('回档'), {
      dbConsole: 'tendbCluster.toolbox.rollback',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_FIXPOINT_EXIST, t('构造'), {
      dbConsole: 'tendbCluster.toolbox.fixpointExist',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_FIXPOINT_NEW, t('构造'), {
      dbConsole: 'tendbCluster.toolbox.fixpointNew',
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
    createRouteItem(TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE, t('清档'), {
      dbConsole: 'tendbCluster.toolbox.dbClear',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_CHECKSUM, t('数据校验修复'), {
      dbConsole: 'tendbCluster.toolbox.checksum',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES, t('客户端权限克隆'), {
      dbConsole: 'tendbCluster.toolbox.clientPermissionClone',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES, t('DB 实例权限克隆'), {
      dbConsole: 'tendbCluster.toolbox.dbInstancePermissionClone',
    }),
    createRouteItem(TicketTypes.TENDBCLUSTER_OPEN_AREA, t('开区模版'), {
      dbConsole: 'tendbCluster.toolbox.openAreaTemplate',
    }),
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
      dbType: DBTypes.TENDBCLUSTER,
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
        name: 'TendbClusterOpenareaTemplateCreate',
        meta: {
          navName: t('新建开区模板'),
        },
        component: () => import('@views/db-manage/tendb-cluster/TENDBCLUSTER_OPEN_AREA/template-create/Index.vue'),
      },
      {
        path: 'openarea-template-edit/:id',
        name: 'TendbClusterOpenareaTemplateEdit',
        meta: {
          navName: t('编辑开区模板'),
        },
        component: () => import('@views/db-manage/tendb-cluster/TENDBCLUSTER_OPEN_AREA/template-create/Index.vue'),
      },
      {
        path: 'openarea-create/:id',
        name: 'TendbClusterOpenareaCreate',
        meta: {
          navName: t('新建开区'),
        },
        component: () => import('@views/db-manage/tendb-cluster/TENDBCLUSTER_OPEN_AREA/create/Index.vue'),
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
