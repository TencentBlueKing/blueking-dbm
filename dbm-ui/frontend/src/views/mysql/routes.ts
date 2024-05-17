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

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

const mySQLExecuteRoute = {
  name: 'MySQLExecute',
  path: 'sql-execute/:step?',
  meta: {
    navName: t('变更SQL执行'),
  },
  component: () => import('@views/mysql/sql-execute/index.vue'),
}

const mySQLDBRenameRoute = {
  name: 'MySQLDBRename',
  path: 'db-rename',
  meta: {
    navName: t('DB重命名'),
  },
  component: () => import('@views/mysql/db-rename/index.vue'),
}

const mySQLPrivilegeCloneClientRoute = {
  name: 'MySQLPrivilegeCloneClient',
  path: 'privilege-clone-client',
  meta: {
    navName: t('客户端权限克隆'),
  },
  component: () => import('@views/mysql/privilege-clone-client/index.vue'),
}

const mySQLPrivilegeCloneInstRoute = {
  name: 'MySQLPrivilegeCloneInst',
  path: 'privilege-clone-inst',
  meta: {
    navName: t('DB实例权限克隆'),
  },
  component: () => import('@views/mysql/privilege-clone-inst/index.vue'),
}

const mySQLSlaveRebuildRoute = {
  name: 'MySQLSlaveRebuild',
  path: 'slave-rebuild/:page?',
  meta: {
    navName: t('重建从库'),
  },
  component: () => import('@views/mysql/slave-rebuild/index.vue'),
}

const mySQLSlaveAddRoute = {
  name: 'MySQLSlaveAdd',
  path: 'slave-add',
  meta: {
    navName: t('添加从库'),
  },
  component: () => import('@views/mysql/slave-add/index.vue'),
}

const mySQLMasterSlaveCloneRoute = {
  name: 'MySQLMasterSlaveClone',
  path: 'master-slave-clone/:page?',
  meta: {
    navName: t('迁移主从'),
  },
  component: () => import('@views/mysql/master-slave-clone/index.vue'),
}

const mySQLMasterSlaveSwapRoute = {
  name: 'MySQLMasterSlaveSwap',
  path: 'master-slave-swap/:page?',
  meta: {
    navName: t('主从互切'),
  },
  component: () => import('@views/mysql/master-slave-swap/index.vue'),
}

const mySQLProxyReplaceRoute = {
  name: 'MySQLProxyReplace',
  path: 'proxy-replace/:page?',
  meta: {
    navName: t('替换Proxy'),
  },
  component: () => import('@views/mysql/proxy-replace/index.vue'),
}

const mySQLProxyAddRoute = {
  name: 'MySQLProxyAdd',
  path: 'proxy-add/:page?',
  meta: {
    navName: t('添加Proxy'),
  },
  component: () => import('@views/mysql/proxy-add/index.vue'),
}

const mySQLMasterFailoverRoute = {
  name: 'MySQLMasterFailover',
  path: 'master-failover/:page?',
  meta: {
    navName: t('主库故障切换'),
  },
  component: () => import('@views/mysql/master-failover/index.vue'),
}

const mySQLDBTableBackupRoute = {
  name: 'MySQLDBTableBackup',
  path: 'db-table-backup/:page?',
  meta: {
    navName: t('库表备份'),
  },
  component: () => import('@views/mysql/db-table-backup/index.vue'),
}

const mySQLDBBackupRoute = {
  name: 'MySQLDBBackup',
  path: 'db-backup/:page?',
  meta: {
    navName: t('全库备份'),
  },
  component: () => import('@views/mysql/db-backup/index.vue'),
}

const mySQLDBClearRoute = {
  name: 'MySQLDBClear',
  path: 'db-clear',
  meta: {
    navName: t('清档'),
  },
  component: () => import('@views/mysql/db-clear/index.vue'),
}

const mySQLDBRollbackRoute = {
  name: 'MySQLDBRollback',
  path: 'rollback/:page?',
  meta: {
    navName: t('定点构造'),
  },
  component: () => import('@views/mysql/rollback/Index.vue'),
}

const mySQLDBFlashbackRoute = {
  name: 'MySQLDBFlashback',
  path: 'flashback/:page?',
  meta: {
    navName: t('闪回'),
  },
  component: () => import('@views/mysql/flashback/Index.vue'),
}

const mySQLChecksumRoute = {
  name: 'MySQLChecksum',
  path: 'checksum',
  meta: {
    navName: t('数据校验修复'),
  },
  component: () => import('@views/mysql/checksum/Index.vue'),
}

const mySQLOpenareaTemplateRoute = {
  name: 'MySQLOpenareaTemplate',
  path: 'openarea-template',
  meta: {
    navName: t('开区模版'),
  },
  component: () => import('@views/mysql/openarea/template/Index.vue'),
}

const toolboxDbConsoleRouteMap = {
  'mysql.toolbox.sqlExecute': mySQLExecuteRoute,
  'mysql.toolbox.dbRename': mySQLDBRenameRoute,
  'mysql.toolbox.rollback': mySQLDBRollbackRoute,
  'mysql.toolbox.flashback': mySQLDBFlashbackRoute,
  'mysql.toolbox.dbTableBackup': mySQLDBTableBackupRoute,
  'mysql.toolbox.dbBackup': mySQLDBBackupRoute,
  'mysql.toolbox.clientPermissionClone':mySQLPrivilegeCloneClientRoute,
  'mysql.toolbox.dbInstancePermissionClone': mySQLPrivilegeCloneInstRoute,
  'mysql.toolbox.slaveRebuild': mySQLSlaveRebuildRoute,
  'mysql.toolbox.slaveAdd': mySQLSlaveAddRoute,
  'mysql.toolbox.masterSlaveClone': mySQLMasterSlaveCloneRoute,
  'mysql.toolbox.masterSlaveSwap': mySQLMasterSlaveSwapRoute,
  'mysql.toolbox.proxyReplace': mySQLProxyReplaceRoute,
  'mysql.toolbox.proxyAdd': mySQLProxyAddRoute,
  'mysql.toolbox.masterFailover': mySQLMasterFailoverRoute,
  'mysql.toolbox.dbClear': mySQLDBClearRoute,
  'mysql.toolbox.checksum': mySQLChecksumRoute,
  'mysql.toolbox.openareaTemplate': mySQLOpenareaTemplateRoute,
}

const singleRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbsingle',
    path: 'single-cluster-list',
    meta: {
      navName: t('MySQL单节点_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/single-cluster-list/Index.vue'),
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    name: 'DatabaseTendbha',
    path: 'ha-cluster-list',
    meta: {
      navName: t('MySQL主从集群_集群管理'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/ha-cluster-list/Index.vue'),
  },
  {
    name: 'DatabaseTendbhaInstance',
    path: 'ha-instance-list',
    meta: {
      navName: t('MySQL主从集群_实例视图'),
      fullscreen: true,
      skeleton: 'clusterList',
    },
    component: () => import('@views/mysql/ha-instance-list/Index.vue'),
  },
];

const mysqlToolboxRouters = [
  {
    name: 'MySQLToolbox',
    path: 'toolbox',
    redirect: {
      name: '',
    },
    meta: {
      navName: t('工具箱'),
      fullscreen: true,
    },
    component: () => import('@views/mysql/toolbox/index.vue'),
    children: [] as RouteRecordRaw[],
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  // 关闭 mysql 功能
  if (controller.mysql !== true) {
    return [];
  }

  const dumperDataSubscriptionRoute = {
    name: 'DumperDataSubscription',
    path: 'dumper-data-subscribe/:dumperId(\\d+)?',
    meta: {
      navName: t('数据订阅'),
      fullscreen: true,
    },
    component: () => import('@views/mysql/dumper/Index.vue'),
  }

  const mysqlPartitionManageRoute = {
    path: 'partition-manage',
    name: 'mysqlPartitionManage',
    meta: {
      navName: t('Mysql 分区管理'),
    },
    component: () => import('@views/mysql/partition-manage/Index.vue'),
  }

  const permissionManageRoutes = [
    {
      name: 'PermissionRules',
      path: 'permission-rules',
      meta: {
        navName: t('MySQL_授权规则'),
      },
      component: () => import('@views/mysql/permission-rule/index.vue'),
    },
    {
      path: 'whitelist',
      name: 'mysqlWhitelist',
      meta: {
        navName: t('授权白名单'),
      },
      component: () => import('@views/whitelist/list/Index.vue'),
    },
  ]

  const commonRouters: RouteRecordRaw[] = [
    {
      name: 'MysqlManage',
      path: 'mysql-manage',
      meta: {
        navName: t('Mysql 集群管理'),
      },
      redirect: {
        name: 'DatabaseTendbha',
      },
      component: () => import('@views/mysql/Index.vue'),
      children: [
        {
          path: 'openarea-template-create',
          name: 'MySQLOpenareaTemplateCreate',
          meta: {
            navName: t('新建开区模板'),
          },
          component: () => import('@views/mysql/openarea/template-create/Index.vue'),
        },
        {
          path: 'openarea-template-edit/:id',
          name: 'MySQLOpenareaTemplateEdit',
          meta: {
            navName: t('编辑开区模板'),
          },
          component: () => import('@views/mysql/openarea/template-create/Index.vue'),
        },
        {
          path: 'openarea-create/:id',
          name: 'mysqlOpenareaCreate',
          meta: {
            navName: t('新建开区'),
          },
          component: () => import('@views/mysql/openarea/create/Index.vue'),
        },
      ],
    },
  ];

  if (checkDbConsole(funControllerData, 'mysql.dataSubscription')) {
    commonRouters[0].children!.push(dumperDataSubscriptionRoute);
  }

  if (checkDbConsole(funControllerData, 'mysql.partitionManage')) {
    commonRouters[0].children!.push(mysqlPartitionManageRoute);
  }

  if (checkDbConsole(funControllerData, 'mysql.permissionManage')) {
    commonRouters[0].children!.push(...permissionManageRoutes);
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'MysqlManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (controller.tendbsingle) {
    renderRoutes.children?.push(...singleRoutes);
  }

  if (controller.tendbha) {
    if (funControllerData['mysql.haInstanceList'] && !funControllerData['mysql.haInstanceList'].is_enabled) {
      haRoutes.pop();
    }
    renderRoutes.children?.push(...haRoutes);
  }

  if (controller.toolbox) {
    Object.entries(toolboxDbConsoleRouteMap).forEach(([key, routeItem]) => {
      const dbConsoleValue = key as ExtractedControllerDataKeys;
      if (!funControllerData[dbConsoleValue] || funControllerData[dbConsoleValue].is_enabled) {
        mysqlToolboxRouters[0].children!.push(routeItem);
        if (routeItem.name === 'MySQLExecute') {
          mysqlToolboxRouters[0].redirect!.name = 'MySQLExecute'
        }
      }
    });

    if (!mysqlToolboxRouters[0].redirect!.name) {
      mysqlToolboxRouters[0].redirect!.name = mysqlToolboxRouters[0].children![0]?.name as string ?? '';
    }
    
    renderRoutes.children?.push(...mysqlToolboxRouters);
  }
  return commonRouters;
}
