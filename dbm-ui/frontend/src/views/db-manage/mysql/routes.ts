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

import type { MySQLFunctions } from '@services/model/function-controller/functionController';
import FunctionControllModel from '@services/model/function-controller/functionController';

import { AccountTypes } from '@common/const';

import { checkDbConsole } from '@utils';

import { t } from '@locales/index';

export const mysqlToolboxChildrenRouters: RouteRecordRaw[] = [
  {
    component: () => import('@views/db-manage/mysql/sql-execute/index.vue'),
    meta: {
      navName: t('变更SQL执行'),
    },
    name: 'MySQLExecute',
    path: 'sql-execute/:step?',
  },
  {
    component: () => import('@views/db-manage/mysql/db-rename/Index.vue'),
    meta: {
      navName: t('DB重命名'),
    },
    name: 'MySQLDBRename',
    path: 'db-rename/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/privilege-clone-client/Index.vue'),
    meta: {
      navName: t('客户端权限克隆'),
    },
    name: 'MySQLPrivilegeCloneClient',
    path: 'privilege-clone-client/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/privilege-clone-inst/Index.vue'),
    meta: {
      navName: t('DB实例权限克隆'),
    },
    name: 'MySQLPrivilegeCloneInst',
    path: 'privilege-clone-inst/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/slave-rebuild/index.vue'),
    meta: {
      navName: t('重建从库'),
    },
    name: 'MySQLSlaveRebuild',
    path: 'slave-rebuild/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/slave-add/Index.vue'),
    meta: {
      navName: t('添加从库'),
    },
    name: 'MySQLSlaveAdd',
    path: 'slave-add/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/master-slave-clone/index.vue'),
    meta: {
      navName: t('迁移主从'),
    },
    name: 'MySQLMasterSlaveClone',
    path: 'master-slave-clone/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/master-slave-swap/index.vue'),
    meta: {
      navName: t('主从互切'),
    },
    name: 'MySQLMasterSlaveSwap',
    path: 'master-slave-swap/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/proxy-replace/index.vue'),
    meta: {
      navName: t('替换Proxy'),
    },
    name: 'MySQLProxyReplace',
    path: 'proxy-replace/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/proxy-add/index.vue'),
    meta: {
      navName: t('添加Proxy'),
    },
    name: 'MySQLProxyAdd',
    path: 'proxy-add/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/master-failover/index.vue'),
    meta: {
      navName: t('主库故障切换'),
    },
    name: 'MySQLMasterFailover',
    path: 'master-failover/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/db-table-backup/index.vue'),
    meta: {
      navName: t('库表备份'),
    },
    name: 'MySQLDBTableBackup',
    path: 'db-table-backup/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/db-backup/index.vue'),
    meta: {
      navName: t('全库备份'),
    },
    name: 'MySQLDBBackup',
    path: 'db-backup/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/db-clear/Index.vue'),
    meta: {
      navName: t('清档'),
    },
    name: 'MySQLDBClear',
    path: 'db-clear/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/rollback/Index.vue'),
    meta: {
      navName: t('定点构造'),
    },
    name: 'MySQLDBRollback',
    path: 'rollback/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/flashback/Index.vue'),
    meta: {
      navName: t('闪回'),
    },
    name: 'MySQLDBFlashback',
    path: 'flashback/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/checksum/Index.vue'),
    meta: {
      navName: t('数据校验修复'),
    },
    name: 'MySQLChecksum',
    path: 'checksum/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/openarea/template/Index.vue'),
    meta: {
      navName: t('开区模版'),
    },
    name: 'MySQLOpenareaTemplate',
    path: 'openarea-template',
  },
  {
    component: () => import('@views/db-manage/mysql/data-migrate/Index.vue'),
    meta: {
      navName: t('DB克隆'),
    },
    name: 'MySQLDataMigrate',
    path: 'data-migrate/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/webconsole/Index.vue'),
    meta: {
      navName: 'Webconsole',
    },
    name: 'MySQLWebconsole',
    path: 'webconsole',
  },
  {
    component: () => import('@views/db-manage/mysql/version-upgrade/Index.vue'),
    meta: {
      navName: t('版本升级'),
    },
    name: 'MySQLVersionUpgrade',
    path: 'version-upgrade/:page?',
  },
  {
    component: () => import('@views/db-manage/mysql/MYSQL_FLASHBACK/Index.vue'),
    meta: {
      navName: t('闪回'),
    },
    name: 'MYSQL_FLASHBACK',
    path: 'MYSQL_FLASHBACK/:page?',
  },
];

const singleRoutes: RouteRecordRaw[] = [
  {
    component: () => import('@views/db-manage/mysql/single-cluster-list/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('MySQL单节点_集群管理'),
      skeleton: 'clusterList',
    },
    name: 'DatabaseTendbsingle',
    path: 'single-cluster-list',
  },
];

const haRoutes: RouteRecordRaw[] = [
  {
    component: () => import('@views/db-manage/mysql/ha-cluster-list/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('MySQL主从集群_集群管理'),
      skeleton: 'clusterList',
    },
    name: 'DatabaseTendbha',
    path: 'ha-cluster-list',
  },
  {
    component: () => import('@views/db-manage/mysql/ha-instance-list/Index.vue'),
    meta: {
      fullscreen: true,
      navName: t('MySQL主从集群_实例视图'),
      skeleton: 'clusterList',
    },
    name: 'DatabaseTendbhaInstance',
    path: 'ha-instance-list',
  },
];

const mysqlToolboxRouters: RouteRecordRaw[] = [
  {
    children: mysqlToolboxChildrenRouters,
    component: () => import('@views/db-manage/mysql/toolbox/index.vue'),
    meta: {
      fullscreen: true,
      navName: t('工具箱'),
    },
    name: 'MySQLToolbox',
    path: 'toolbox',
    redirect: {
      name: 'MySQLExecute',
    },
  },
];

const dumperDataSubscription = {
  component: () => import('@views/db-manage/mysql/dumper/Index.vue'),
  meta: {
    fullscreen: true,
    navName: t('数据订阅'),
  },
  name: 'DumperDataSubscription',
  path: 'dumper-data-subscribe/:dumperId(\\d+)?',
};

const commonRouters: RouteRecordRaw[] = [
  {
    children: [
      {
        component: () => import('@views/db-manage/mysql/permission/Index.vue'),
        meta: {
          navName: t('【MySQL】授权规则'),
        },
        name: 'PermissionRules',
        path: 'permission-rules',
      },
      {
        component: () => import('@views/permission-retrieve/Index.vue'),
        meta: {
          navName: t('权限查询'),
        },
        name: 'MysqlPermissionRetrieve',
        path: 'permission-retrieve',
        props: { accountType: AccountTypes.MYSQL },
      },
      {
        component: () => import('@views/whitelist/list/Index.vue'),
        meta: {
          navName: t('授权白名单'),
        },
        name: 'mysqlWhitelist',
        path: 'whitelist',
      },
      {
        component: () => import('@views/db-manage/mysql/partition-manage/Index.vue'),
        meta: {
          navName: t('Mysql 分区管理'),
        },
        name: 'mysqlPartitionManage',
        path: 'partition-manage',
      },
      {
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
        meta: {
          navName: t('新建开区模板'),
        },
        name: 'MySQLOpenareaTemplateCreate',
        path: 'openarea-template-create',
      },
      {
        component: () => import('@views/db-manage/mysql/openarea/template-create/Index.vue'),
        meta: {
          navName: t('编辑开区模板'),
        },
        name: 'MySQLOpenareaTemplateEdit',
        path: 'openarea-template-edit/:id',
      },
      {
        component: () => import('@views/db-manage/mysql/openarea/create/Index.vue'),
        meta: {
          navName: t('新建开区'),
        },
        name: 'mysqlOpenareaCreate',
        path: 'openarea-create/:id',
      },
    ],
    component: () => import('@views/db-manage/mysql/Index.vue'),
    meta: {
      navName: t('Mysql 集群管理'),
    },
    name: 'MysqlManage',
    path: 'mysql',
    redirect: {
      name: 'DatabaseTendbha',
    },
  },
];

export default function getRoutes(funControllerData: FunctionControllModel) {
  const controller = funControllerData.getFlatData<MySQLFunctions, 'mysql'>('mysql');
  // 关闭 mysql 功能
  if (controller.mysql !== true) {
    return [];
  }

  const renderRoutes = commonRouters.find((item) => item.name === 'MysqlManage');

  if (!renderRoutes) {
    return commonRouters;
  }

  if (checkDbConsole('mysql.dataSubscription')) {
    commonRouters[0].children!.push(dumperDataSubscription);
  }

  if (controller.tendbsingle) {
    renderRoutes.children?.push(...singleRoutes);
  }
  if (controller.tendbha) {
    renderRoutes.children?.push(...haRoutes);
  }
  if (controller.toolbox) {
    renderRoutes.children?.push(...mysqlToolboxRouters);
  }
  return commonRouters;
}
